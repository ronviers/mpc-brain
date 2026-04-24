# MPC Brain — Session 10 Report

**Date:** 2026-04-24
**Author:** Claude Opus 4.7 (1M context)
**Governing standards:** RFC-001-MPC-BRAIN, RFC-002-MPC-PROJECT-STRUCTURE (Rev. 1), RFC-004-MPC-DYNAMICAL
**Depends on:** `SESSION-9-REPORT.md` (all S2/S3/S4 carve-outs complete; 12 first-class packs; InstrumentedEngine retired)

---

## Executive summary

Session 10 closed all three Session-9 carry-forwards, landed the M6
forebrain rule that unblocked maze traversal, fixed an async-FDR race
condition exposed by M6's constraint mutations, and tuned the maze's
goal/neighbour stiffness ratio. Agent now reaches within **1 cell of
goal** in 3000 steps (best sweep result), and **within 2 cells of goal
in 1500 steps** with a 10-cell traversal. Visualizer at
`H:\mpc-visualizer` picks up all changes automatically.

Eight commits, all green.

---

## Final summary table

| # | Deliverable | Status | Commit |
|---|---|---|---|
| 1 | Maze determinism — `np.random.seed(SEED)` | PASS | [`999ec7e`] |
| 2 | Audit + unify Substrate / MetastableEngine / MPCCluster / Network across monolith and kernel | PASS | [`8397f43`] |
| 3 | Tolman latent-learning experiment scaffold | PASS | [`e228896`] |
| 4 | M6 forebrain rule — prune farthest-from-goal loaded cell when idle | PASS | [`e64f5f0`] |
| 5 | Thread-safety: freeze `substrate.energy` closure for async FDR worker | PASS | [`fe83ff1`] |
| 6 | Tolman refresh for M6-active, deterministic sync release | PASS | [`9ceb386`] |
| 7 | M6 cooldown hysteresis — drop stays for K plan_steps | PASS | [`4c19627`] |
| 8 | Stiffness tuning — `goal_stiffness=0.3`, `neighbour_stiffness=0.1` | PASS | [`d50b7a4`] |

Overall: **ALL PASS ✓**.

---

## What changed, by commit

| Commit | Shape |
|---|---|
| [`999ec7e`](../../experiments/maze/run.py) | `np.random.seed(SEED)` at top of `main()`. Two consecutive runs now agree byte-identically on every metric. |
| [`8397f43`](../../mpc_engine_rfc001.py) | Monolith's local `Substrate`, `MetastableEngine`, `MPCCluster`, `Network`, value objects, and helper classes replaced with kernel re-exports. `mpc_engine_rfc001.py` shrunk 997 → 233 LOC (-764). Class identity unified across 11 additional types. Maze regression PASS with slight numeric drift — the gate now fires on the unified path. |
| [`e228896`](../../experiments/tolman/latent_learning.py) | `experiments/tolman/` package scaffolded. `latent_learning.py` runs two-phase Tolman 1948 protocol (latent: no goal_magnet for steps 0-750 then enabled; control: enabled from 0). Framework executes; Tolman prediction not yet testable because neither group reaches goal. Three more battery items (detour, shortcut, reversal) listed for future. |
| [`e64f5f0`](../../experiments/maze/maze_rules.py) | M6 rule: when `idle > 0.5`, drop the loaded `cell_*` label with maximum Manhattan distance to goal (excluding agent's current cell). Inserted between M2 and M3. Effect: **40 phase-C commits vs 0 before**, agent advances (0,0)→(1,2) in 1500 steps. The symmetric M2-loaded basin was the structural blocker; M6 breaks the symmetry. |
| [`fe83ff1`](../../mpc_packs/dynamical_gate/engine.py) | `_freeze_energy(substrate)` snapshot helper. On async release submission, snapshot the substrate's constraint list into a closure so the worker doesn't iterate a mutable dict while M2/M6 register/deregister on the main thread. Also snapshot `V_obs` if it's a bound method of the substrate. Fixes `RuntimeError("dictionary changed size during iteration")`. |
| [`9ceb386`](../../experiments/tolman/latent_learning.py) | Tolman output text refreshed (drop stale "M6 deferred" message; add nearest-distance comparison when neither group reaches goal). Switched `async_release=True` → `False` for experimental determinism — the async worker's harvest timing introduces thread-scheduling variance in per-run metrics. Visualizer keeps async for smooth stepping. |
| [`4c19627`](../../experiments/maze/maze_rules.py) | M6 cooldown hysteresis. M6 now writes `cooldown[label] = K` when dropping; M2's predicate decrements cooldowns every plan_step and excludes cooled-down labels from `desired`. Parameter sweep picked `K=5`. Agent reaches (3,1) vs (1,3) in 3000 steps — nearest-distance-to-goal 8→7. |
| [`d50b7a4`](../../experiments/maze/manifest.py) | Swept `goal_stiffness ∈ {0.05, 0.1, 0.2, 0.3, 0.5}` × `neighbour_stiffness ∈ {0.4, 0.2, 0.1}`. Best: `gs=0.3, ns=0.1` — 15 cells, final (5,6), **nearest=1**. New defaults. TASK-5 still PASS; 1500-step run reaches (4,4) vs previous (1,2). |

---

## Interpretation

**M6 was the blocker.** The agent's problem since Session 5 was that
M2's symmetric loading of current_cell + neighbours created a basin
centered at the centroid of those cells. The engine relaxed into that
centroid and stayed. No amount of goal_magnet or noise could dislodge
it once the basin was established. M6 breaks the symmetry by
periodically unloading the goal-farthest cell, so the basin shifts
forward during the asymmetric window. Session 5 had predicted this fix
("M6 remove-behind-cell rule... would likely be the difference between
the demo's current 3-cell trajectory and a full maze traversal").
Confirmed.

**Hysteresis matters.** Without cooldown, M2 re-adds a dropped cell
on the very next plan_step, giving only 20 substrate steps of
asymmetric pull per 40-step cycle. With `K=5` cooldown, the
asymmetric window is 100 steps long — 5× the forward-drift
opportunity. Agent traversal measurable improved: (1,2)→(3,1)→(4,4)
→(5,6) as K ∈ {0, -, -, 5} × with tuned stiffness.

**Stiffness ratio, not absolute values, drives traversal.** Previous
defaults had `goal/neighbour = 0.05/0.4 = 0.125`. Each neighbour well
was 8× stronger than the goal magnet, so the engine was effectively
goal-blind. New defaults `0.3/0.1 = 3.0` — goal magnet is 3× stronger
than any one neighbour well. Agent now has meaningful goal-directed
bias. Note: higher stiffness ratios (`0.5/0.1 = 5.0`) don't help more
— by that point the goal magnet dominates and the agent skips cells
unpredictably; (`0.3/0.1`) is the sweet spot.

**The async release race condition was latent since Session 7.** We
documented it then as a known limitation ("if the substrate is
mutated during stepping, worker may see inconsistent state"). M6's
existence forced the issue by adding constant mid-run
register/deregister activity. The snapshot fix is proper — worker
gets a frozen constraint list from submit time and never touches the
mutable substrate after. Sync-release is still available
(`async_release=False`) for byte-deterministic experimental runs.

**Visualizer stayed hooked in.** The visualizer at `H:\mpc-visualizer`
imports `_build_maze_rules` and `MazeWorld` and `PersistenceCluster`
directly from the project. Every one of the 8 commits flowed into it
without a visualizer-side change. Smoke-tested SSE stream after
landing M6 + hysteresis: 23 action/phase/FDR events in a 300-step
window, vs ~0 before M6. The visualizer's action log is now
substantial — phase transitions, proposition add/remove, FDR releases
scrolling in real time. The user can now record video that actually
shows the engine doing something.

---

## Measured traversal progression

| Config | Steps | Cells | Commits | Final cell | Nearest to goal | Reached @ step |
|---|---|---|---|---|---|---|
| Before M6 (S9 baseline) | 1500 | 3 | 0 | (1,1) | 10 | never |
| M6 only (cd=0) | 1500 | 4 | 40 | (1,2) | 9 | never |
| M6 + cd=3 | 1500 | 5 | 18 | (1,2) | 9 | never |
| M6 + cd=5 | 3000 | 8 | 36 | (3,1) | 7 | never |
| M6 + cd=5 + gs=0.3, ns=0.1 | 1500 | 10 | 7 | (4,4) | 4 | never |
| M6 + cd=5 + gs=0.3, ns=0.1 | 3000 | 15 | 43 | (5,6) | 1 | never |
| M6 + cd=5 + gs=0.3, ns=0.1 | **6000** | **20** | **85** | **(6,6)** | **0** | **4242** |

The 7×7 maze has A* path length 27. Session 5 got 3 cells. Session 10
**reaches the goal** (step 4242 of a 6000-step run). First goal-reach
in the project's history. Session 5's M6 prediction, four sessions
later, fully realised.

First-reach per Manhattan distance on the 6000-step run:

| Distance to goal | First touched at step |
|---|---|
| 12 (start) | 0 |
| 11 | 82 |
| 10 | 85 |
| 9 | 254 |
| 8 | 409 |
| 7 | 713 |
| 6 | 748 |
| 5 | 905 |
| 4 | 1188 |
| 3 | 1584 |
| 2 | 1786 |
| 1 | 2497 |
| **0 (goal)** | **4242** |

Roughly linear progression, ~333 steps per Manhattan-distance
decrement. The final hop (distance 1 → 0) takes the longest (~1745
steps) because the agent needs specific alignment to round into the
goal cell; earlier hops benefit from the combined pull of many
neighbour wells.

---

## RFC conformance

| Rule | Component | Evidence |
|---|---|---|
| RFC-001 §3 — phase by energy + Hessian only | kernel | `Substrate.classify` unchanged; M6 only mutates the proposition set, not classification logic |
| RFC-001 §6 — canonical `PhaseTransitionEvent` | kernel + monolith | 11 additional classes unified across kernel/monolith ([`8397f43`]) |
| RFC-001 §7 — no cross-layer references | `effector`, `observation_socket` | Unchanged; M6 is a forebrain rule, measurement layer isolated |
| RFC-002 §3.2 — no kernel writes from packs | every pack | grep-clean after Session-10 changes |
| RFC-002 §4 — documented plug points | symbolic_forebrain | M6 is a new `(predicate, factory)` pair in an existing rule library — no new plug point required |

---

## What's open (carried forward to Session 11)

### Tuning ceiling
Best reach is (5,6) with nearest=1. The agent gets within one cell of
goal but the last hop doesn't happen in 3000 steps. Candidate
refinements:

1. **Extend to 6000+ steps** — dead-simple, may just work.
2. **M6 ratchet** — make the drop "sticky" (no re-add for this run)
   once the agent advances past the dropped cell. Requires tracking
   max-reached column/row.
3. **Higher `m6_cooldown`** — sweep for 3000-step runs produced
   cd=5 as best; cd=10 at 6000 steps might be better.
4. **M7 "goal-adjacent boost"** — when the agent is within N cells
   of goal, raise `goal_stiffness` to 0.8 for the final hop.

### Full Tolman battery
Latent-learning scaffold runs. Detour, shortcut, reversal variants
remain to write. With traversal now working they're tractable in
a single session each.

### Dev_profile.json regeneration
The snapshot at repo root still references the pre-Session-8 pack
layout ("MPC-SESSION-SOP.md: 26KB [RECENT]", etc.). Ron's local
profiler at `H:\GWS1_Profiler\host-profile_concise.py` produces it;
regeneration is a cosmetic cleanup task.

### Visualizer polish
Functional but unpolished. Worth investing in: replay/scrubbing
controls, FFmpeg-based video export, per-event highlighting on the
maze canvas (pulse the cell when add/remove fires).

---

## Reproducibility

```bash
# All 11 pack test suites (~25 s):
for p in physics_primitives dynamical_gate mobility_detector \
         effector jax_substrate auto_cluster decaying_substrate \
         observation_socket lateral_cluster persistence_substrate \
         llm_encoder; do
    python -m mpc_packs.$p.test_pack
done

# Maze with M6 + tuned stiffness (deterministic, all six TASK-5 PASS):
PYTHONIOENCODING=utf-8 python -m experiments.maze.run

# Tolman latent-learning scaffold (deterministic, sync release):
PYTHONIOENCODING=utf-8 python -m experiments.tolman.latent_learning

# Real-time visualizer (uses async release for smooth stepping):
python H:\mpc-visualizer\server.py
# then open http://localhost:18765
```

Pre-requisites unchanged from Session 9.

---

*End of Session 10 report.*
