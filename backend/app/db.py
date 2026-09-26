"""Portable SQLAlchemy persistence. Service layer owns multi-row transactions."""
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.pool import StaticPool

from .schemas import UrbanState


class Base(DeclarativeBase):
    pass


class StateRow(Base):
    __tablename__ = "state_snapshots"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)


class CurrentRow(Base):
    __tablename__ = "ward_current"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    state_id: Mapped[str] = mapped_column(ForeignKey("state_snapshots.id"))
    version: Mapped[int] = mapped_column(Integer, default=0)


class PassportRow(Base):
    __tablename__ = "action_passports"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    state_id: Mapped[str] = mapped_column(ForeignKey("state_snapshots.id"))
    state_version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    payload: Mapped[dict] = mapped_column(JSON)


class AuditRow(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                               default=lambda: datetime.now(timezone.utc))
    event: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSON)


class Store:
    def __init__(self, url: str = "sqlite:///urbannexus.db"):
        options = {}
        if url.startswith("sqlite"):
            options["connect_args"] = {"check_same_thread": False}
            if url.endswith(":memory:"):
                options["poolclass"] = StaticPool
        self.engine = create_engine(url, **options)
        Base.metadata.create_all(self.engine)

    def initialize(self, state: UrbanState):
        with Session(self.engine) as session, session.begin():
            if session.get(CurrentRow, 1) is None:
                session.add(StateRow(id=state.id, payload=state.model_dump(mode="json")))
                session.flush()
                session.add(CurrentRow(id=1, state_id=state.id, version=0))

    def current(self) -> tuple[UrbanState, int]:
        with Session(self.engine) as session:
            pointer = session.get(CurrentRow, 1)
            if pointer is None:
                raise RuntimeError("Store has not been initialized")
            state = session.get(StateRow, pointer.state_id)
            return UrbanState.model_validate(state.payload), pointer.version
