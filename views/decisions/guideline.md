# decisions

The checks a request goes through and the outcome of each: guards, failure reasons, flag forks.

## Use when
- explain: ≥ 3 distinct outcomes, or the order of checks matters (which fails first).
- present: rules about who may use what, fallbacks, shortages.
Signal: ≥ 3 new `raise` sites (`facts` reports them) — each is an outcome a reader should see.
Not for a single yes/no guard — say it in a node's explanation instead.

## Ask (present)
- In which order are the conditions checked?
- What happens on shortage / fallback — fail, partial, or take from elsewhere?

## Extract (explain)
Walk the guard chain in code order; leaves are outcomes (`tone` ok|err|plain, plain for enum reasons). Prefer test refs for outcomes.
