import pytest
from pydantic import ValidationError

from backend.app.db import Store
from backend.app.generator import generate_state
from backend.app.schemas import UrbanState


def test_generator_is_repeatable_and_seed_changes_measurements():
    first = generate_state(42)
    assert first == generate_state(42)
    assert first.zones != generate_state(43).zones
    assert len(first.zones) == 4
    assert first.metadata.source_type == "synthetic"


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf")])
def test_invalid_water_measurement_is_rejected(value):
    data = generate_state(42).model_dump()
    data["zones"][0]["water"]["demand_m3h"] = value
    with pytest.raises(ValidationError):
        UrbanState.model_validate(data)


def test_duplicate_zones_are_rejected():
    data = generate_state(42).model_dump()
    data["zones"][1]["id"] = data["zones"][0]["id"]
    with pytest.raises(ValidationError):
        UrbanState.model_validate(data)


def test_missing_domain_is_rejected_not_silently_filled():
    data = generate_state(42).model_dump()
    del data["zones"][0]["water"]
    with pytest.raises(ValidationError):
        UrbanState.model_validate(data)


def test_persistence_survives_restart(tmp_path):
    url = f"sqlite:///{tmp_path / 'ward.db'}"
    original = generate_state(42)
    store = Store(url)
    store.initialize(original)
    assert Store(url).current() == (original, 0)
    store.initialize(generate_state(99))
    assert store.current() == (original, 0)
