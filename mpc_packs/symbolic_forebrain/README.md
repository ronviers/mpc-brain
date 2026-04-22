# symbolic_forebrain — rule-based planner

**Spec:** `SESSION-5-TASK-PROMPT-v2.md §AMEND-009` plus
`SESSION-5a-part2-TASK-PROMPT.md §D4` for the default rule library
thresholds and ordering.
**Pack version:** 0.1.0
**Status:** normative (first-class; not a transitional shim).

## Purpose

`SymbolicForebrain` reads `Metareasoner.snapshot(cid)` signals for each
registered cluster, evaluates a first-match-wins rule library, and
executes the chosen `Action` via three public mutation routes on the
target cluster (see config.py).

`Action` is a small dataclass with four `kind` values:
`"add_proposition"`, `"remove_proposition"`, `"rebudget"`, `"noop"`.

## Default rule library (§D4)

| # | Predicate                                           | Action               |
|---|-----------------------------------------------------|----------------------|
| 1 | `thermal_pressure > 0.3 ∧ under_budget > 0.3`       | rebudget × 1.5       |
| 2 | `exploration_saturation > 0.7`                      | add_proposition      |
| 3 | `distant_start > 0.6 ∧ len(handles) ≥ 1`            | remove_proposition   |
| 4 | `idle > 0.7 ∧ len(engines) ≥ 2`                     | rebudget × 0.7       |
| 5 | `True`                                              | noop                 |

A custom library can be injected via the `plan_library=` constructor
argument; TASK-5 (deferred to 5b) uses this hook for maze-specific rules.

## Declared mutations (RFC-002 §4.3)

Three, all via public cluster surface:
1. `cluster.load(...)` — add_proposition.
2. `cluster.ops.reset(handle, cluster.cluster_id)` + `cluster._handles.pop(pid)` — remove_proposition.
3. `cluster.local_budget = new` and per-engine `engine.E_star = new` — rebudget.

No direct writes to substrate internals, engine positions, or the bus.

## Declared dependencies (RFC-002 §3.2)

- `mpc_kernel.rfc001.events.EventBus` — kernel.
- `mpc_engine_rfc001.Network`         — kernel.
- `mpc_packs.metareasoner.Metareasoner` — same-layer pack.
- `mpc_packs.z3_socket.Z3SymbolicSocket` — same-layer pack.

## No-shadow note

Nothing in this pack redeclares kernel or sibling-pack types.
