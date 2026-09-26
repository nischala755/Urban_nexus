"""Synthetic source with no wall-clock or global random-state dependence."""

import hashlib
import random
from datetime import UTC, datetime

from .schemas import Energy, Provenance, Traffic, UrbanState, Waste, Water, Zone


def stamp(state: UrbanState) -> UrbanState:
    data = state.model_dump_json(exclude={"id"})
    state.id = "S-" + hashlib.sha256(data.encode()).hexdigest()[:16]
    return state


def generate_state(seed: int = 42) -> UrbanState:
    rng = random.Random(seed)
    zones = []
    names = ["Market quarter", "Civic district", "Garden neighbourhood", "Riverside ward"]
    positions = [(25, 70), (68, 76), (30, 24), (77, 30)]
    for i, (name, (x, y)) in enumerate(zip(names, positions), 1):
        arrival = rng.uniform(16, 20)
        water = rng.uniform(115, 145)
        base = rng.uniform(245, 295)
        pump = water + 25
        demand = base + 60 + pump * 0.6
        history = lambda value: [round(value + rng.uniform(-3, 3), 4) for _ in range(12)]
        zones.append(
            Zone(
                id=f"Z{i:02}",
                name=name,
                x=x,
                y=y,
                traffic=Traffic(
                    arrival_vpm=arrival,
                    queue_vehicles=5,
                    density=arrival / 30,
                    vehicle_count=arrival * 5,
                    average_speed_kph=32,
                    delay_seconds=18,
                    history=history(arrival),
                ),
                energy=Energy(
                    base_kw=base, flexible_kw=60, renewable_kw=90, demand_kw=demand, history=history(demand)
                ),
                water=Water(
                    demand_m3h=water,
                    reservoir_m3=600,
                    pump_flow_m3h=pump,
                    pump_kw=pump * 0.6,
                    history=history(water),
                ),
                waste=Waste(
                    fill_pct=rng.uniform(75, 79) if i == 4 else rng.uniform(35, 55),
                    rate_pct_h=6,
                    rate_std_pct_h=2,
                ),
            )
        )
    return stamp(
        UrbanState(
            id="pending",
            timestamp=datetime(2026, 1, 1, 7, 50, tzinfo=UTC),
            zones=zones,
            metadata=Provenance(seed=seed),
        )
    )
