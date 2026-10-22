# sequence

Who talks to whom, in time order: API → command → database → events → external services.

## Use when
- explain: a new/changed operation crosses components, publishes events, calls external services, or the order of calls matters.
- present: the brief describes an interaction between systems ("receiving writes, picking reads").
Signal: an event payload changes (`facts` reports it) — show who publishes it and who consumes it.
Not when the call path already shows everything in order and no event or external call is involved.

## Ask (present)
- Which systems/actors take part, and which steps are new?
- Is there a branch (flag on/off, segmented vs not) worth framing?

## Extract (explain)
Actors from the call sites; steps in execution order with `kind` call|return|event|write|read and `status`; consecutive steps sharing `branch` get a frame. Cite each step.
