# interface-changes

Type cards: detected interface changes (from facts: new → definition, changed → diff, breaking/review badges) or authored `cards` for a proposed model.

## Use when
- explain: facts list interface changes (GraphQL, events, migrations, SDK). Include it whenever contracts.json is not empty.
- present: the design adds or changes types/records (`cards`).

## Ask (present)
- Which records gain or lose fields?

## Extract (explain)
With facts: no fields needed — cards come from contracts.json. For a proposal: `cards` = [{name, surface, change: added|changed, after, before?, ref}].
