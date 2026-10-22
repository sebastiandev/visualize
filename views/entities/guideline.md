# entities

Types, tables, inputs and events with their relations, and field-level changes.

## Use when
- explain: **the same field is added to ≥ 3 types** — it travels across layers (input → DTO → domain → row /
  event). `facts` reports this as a signal. Cards show each type alone; only this view shows the route and
  where the value changes form (e.g. a global id becoming a row id).
- explain: the change adds or changes data shapes (inputs, events, models, migrations) that relate to each other.
- present: new records/fields/relations in the design.
Skip only when a single type changes and nothing else carries its fields.

## Ask (present)
- Which records gain or lose fields, and which one is the source of truth?

## Extract (explain)
One entity per type/table touched (≤ 8), changed/new fields marked, unchanged fields only for context; relations as `from → to` with a short label.
