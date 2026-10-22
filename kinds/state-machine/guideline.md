# state-machine

Statuses and the transitions between them, with what this change adds, removes or alters.

## Use when
- explain: the diff changes a status enum, adds/removes a transition, or guards a transition with a new rule.
- present: the brief describes a lifecycle ("pending → allocated → picked → shipped") or asks what can move where.
Not for linear pipelines without branching — use the call path or a sequence diagram instead.

## Ask (present)
- Which transitions are new or blocked, and by what rule?
- Is there a terminal status, and can anything leave it?

## Extract (explain)
Statuses from the enum (head vs base), transitions from guard/assignment sites; cite each with `path:line`.
