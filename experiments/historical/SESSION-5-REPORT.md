# MPC Brain — Session 5 Report (5a + 5b combined)

**Date:** 2026-04-21
**Author:** Claude Opus 4.7 (Session 5b)
**Governing standards:** RFC-001-MPC-BRAIN, RFC-002-MPC-PROJECT-STRUCTURE
**Task prompts:** `SESSION-5-TASK-PROMPT-v3.md` (master), `SESSION-5-TASK-PROMPT-v2.md` (authoritative for TASK-5 mechanics), `SESSION-5b-TASK-PROMPT.md` (this session's execution contract)
**Depends on:** `SESSION-5a-REPORT.md` (all eight 5a rows PASS)

---

## Executive summary

Session 5 is complete. Session 5a carved the kernel scaffold, built the three new packs (z3_socket, metareasoner, symbolic_forebrain), and landed two transitional shims (decaying_substrate, persistence_substrate). Session 5b wired those packs around a 7×7 procedurally-generated maze, ran a 1500-step closed-loop substrate step + plan_step demo, and produced the 4-panel evidence figure.

**All seven Final-Summary rows PASS. TASK-5 passes all six sub-criteria.**

---

## Final summary table (v3 §end)

```
KERNEL-SURGERY  PhaseTransitionEvent canonical form         PASS   (carried from 5a)
KERNEL-LAYOUT   Directory scaffold per RFC-002 §6           PASS   (carried from 5a)
AMEND-007       Z3SymbolicSocket pack                       PASS   (carried from 5a)
AMEND-008       Metareasoner pack                           PASS   (carried from 5a)
AMEND-009A      SymbolicForebrain predicates                PASS   (carried from 5a)
AMEND-009B      SymbolicForebrain execute                   PASS   (carried from 5a)
TASK-5          Maze navigation closed-loop demo            PASS   (this session)

Overall: ALL PASS ✓
```

Rows 1–6 evidence: `SESSION-5a-REPORT.md` §§Final Results, §KERNEL-SURGERY, §KERNEL-LAYOUT, §AMEND-007, §AMEND-008, §AMEND-009. Tests re-runnable via `python3 mpc_packs/<pack>/test_pack.py`.

---

## TASK-5 — Maze Navigation Closed-Loop Demo

### Configuration (v2 §TASK-5 Configuration block, verbatim)

```
MAZE_W, MAZE_H      = 7, 7
DIM                 = 4
E_STAR_init         = 8.0
MAX_ENGINES         = 2
tau_base            = 200.0
usage_coefficient   = 1.0
outcome_coefficient = 0.3
N_STEPS             = 1500
PLAN_INTERVAL       = 20
window              = 50         # Metareasoner window
GOAL_STIFFNESS      = 0.05       # broad attractor (well_width=0.1)
NEIGHBOUR_STIFFNESS = 0.4        # strong wells at adjacent cells (well_width=1.0)
E_c, E_s            = 0.5, 3.0
seed                = 2026
```

### Sub-criteria (v2 §TASK-5 / v3 §4.3)

| ID         | Description                                              | Result | Evidence                                                                |
|------------|----------------------------------------------------------|--------|-------------------------------------------------------------------------|
| TASK-5.1   | No crash over N_STEPS substrate steps                    | PASS   | 1500/1500 steps completed                                               |
| TASK-5.2   | plan_step() called ≥ ⌊N_STEPS / PLAN_INTERVAL⌋ − 1       | PASS   | 74 plan_step() calls ≥ 74 (tight match: fires on steps 20, 40, …, 1480) |
| TASK-5.3   | At least one non-noop action                             | PASS   | 8 non-noop actions: 6 × add_proposition, 2 × remove_proposition          |
| TASK-5.4   | Cluster has at least one constraint at end of run        | PASS   | 4 handles at end: cell_1_0, cell_1_1, cell_1_2, goal_magnet              |
| TASK-5.5   | Plot saved at experiments/maze/artifacts/maze_demo.png   | PASS   | 125.6 KB PNG, 4 panels, non-empty                                        |
| TASK-5.6   | Agent visited ≥ 3 distinct maze cells                    | PASS   | 3 distinct cells visited: {(0,0), (1,0), (1,1)}                          |

**TASK-5 overall: PASS**

### Informational metrics (v3 §4.4)

| Metric                                      | Value                                                                                            |
|---------------------------------------------|--------------------------------------------------------------------------------------------------|
| Final agent cell                            | (1, 1)                                                                                           |
| Goal cell                                   | (6, 6)                                                                                           |
| Reached goal                                | False                                                                                            |
| Distinct cells visited                      | 3                                                                                                |
| A* optimal path length                      | 27 cells                                                                                         |
| EffectorEvent count                         | 0                                                                                                |
| Action histogram (by kind)                  | {add_proposition: 6, remove_proposition: 2, rebudget: 0}                                         |
| Final Metareasoner signals                  | under_budget=0.0, distant_start=0.0, exploration_saturation=0.0, thermal_pressure=0.0, idle=1.0  |
| Final cluster.local_budget                  | 8.0                                                                                              |
| Final handles                               | cell_1_0, cell_1_1, cell_1_2, goal_magnet                                                        |

**Interpretation.** The closed loop is healthy: the substrate advanced the engine from (0,0) to (1,1) by gradient descent on the superposition of the goal magnet and the neighbourhood wells that M2 progressively loaded as the agent crossed cell boundaries. No commitments (phase-C transitions) fired during the run — the configured E_c = 0.5 is below the residual energy the engine experiences at the compromise point between its 3-to-4 active wells — so `n_effector_events = 0` and cumulative `total_cost` stays at zero. This is consistent with the acceptance contract: goal-reaching and commitment are explicitly informational (v2 §TASK-5 "Informational" section, v3 §4.3).

The forebrain fired correctly: M1 loaded goal_magnet once (step 20), then M2 fired repeatedly to load `cell_0_0`, its neighbours, and follow-ups as focus advanced. M3 (2-hop expansion) fired briefly around step 500 under `idle > 0.5 ∧ exploration_saturation > 0.7`. M4 never fired (no reset pressure). M5 (noop) covered the rest.

### Known deferred-to-later refinements

- **Phase-C commitments do not fire in this parameterisation.** The engine settles above E_c. To get commits, one of: lower E_c to e.g. 0.15; raise NEIGHBOUR_STIFFNESS to e.g. 1.0; increase well separation by scaling cell coordinates. The maze demo's acceptance doesn't require commits, but Session 7's Tolman experiments will.
- **Agent does not traverse the maze.** The combined-well attractor basin for the loaded 3–5-cell neighbourhood is narrow; the engine reaches the local minimum and stays. Remedies: a stronger goal magnet, an M6 rule that removes the "behind" cell from the loaded set once the agent advances, or a non-zero stochastic diffusion term. Deferred to Session 6 / Session 7.
- See also the v3 "What's deferred" list, item §5 (auto-scale E_STAR to constraint magnitude) — likely the cleanest fix.

---

## RFC-001 + RFC-002 conformance checklist (v3 §end)

| Rule                                                       | Component               | Evidence                                                            |
|------------------------------------------------------------|-------------------------|---------------------------------------------------------------------|
| RFC-001 §3 — phase by energy + Hessian only                | kernel (unchanged)      | `MetastableEngine.classify` inherited; no override in 5a/5b         |
| RFC-001 §3.2 — every reset emits LandauerEvent             | kernel (unchanged)      | `MetastableEngine._trigger_reset` inherited                         |
| RFC-001 §7 — measurement holds no Substrate/Bus            | metareasoner            | bus stored only as `_attached_bus` (mpc_packs/metareasoner/pack.py) |
| RFC-001 §7 — measurement does not write to landscape       | metareasoner            | handlers only update internal dicts; no outbound calls              |
| RFC-001 §7 — observation socket holds neither              | z3_socket               | Z3 `Real` vars are sole external state (mpc_packs/z3_socket/pack.py) |
| RFC-002 §3.2 — pack does not modify kernel files           | all three packs         | grep-clean: zero writes to `mpc_kernel/` or `mpc_engine_rfc001.py`  |
| RFC-002 §3.2 — pack does not shadow kernel types           | all three packs         | event types are imported from kernel, not redeclared                |
| RFC-002 §3.2 — pack declares dependencies                  | symbolic_forebrain      | `DECLARED_DEPENDENCIES` in `mpc_packs/symbolic_forebrain/config.py` |
| RFC-002 §4.3 — Governor declares mutations                 | symbolic_forebrain      | `DECLARED_MUTATIONS` (3 routes) in config.py                        |
| RFC-002 §3.3 — experiment declares kernel ver + manifest   | maze experiment         | `experiments/maze/manifest.py` (`KERNEL_REQUIRED = "0.4.0"`)        |

---

## Step-0 caveats inherited from 5a (non-blocking)

Three informational caveats were flagged in `SESSION-5a-REPORT.md` and carry over:

- **C1** — `PhaseTransitionEvent.energy` pre-update-vs-post-update semantic ambiguity. The kernel now emits post-update energy; a pre-update consumer would need to adjust. No 5b consumer uses this field. (Does not affect TASK-5 acceptance.)
- **C2** — `PhaseTransitionEvent.energy` has no kernel-side default. All emitters fill it explicitly. No missing-field crash surfaced in 5b.
- **C3** — No `engine_id` field on PhaseTransitionEvent. The Metareasoner and Effector both key by `cluster_id` only, which is adequate for single-cluster experiments like TASK-5. Session 8 (parallel mazes) will need per-engine provenance.

---

## Artefacts

### Produced in Session 5a (carried into `session5_final.zip`)

| Path                                              | Purpose                                                                 |
|---------------------------------------------------|-------------------------------------------------------------------------|
| `mpc_kernel/__version__.py`                       | `__version__ = "0.4.0"` — canonical post-Step-0 version                 |
| `mpc_kernel/__init__.py`                          | Package marker, re-exports `__version__`                                |
| `mpc_kernel/rfc001/events.py`                     | Kernel event type shim (re-exports from `mpc_engine_rfc001`)            |
| `mpc_packs/z3_socket/`                            | AMEND-007 (Z3SymbolicSocket) — first-class pack                         |
| `mpc_packs/metareasoner/`                         | AMEND-008 (Metareasoner) — first-class pack                             |
| `mpc_packs/symbolic_forebrain/`                   | AMEND-009 (SymbolicForebrain) — first-class pack                        |
| `mpc_packs/decaying_substrate/`                   | S3 transitional shim (re-exports `DecayingSubstrate` from mpc_session3) |
| `mpc_packs/persistence_substrate/`                | S4 transitional shim (re-exports `PersistenceCluster`/`Effector`/`InstrumentedEngine`/`EffectorEvent` from mpc_session4) |

### Produced in Session 5b (this session)

| Path                                             | Purpose                                                             |
|--------------------------------------------------|---------------------------------------------------------------------|
| `experiments/__init__.py`                        | Top-level experiments package marker                                |
| `experiments/maze/__init__.py`                   | Maze experiment package marker                                      |
| `experiments/maze/manifest.py`                   | RFC-002 §3.3 kernel-version guard + pack manifest + EXPERIMENT_CONFIG |
| `experiments/maze/maze_world.py`                 | Procedural 7×7 recursive-backtracker maze + A* oracle + ASCII render |
| `experiments/maze/maze_rules.py`                 | Five-rule maze-specific plan_library (M1–M5) for SymbolicForebrain  |
| `experiments/maze/run.py`                        | 1500-step closed-loop driver + trace arrays + acceptance + 4-panel plot |
| `experiments/maze/artifacts/maze_demo.png`       | 4-panel evidence figure (maze+trajectory, signals, handles/budget, cost+actions) |
| `experiments/maze/report.md`                     | This report (Session 5 wide; carries 5a rows + 5b new row)          |

---

## What's open (carried forward to Session 6)

From v3 "What's deferred" §end, plus items surfaced this session:

1. **Carve out S2/S3/S4 contents into first-class packs.** Replace the two transitional shims (`decaying_substrate`, `persistence_substrate`) and add `jax_substrate`, `auto_cluster`, `llm_encoder`, `lateral_cluster`, `anthropic_socket`, `effector`, `persistence_cluster`. Reference: RFC-002 §5 / v3 §"What's deferred" items 1–3.
2. **Auto-scale E_STAR to constraint magnitude** (v3 item 5). Likely the cleanest remedy for the "no commits fire" observation in this demo.
3. **Remove the backward-compat shim in `mpc_engine_rfc001.py`.** All callers should import from `mpc_kernel.rfc001` after the carve-out.
4. **Sliding-window EffectorEvent retention** (v3 item 6).
5. **Forebrain action provenance** — add `origin` field to LandauerEvent, threaded through Action (v3 item 7).
6. **New this session** — optional M6 rule ("remove-behind-cell") that culls a no-longer-adjacent well as the agent advances. Would likely be the difference between the demo's current 3-cell trajectory and a full maze traversal. Holding for Session 7 where Tolman experiments need goal-reaching.
7. **New this session** — engine-level provenance on `PhaseTransitionEvent` / `EffectorEvent`. Required for Session 8 (parallel mazes).

---

## Reproducibility

```bash
cd <repo_root>
python3 -m experiments.maze.run
```

Requirements: `numpy`, `scipy`, `matplotlib`, `z3-solver`, and the 5a pack suite (`mpc_packs/`) on `sys.path` along with the four legacy session files (`mpc_engine_rfc001.py`, `mpc_session2.py`, `mpc_session3.py`, `mpc_session4.py`) that the transitional shims re-export from. No API keys required.

---

*End of Session 5 report.*
