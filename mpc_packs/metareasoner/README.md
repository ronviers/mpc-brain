# metareasoner — event-driven signal computation

**Spec:** `SESSION-5-TASK-PROMPT-v2.md §AMEND-008`
**Pack version:** 0.1.0
**Status:** normative (first-class; not a transitional shim).

## Purpose

Computes five domain-agnostic signals per `cluster_id` from a stream of
`BudgetResetEvent` + `EffectorEvent` traffic on the bus:

| Signal                  | Intuition                                            |
|-------------------------|------------------------------------------------------|
| `under_budget`          | Landauer cost as a fraction of total cost.           |
| `distant_start`         | Mean work-estimate per commit, normalised by E*.     |
| `exploration_saturation`| Commits concentrated at the same position (tol 0.5). |
| `thermal_pressure`      | Reset rate over the window.                          |
| `idle`                  | Steps since last commit, normalised by window.       |

All signals clipped to [0, 1].

## Architectural role

Measurement-side (RFC-001 §7). Two subscriptions: `BudgetResetEvent` and
`EffectorEvent`. The forebrain reads snapshots via `snapshot(cluster_id)`
— the Metareasoner itself emits no actions and touches no brain state.

## Declared dependencies (RFC-002 §3.2)

- `mpc_kernel.rfc001.events.BudgetResetEvent` — kernel-defined.
- `mpc_kernel.rfc001.events.EventBus`         — kernel-defined.
- `mpc_session4.EffectorEvent`                — cross-pack import, sourced
  from the `persistence_substrate` pack's source module. Documented here
  per RFC-002 §3.2 cross-pack dependency policy.

## Declared mutations (RFC-002 §4.3)

None. Only private dicts keyed by `cluster_id`. The attached `EventBus`
is held as `_attached_bus` for diagnostics only.

## No-shadow note

`EventBus`, `BudgetResetEvent`, and `EffectorEvent` are imported, not
redeclared.
