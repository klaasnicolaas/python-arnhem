# pylint: disable=W0621
"""Asynchronous Python client providing Open Data information of Arnhem."""

import asyncio

from arnhem import ODPArnhem


async def main() -> None:
    """Show example on using the ODP Arnhem API client."""
    async with ODPArnhem() as client:
        locations = await client.locations(
            limit=100,
            set_filter="RVV_SOORT='E6a'",
        )

        count: int = len(locations)
        for item in locations:
            print(item)

        # Count unique id's in disabled_parkings
        unique_values = len({item.spot_id for item in locations})

        print("__________________________")
        print(f"Total locations found: {count}")
        print(f"Unique ID values: {unique_values}")


def start() -> None:
    """Call the main async method."""
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
