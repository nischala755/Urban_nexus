# Urban state

One immutable-by-convention Pydantic UrbanState contains an ID, UTC timestamp,
elapsed minutes, zones, vehicle availability, weather and source metadata.
Each zone has traffic (vehicles/minute, queue, density, speed, delay), energy
(base, flexible, renewable and pump kW), water (m3/h, reservoir m3/capacity,
pump m3/h and availability), and waste (m3 capacity, fill %, rate %/hour).
Histories are short numeric arrays for transparent forecasting. Finite values,
physical bounds, unique zone identifiers and nonempty domains are validated.
Source metadata records synthetic, generator version, seed and scenario.
State snapshots are persisted as validated JSON; the ward row points to the
current snapshot with an optimistic version. Passports reference that version.
SQLAlchemy tables: state_snapshots, ward_current, action_passports, audit_events.
