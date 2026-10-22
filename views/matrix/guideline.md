# matrix

Cases × variants with what happens in each: what tests assert, or design rules; `untested` marks gaps.

## Use when
- explain: tests cover several cases or paths (flag on/off, old vs new); parity gaps matter.
- present: rules with example values ("order of 5 with 3 reserved → …").

## Ask (present)
- Which example values should the reader see?

## Extract (explain)
One row per asserted case (`ref` = test line), one column per path; cells yes|no|error|untested|n/a or {text, tone}.
