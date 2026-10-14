# Complete parking collections

[Back to the README](../README.md)

`await client.parking_collection(set_filter="1=1", page_size=500, max_records=10000)` returns a `ParkingCollection` with `records`, `total_count`, `pages_fetched` and `complete`. Use an ArcGIS selection such as `set_filter="RVV_SOORT='E6a'"` when only general disabled-parking records are needed.

Every record exposes the original asset `ID` as `record.id`, full WGS84 geometry and original `source_attributes`. The auxiliary ArcGIS `OBJECTID` remains in `source_attributes["OBJECTID"]`; source queries use it to identify complete retrieval batches. It does not replace the asset identity.

The client compares the source count with all unique object IDs, retrieves each object in bounded batches, checks unique asset IDs and verifies the selection membership again. Invalid limits raise `ValueError`; source errors, malformed records, incomplete batches or changed selection raise `ODPArnhemError` instead of returning a partial collection. The safety ceiling rejects oversized selections rather than truncating them.

Selection membership checks do not guarantee a transactional snapshot: a source can edit a record in place without changing its ID. Original geometry and source claims remain available for consumer review.
