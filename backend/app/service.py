"""Stateful application operations; simulation and optimization stay pure."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .db import AuditRow, CurrentRow, PassportRow, StateRow
from .decision import evaluate_action, find_minimum_effective_intervention
from .domains import MODEL_VERSIONS
from .generator import stamp
from .schemas import Action, DecisionRequest, UrbanState


class ConflictError(Exception):
    pass


class MissingError(Exception):
    pass


class Service:
    def __init__(self, store):
        self.store = store

    @staticmethod
    def reserve_revision(session, expected_version):
        # Acquire the ward write lock before inserting a content-addressed outcome.
        # Otherwise simultaneous equivalent simulations can race on its primary key.
        changed = session.execute(
            update(CurrentRow)
            .where(CurrentRow.id == 1, CurrentRow.version == expected_version)
            .values(version=expected_version + 1)
        )
        if changed.rowcount != 1:
            raise ConflictError("Concurrent state update; evaluate again")

    def replace_state(self, state, event, details):
        state = stamp(state.model_copy(deep=True))
        with Session(self.store.engine) as session, session.begin():
            current = session.get(CurrentRow, 1)
            old_version = current.version
            self.reserve_revision(session, old_version)
            payload = state.model_dump(mode="json")
            existing = session.get(StateRow, state.id)
            if existing is None:
                session.add(StateRow(id=state.id, payload=payload))
            elif existing.payload != payload:
                raise ConflictError("Snapshot ID collision; historical state cannot be overwritten")
            session.flush()
            session.execute(update(CurrentRow).where(CurrentRow.id == 1).values(state_id=state.id))
            session.add(
                AuditRow(event=event, payload={"state_id": state.id, "version": old_version + 1, **details})
            )
        return state, old_version + 1

    def recommend(self, request):
        state, version = self.store.current()
        result = find_minimum_effective_intervention(state, request)
        selected = result["selected"]
        passport = None
        if selected:
            passport = {
                "id": "AP-" + uuid.uuid4().hex[:12],
                "timestamp": datetime.now(UTC).isoformat(),
                "input_state_id": state.id,
                "input_state_version": version,
                "problem": f"Prevent waste overflow in {request.zone_id} over {request.horizon_minutes} minutes",
                "affected_zones": selected["simulation"]["affected_zones"],
                "proposed_intervention": selected["action"],
                "minimum_effective_intervention": selected["magnitude"],
                "target_kpi": {
                    "name": "overflow_probability",
                    "less_than": request.budget.waste_overflow_max,
                },
                "baseline_kpi": result["baseline"]["kpis"],
                "predicted_kpi": selected["simulation"]["kpis"],
                "direct_impacts": {
                    "waste_overflow_delta": selected["ripple"]["deltas"]["overflow_probability"]
                },
                "cross_domain_impacts": selected["ripple"],
                "impact_budget": request.budget.model_dump(),
                "constraint_results": selected["budget"],
                "objective_contributions": selected["objective"],
                "prediction_uncertainty": selected["simulation"]["uncertainty"],
                "model_versions": MODEL_VERSIONS,
                "simulation_seed": request.seed,
                "data_provenance": state.metadata.model_dump(),
                "assumptions": selected["simulation"]["assumptions"],
                "reversibility": "Cancelable before dispatch. A simulated completed collection cannot be undone; reset starts a new audited scenario.",
                "approval_status": "pending",
                "request": request.model_dump(),
                "runtime_ms": selected["simulation"]["runtime_ms"],
            }
        with Session(self.store.engine) as session, session.begin():
            if passport:
                session.add(
                    PassportRow(
                        id=passport["id"],
                        state_id=state.id,
                        state_version=version,
                        status="pending",
                        payload=passport,
                    )
                )
            session.add(
                AuditRow(
                    event="recommendation" if passport else "no_safe_action",
                    payload={
                        "state_id": state.id,
                        "version": version,
                        "request": request.model_dump(),
                        "passport_id": passport["id"] if passport else None,
                        "rejections": result["rejection_summary"],
                    },
                )
            )
        result["passport"] = passport
        return result

    def passports(self):
        with Session(self.store.engine) as session:
            return [r.payload for r in session.scalars(select(PassportRow).order_by(PassportRow.id))]

    def passport(self, passport_id):
        with Session(self.store.engine) as session:
            row = session.get(PassportRow, passport_id)
            if not row:
                raise MissingError("Action Passport not found")
            return row.payload

    def decide(self, passport_id, approval, approve=True):
        with Session(self.store.engine) as session, session.begin():
            row = session.scalar(select(PassportRow).where(PassportRow.id == passport_id).with_for_update())
            if row is None:
                raise MissingError("Action Passport not found")
            if row.status != "pending":
                raise ConflictError(f"Passport already {row.status}; actions cannot be replayed")
            payload = dict(row.payload)
            current = session.get(CurrentRow, 1)
            if approve:
                if current.version != row.state_version or current.state_id != row.state_id:
                    raise ConflictError("Stale passport: ward state changed. Evaluate again.")
                state = UrbanState.model_validate(session.get(StateRow, row.state_id).payload)
                request = DecisionRequest.model_validate(payload["request"])
                action = Action.model_validate(payload["proposed_intervention"])
                checked = evaluate_action(state, action, request)
                if not checked["budget"]["passed"]:
                    raise ConflictError("Action no longer meets hard constraints")
                self.reserve_revision(session, row.state_version)
                next_state = checked["simulation"]["state"]
                existing = session.get(StateRow, next_state["id"])
                if existing is None:
                    session.add(StateRow(id=next_state["id"], payload=next_state))
                elif existing.payload != next_state:
                    raise ConflictError("Snapshot ID collision; historical state cannot be overwritten")
                session.flush()
                session.execute(
                    update(CurrentRow).where(CurrentRow.id == 1).values(state_id=next_state["id"])
                )
                payload["outcome"] = {
                    "state_id": next_state["id"],
                    "kpis": checked["simulation"]["kpis"],
                    "measurement_type": "simulated outcome, not field observation",
                }
            payload["approval_status"] = "approved" if approve else "rejected"
            payload["human_decision"] = {**approval.model_dump(), "timestamp": datetime.now(UTC).isoformat()}
            updated = session.execute(
                update(PassportRow)
                .where(PassportRow.id == passport_id, PassportRow.status == "pending")
                .values(status=payload["approval_status"], payload=payload)
            )
            if updated.rowcount != 1:
                raise ConflictError("Concurrent approval; action was already decided")
            session.add(
                AuditRow(
                    event="approved_and_simulated" if approve else "rejected",
                    payload={
                        "passport_id": passport_id,
                        "input_state_id": row.state_id,
                        "seed": payload["simulation_seed"],
                        "model_versions": MODEL_VERSIONS,
                        "decision": payload["human_decision"],
                        "result": payload.get("outcome"),
                    },
                )
            )
        return payload

    def audit(self):
        with Session(self.store.engine) as session:
            return [
                {"id": r.id, "timestamp": r.timestamp.isoformat(), "event": r.event, "payload": r.payload}
                for r in session.scalars(select(AuditRow).order_by(AuditRow.id.desc()).limit(200))
            ]

    def comparison(self):
        with Session(self.store.engine) as session:
            event = session.scalar(
                select(AuditRow)
                .where(AuditRow.event == "approved_and_simulated")
                .order_by(AuditRow.id.desc())
            )
            if event is None:
                return {"action_id": None, "before": None, "after": None}
            passport = session.get(PassportRow, event.payload["passport_id"]).payload
            return {
                "action_id": passport["id"],
                "before": passport["baseline_kpi"],
                "after": passport["outcome"]["kpis"],
                "measurement_type": "simulated",
            }
