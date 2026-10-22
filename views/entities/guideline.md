# entities

Types, tables, inputs and events with their relations, and field-level changes.

## Use when
- explain: the change adds or changes data shapes (inputs, events, models, migrations), especially when a value changes form across layers.
- present: new records/fields/relations in the design.
Not when the interface cards already show the only changed type.

## Ask (present)
- Which records gain or lose fields, and which one is the source of truth?

## Extract (explain)
One entity per type/table touched (≤ 8), changed/new fields marked, unchanged fields only for context; relations as `from → to` with a short label.
