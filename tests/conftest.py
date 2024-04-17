"""Fixture for the Open Data Platform API of Arnhem tests."""

from collections.abc import AsyncGenerator

import pytest
from aiohttp import ClientSession

from arnhem import ODPArnhem


@pytest.fixture(name="odp_arnhem_client")
async def client() -> AsyncGenerator[ODPArnhem, None]:
    """Fixture for the Open Data Platform API of Arnhem client."""
    async with (
        ClientSession() as session,
        ODPArnhem(session=session) as odp_arnhem_client,
    ):
        yield odp_arnhem_client
