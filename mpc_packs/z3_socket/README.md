# z3_socket — Z3-backed symbolic ObservationSocket

**Spec:** `SESSION-5-TASK-PROMPT-v2.md §AMEND-007`
**Pack version:** 0.1.0
**Status:** normative (first-class; not a transitional shim).

## Purpose

`Z3SymbolicSocket` encodes a proposition — given as a callable from Z3
variables to a list of `z3.BoolRef` conjuncts — into a `ConstraintSpec`
whose `fn` is a quadratic well centred at a satisfying point. Two
graceful-degradation branches: `symbolic_unsat` (Z3 returned unsat) and
`symbolic_eval_failed` (the `observe()` eval-dispatch path raised), both
with `fn ≡ 0.0`.

## Architectural role

Measurement-side. The socket holds neither Substrate nor Bus. A forebrain
calls `observe_symbolic(...)` and then `flush()` to extract specs; the
specs are passed to `cluster.load(...)` by the forebrain's `execute()`,
never by the socket itself.

## Declared dependencies (RFC-002 §3.2)

- `mpc_session3.ObservationSocket` — abstract base (inherited, not shadowed).
- `mpc_session3.ConstraintSpec`    — return record.
- `z3-solver` (third-party).

## Declared mutations (RFC-002 §4.3)

None. The only mutable state is `self._buffer: List[ConstraintSpec]`,
drained on each `flush()`.

## No-shadow note

`ConstraintSpec` and `ObservationSocket` are imported from `mpc_session3`
verbatim; this pack does not redeclare them.
