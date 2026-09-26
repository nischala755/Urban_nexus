import os

import pytest

from backend.app.db import Store
from backend.app.generator import generate_state


@pytest.mark.skipif(not os.getenv("TEST_POSTGRES_URL"), reason="Requires PostgreSQL")
@pytest.mark.parametrize("scheme", ["postgresql://", "postgres://"])
def test_render_connection_url_uses_installed_driver(scheme):
    url = os.environ["TEST_POSTGRES_URL"]
    render_url = scheme + url.split("://", 1)[1]
    store = Store(render_url)
    try:
        store.initialize(generate_state(42))
        assert store.engine.dialect.driver == "psycopg"
        assert len(store.current()[0].zones) == 4
    finally:
        store.engine.dispose()
