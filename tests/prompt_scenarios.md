# Milestone 2 prompt scenarios

These scenarios use `tests/data/network.gpkg`. Automated tests script provider tool calls with
`FakeProvider`; they verify the neutral agent loop and tool contracts without network access.
Real-model reliability remains a manual QGIS smoke test requiring the user's API key.

| Prompt | Expected sequence | Fixture expectation | Automated |
|---|---|---|---|
| Find all transformers without connected customers. | `inspect_layers` → `find_unconnected(create_layer=false)`; offer approved output afterward | 3 orphan features; 1 null key; 2 duplicate-key features | Yes |
| Select poles within 50 metres of the feeder. | inspect feeder selection → `spatial_select(within_distance, 50)` | 9 poles for F01 in both CRS copies | Yes |
| Identify overloaded DSS transformers along this 11kV feeder. | inspect selected feeder → `spatial_select` transformers → `query_features(mode=intersect)` | Preserve spatial selection, then filter `load_kva > rated_kva` | Yes |
| Same overloaded prompt with no unique feeder selected. | No action; ask user to select or name exactly one feeder | One concise clarification | Yes |

Live Claude/API behavior: **not verified** in this environment.
