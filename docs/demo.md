# GeoUtility AI Copilot demo

Use the synthetic `tests/data/network.gpkg` layers ending in `_32631`, then confirm the bundled
schema map or propose and review one in Settings. Never use real customer data for this demo.

## 1. Inspect the project

Prompt: **What layers do I have?**

Expected: `inspect_layers` reports mapped roles, projected CRS, fields, counts, and selection state
without sending geometry coordinates.

## 2. Find orphan transformers

Prompt: **Find all transformers without connected customers.**

Expected: count-only analysis returns 3 orphan features. If a temporary result layer is requested,
the OUTPUT approval dialog appears first. Rejecting must leave the project unchanged.

## 3. Select poles near a feeder

Select feeder F01, then prompt: **Select poles within 50 metres of this feeder.**

Expected: `spatial_select` selects 9 poles, including the pole exactly 50 m away. The tool step
offers **Undo selection**. The same count is expected with the `_4326` fixture copies.

## 4. Identify overloaded transformers

With exactly one feeder selected, prompt: **Identify overloaded DSS transformers along this 11kV
feeder.**

Expected: the copilot spatially selects transformers, then intersects that selection with
`load_kva > rated_kva`. With no unique feeder selected it asks one clarifying question.

## 5. Generate a validation report

Prompt: **Generate a network asset validation report.**

Expected: the approval dialog shows the destination before any write. The report includes all
eight checks, QGIS/model metadata, and known fixture findings including 3 orphan transformers,
2 duplicate-ID features, 1 missing mandatory-ID feature, and 1 capacity outlier.
