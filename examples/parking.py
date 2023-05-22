# pylint: disable=W0621
"""Asynchronous Python client providing Open Data information of Arnhem."""

import asyncio

from arnhem import ODPArnhem


async def main() -> None:
    """Show example on using the ODP Arnhem API client."""
    async with ODPArnhem() as client:
        count: int

        locations = await client.locations(
            limit=100,
            set_filter="RVV_SOORT='E6a'",
        )

        for index, item in enumerate(locations, 1):
            count = index
            print(item)

        # Count unique id's in disabled_parkings
        unique_values: list[int] = []
        for location in locations:
            unique_values.append(location.spot_id)
        num_values = len(set(unique_values))

        print("__________________________")
        print(f"Total locations found: {count}")
        print(f"Unique ID values: {num_values}")


def start() -> None:
    """Call the main async method."""
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
