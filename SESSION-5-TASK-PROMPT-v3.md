# MPC Brain — Session 5 Task Prompt (v3 — RFC-002 structure)

**Date issued:** 2026-04-17
**Supersedes:** SESSION-5-TASK-PROMPT-v2.md (the monolith)
**Governing standards:** RFC-001-MPC-BRAIN, RFC-002-MPC-PROJECT-STRUCTURE
**Prerequisites:** existing baseline (`mpc_engine_rfc001.py`, `mpc_session2.py`, `mpc_session3.py`, `mpc_session4.py`)
**Dependencies:** Z3 (`pip install z3-solver --break-system-packages`)
**No LLM dependency.** `ANTHROPIC_API_KEY` is not required and not used.

---

## Why v3

v2 specified Session 5 as a single `mpc_session5.py` file containing three new amendments plus the maze world plus the rule library plus the demo plus the plot generator. That pattern — accepted in S2 through S4 — is what produced the technical debt RFC-002 exists to stop.

v3 is the same Session 5 work, refiled under RFC-002. The technical specifications for the Z3 socket, the Metareasoner signal computations, the SymbolicForebrain rules, and the MazeWorld helper are unchanged from v2; what changes is where the code lives and how it composes. Where v3 says "as v2 §X," consult v2 for the exact specification — those sections are normative carryover.

The maze pivot is a defining step. v3 ensures that defining step lands as the first session executed under RFC-002, so the project's shape changes alongside its scientific scope.

---

## Output deliverables

```
mpc_kernel/                                     [Step 0 — directory scaffold]
   __version__.py                               kernel version "0.4.0"
   rfc001/
      events.py                                 PhaseTransitionEvent w/ energy field

mpc_packs/
   z3_socket/                                   [Step 1]
      __init__.py
      pack.py                                   Z3SymbolicSocket class
      config.py                                 Z3SocketConfig dataclass
      test_pack.py                              test_amend007()
      README.md
   metareasoner/                                [Step 2]
      __init__.py
      pack.py                                   Metareasoner class
      config.py                                 MetareasonerConfig dataclass
      test_pack.py                              test_amend008()
      README.md
   symbolic_forebrain/                          [Step 3]
      __init__.py
      pack.py                                   Action, SymbolicForebrain, _default_rules
      config.py                                 ForebrainConfig dataclass
      test_pack.py                              test_amend009() Tests A and B
      README.md

experiments/
   maze/                                        [Step 4]
      __init__.py
      manifest.py                               kernel ver + pack manifest + config
      maze_world.py                             MazeWorld helper (domain-specific)
      run.py                                    the 1500-step demo driver
      report.md                                 SESSION-5-REPORT
      artifacts/
         maze_demo.png                          the 4-panel plot
```

The single file `mpc_session5.py` is **not** a deliverable. If you find yourself writing it, stop and re-read RFC-002 §3.

---

## Step 0 — Kernel surgery (blocking)

This is the only kernel modification required by Session 5. It exists because the S4 shadow `PhaseTransitionEvent` is not RFC-002 conformant (a pack shadowing a kernel type is forbidden by §3.2). The fix is small.

### 0.1 PhaseTransitionEvent canonical form

In `mpc_engine_rfc001.py` (which will move to `mpc_kernel/rfc001/events.py` under Step 0.3), modify the `PhaseTransitionEvent` dataclass:

```python
@dataclass
class PhaseTransitionEvent:
    cluster_id: str
    engine_id: str
    from_phase: Phase
    to_phase: Phase
    position: np.ndarray
    timestamp: float
    energy: float = 0.0          # NEW — added for AMEND-005 (Effector)
```

The field has a default of `0.0` so any pre-existing emitter that does not populate it remains valid. New emitters (and `MetastableEngine.step` itself, see 0.2) MUST populate it.

### 0.2 MetastableEngine.step populates energy

In `MetastableEngine.step`, when a `PhaseTransitionEvent` is emitted, populate `energy` with `self.sub.energy(self.v)` evaluated at the transition position. The S4 `InstrumentedEngine` (which exists only to do this) becomes obsolete and SHOULD be deleted from the carved-out S4 pack when that pack is filed.

### 0.3 Directory scaffold

Create the three top-level directories:

```
mpc_kernel/
mpc_packs/
experiments/
```

Move `mpc_engine_rfc001.py` to `mpc_kernel/rfc001/` and split it by class into the files listed in RFC-002 §6 (`phase.py`, `substrate.py`, `engine.py`, `cluster.py`, `network.py`, `bus.py`, `events.py`). Add a `mpc_kernel/__init__.py` that re-exports the canonical names so existing imports `from mpc_engine_rfc001 import ...` continue to work via a backward-compat shim:

```python
# mpc_engine_rfc001.py  (post-migration shim)
import warnings
warnings.warn(
    "Importing from mpc_engine_rfc001 is deprecated; use mpc_kernel.rfc001",
    DeprecationWarning, stacklevel=2,
)
from mpc_kernel.rfc001.phase import *           # noqa: F401, F403
from mpc_kernel.rfc001.substrate import *       # noqa: F401, F403
# ... etc.
```

The shim deprecates with one revision of grace; it is removed in a future RFC-002 revision after S2-S4 carve-out is complete.

`mpc_session2.py`, `mpc_session3.py`, and `mpc_session4.py` are **not** modified or moved by Step 0. Their carve-out into packs is a separate housekeeping task tracked in §"What's deferred" below. They continue to function unchanged because the shim preserves their imports.

### 0.4 Acceptance for Step 0

```
KERNEL-SURGERY    PhaseTransitionEvent has energy field         PASS/FAIL
KERNEL-SURGERY    MetastableEngine.step populates energy        PASS/FAIL
KERNEL-LAYOUT     mpc_kernel/, mpc_packs/, experiments/ exist   PASS/FAIL
KERNEL-SHIM       Existing S2/S3/S4 imports still work          PASS/FAIL
```

All four MUST pass before proceeding to Step 1.

---

## Step 1 — z3_socket pack

### 1.1 Plug point

`SubstrateExtension`-adjacent observation pack. Conforms to the `ObservationSocket` interface defined in S3 (AMEND-004); operationally an `EventSubscriber` that does not subscribe to events but does emit constraint specs into a cluster.

### 1.2 Files

`mpc_packs/z3_socket/pack.py` — the `Z3SymbolicSocket` class. Specification unchanged from **v2 §AMEND-007** (Z3 boolean variables, `observe_symbolic(label, formula_callable)`, `flush()` returning `List[ConstraintSpec]`, RFC-001 §7 compliance: holds no Substrate or Bus reference).

`mpc_packs/z3_socket/config.py`:
```python
@dataclass
class Z3SocketConfig:
    declared_dependencies: List[str] = field(default_factory=list)  # none for this pack
    z3_timeout_ms: int = 5000
```

`mpc_packs/z3_socket/test_pack.py` — `test_amend007()` exactly as v2 specifies it.

`mpc_packs/z3_socket/README.md` — pack interface, dependencies (none), status (new in S5), examples.

### 1.3 Acceptance

```
AMEND-007    Z3SymbolicSocket conforms to ObservationSocket    PASS/FAIL
PACK-CONFORM RFC-002 §3.2 + §7.2                                PASS/FAIL
```

---

## Step 2 — metareasoner pack

### 2.1 Plug point

`EventSubscriber`. Subscribes to `BudgetResetEvent` and `EffectorEvent`. RFC-001 §7 compliance: holds no Substrate, Engine, Cluster, or Effector reference.

### 2.2 Files

`mpc_packs/metareasoner/pack.py` — the `Metareasoner` class. Five signals, signal definitions, `attach`/`detach`/`tick`/`snapshot` interface — all exactly as **v2 §AMEND-008**. Carry over the signal formulas verbatim:

```
under_budget(c)            = _landauer_total[c] / max(_total_cost_total[c], 1e-9)
distant_start(c)           = mean(work_estimates) / _known_e_star[c]
exploration_saturation(c)  = (max bucket count) / len(_commit_history[c])
thermal_pressure(c)        = len(_reset_history[c]) / window
idle(c)                    = _steps_since_commit[c] / window
```

All clipped to `[0, 1]`.

`mpc_packs/metareasoner/config.py`:
```python
@dataclass
class MetareasonerConfig:
    declared_dependencies: List[str] = field(default_factory=list)
    window: int = 50
    bucket_tolerance: float = 0.5
```

`mpc_packs/metareasoner/test_pack.py` — `test_amend008()` exactly as v2 specifies (the five-signal injection test with the documented expected values).

`mpc_packs/metareasoner/README.md` — pack interface, no dependencies, signal definitions, intended use cases.

### 2.3 Acceptance

```
AMEND-008    Metareasoner produces five signals correctly       PASS/FAIL
PACK-CONFORM RFC-002 §3.2 + §7.2                                PASS/FAIL
```

---

## Step 3 — symbolic_forebrain pack

### 3.1 Plug point

`Governor`. Reads signals from a `Metareasoner`, observes a `Network`, emits `Action` mutations through `cluster.load`, `cluster.local_budget`, `cluster.shed_load`, and `cluster.ops.reset`. RFC-002 §4.3: declared dependencies on `metareasoner` and `z3_socket` (the symbolic socket is needed by `add_proposition` actions).

### 3.2 Files

`mpc_packs/symbolic_forebrain/pack.py` — the `Action` dataclass and `SymbolicForebrain` class. Specification unchanged from **v2 §AMEND-009**:

- `Action(kind, cluster_id, payload)` with the four payload schemas (add_proposition, remove_proposition, rebudget, noop).
- `SymbolicForebrain(network, metareasoner, symbolic_socket, plan_library=None)`.
- `plan_step()` returns `{cluster_id: Action}` for every registered cluster.
- `execute(action)` performs the four mutation kinds as v2 §AMEND-009 specifies.
- `_default_rules()` provides the five generic rules (under-budgeted thermal stress; exploration stalled; distant_start drop hardest; idle over-provisioned downbudget; catch-all noop).

`mpc_packs/symbolic_forebrain/config.py`:
```python
@dataclass
class ForebrainConfig:
    declared_dependencies: List[str] = field(default_factory=lambda: ["metareasoner", "z3_socket"])
    declared_mutations: List[str] = field(
        default_factory=lambda: ["load", "local_budget", "shed_load", "ops.reset"]
    )
    plan_library: Optional[List[Tuple[Callable, Callable]]] = None
```

The `declared_mutations` list is a new requirement under RFC-002 §4.3 (a Governor MUST declare which cluster-level mutations it performs). Maze-specific rule libraries inject through `plan_library`; defaults are exercised by `test_pack.py`.

`mpc_packs/symbolic_forebrain/test_pack.py` — `test_amend009()` Tests A (predicate firing, all five rules) and B (execute side effects), exactly as v2.

`mpc_packs/symbolic_forebrain/README.md` — pack interface, dependencies, the contract that rule libraries are domain-specific and swappable, examples.

### 3.3 Acceptance

```
AMEND-009A   Predicate firing — all five default rules          PASS/FAIL
AMEND-009B   execute side effects — add and remove              PASS/FAIL
PACK-CONFORM RFC-002 §3.2, §4.3, §7.2                            PASS/FAIL
```

---

## Step 4 — maze experiment

### 4.1 Why filed as experiment, not pack

`MazeWorld` is domain-specific to maze navigation. RFC-002 §3.2 requires that a pack be reusable across experiments; until a second experiment depends on `MazeWorld` (e.g., the proposed Tolman battery in S7), it stays in `experiments/maze/`. If S7 lands and uses it unchanged, it graduates to a pack at that point per §5.1.

The maze-specific rule library that the SymbolicForebrain consumes is similarly domain-specific. It lives in `experiments/maze/maze_rules.py`, NOT in the forebrain pack. This is the architectural statement the maze pivot makes explicit: the forebrain is generic infrastructure; rule libraries are domain-specific and live with their experiment.

### 4.2 Files

`experiments/maze/manifest.py`:
```python
from mpc_kernel import __version__ as KERNEL_VERSION

KERNEL_REQUIRED = "0.4.0"   # the post-Step-0 kernel
DEFAULT_PACKS_DISABLED = []  # all defaults loaded
PACKS = [
    ("decaying_substrate",   {}),                              # S3 carve-out
    ("persistence_substrate", {"usage_coef": 1.0,
                               "outcome_coef": 0.3,
                               "tau_base": 200.0}),            # S4 carve-out
    ("z3_socket",            {}),                               # S5 new
    ("metareasoner",         {"window": 50,
                              "bucket_tolerance": 0.5}),        # S5 new
    ("symbolic_forebrain",   {"plan_library": maze_rules}),     # S5 new
]
EXPERIMENT_CONFIG = {
    "maze_w": 7, "maze_h": 7,
    "dim": 4,
    "e_star_init": 8.0,
    "max_engines": 2,
    "n_steps": 1500,
    "plan_interval": 20,
    "goal_stiffness": 0.05,
    "neighbour_stiffness": 0.4,
}
```

If a pack referenced above (`decaying_substrate`, `persistence_substrate`) has not been carved out from S3/S4 yet, the experiment manifest MAY use a transitional shim that imports from the legacy session files. Note this in `experiments/maze/README.md` so the carve-out gets prioritised.

`experiments/maze/maze_world.py` — the `MazeWorld` class with all six methods. Specification unchanged from **v2 §TASK-5 → MazeWorld**. Pure utility, no MPC dependency.

`experiments/maze/maze_rules.py` — the maze-specific rule library that the SymbolicForebrain consumes. Specification carried over from v2's TASK-5 wiring section: rules that translate maze state (current cell, neighbour set, goal direction) into add/remove/rebudget actions.

`experiments/maze/run.py` — the 1500-step driver. Wires the manifest, runs the loop, populates trace arrays, calls the plot generator. Specification unchanged from **v2 §TASK-5**.

`experiments/maze/artifacts/maze_demo.png` — the 4-panel plot:
1. Maze + agent path overlay (with A* reference path)
2. Five Metareasoner signals over time
3. Constraint count + cluster.local_budget over time
4. Cumulative EffectorEvent total_cost with action-log markers

Unchanged from v2 §TASK-5 → "Plot."

`experiments/maze/report.md` — the session report. Structure follows the SESSION-N-REPORT.md format used in S2-S4: Final Results table, per-component sections, RFC-001 invariant checklist (now with RFC-002 conformance checklist alongside), artefacts list, what is open.

### 4.3 Acceptance — TASK-5 (unchanged from v2)

All six hard criteria from v2 §TASK-5 apply:

```
TASK-5.1   No crash over N_STEPS substrate steps                            PASS/FAIL
TASK-5.2   plan_step() called >= floor(N_STEPS / PLAN_INTERVAL) - 1 times   PASS/FAIL
TASK-5.3   At least one non-noop action executed                            PASS/FAIL
TASK-5.4   Cluster has at least one constraint at end of run                PASS/FAIL
TASK-5.5   Plot saved at experiments/maze/artifacts/maze_demo.png           PASS/FAIL
TASK-5.6   Agent visited at least 3 distinct maze cells                     PASS/FAIL
```

The rationale for criterion 6 from v2 stands: that's the weakest end-to-end "this actually navigated" check possible, and proves the entire feedback loop closes (Z3 → substrate → effector → metareasoner → forebrain → cluster mutation).

Optimal pathfinding is not in scope for S5. It is a Session 7+ concern.

### 4.4 Informational (printed but not part of PASS/FAIL)

Same as v2: agent's final cell vs goal, unique cells visited vs A* optimal length, EffectorEvent count, action histogram by kind, final signal snapshot, did the agent reach the goal.

---

## Implementation order

1. **Step 0** — Kernel surgery and directory scaffold. Verify all four Step-0 acceptance criteria pass before touching any pack.
2. **Step 1** — `z3_socket` pack. Run `test_amend007()` to green.
3. **Step 2** — `metareasoner` pack. Run `test_amend008()` to green.
4. **Step 3** — `symbolic_forebrain` pack. Run `test_amend009()` Tests A and B to green.
5. **Step 4 (transitional setup)** — If `decaying_substrate` and `persistence_substrate` are not yet carved out from S3/S4, create transitional shims in `mpc_packs/decaying_substrate/pack.py` and `mpc_packs/persistence_substrate/pack.py` that re-export from the legacy session modules. These are temporary and flagged for replacement in S6 housekeeping.
6. **Step 4 (continued)** — `experiments/maze/`. Build `maze_world.py`, `maze_rules.py`, `manifest.py`, `run.py`. Generate the plot. Write `report.md`.

---

## Final summary table (in report.md)

```
KERNEL-SURGERY  PhaseTransitionEvent canonical form         PASS/FAIL
KERNEL-LAYOUT   Directory scaffold per RFC-002 §6           PASS/FAIL
AMEND-007       Z3SymbolicSocket pack                       PASS/FAIL
AMEND-008       Metareasoner pack                           PASS/FAIL
AMEND-009A      SymbolicForebrain predicates                PASS/FAIL
AMEND-009B      SymbolicForebrain execute                   PASS/FAIL
TASK-5          Maze navigation closed-loop demo            PASS/FAIL

Overall: ALL PASS ✓ / SOME FAILURES ✗
```

---

## RFC-001 + RFC-002 conformance checklist

| Rule                                                       | Component               | Evidence                                                |
|------------------------------------------------------------|-------------------------|---------------------------------------------------------|
| RFC-001 §3 — phase by energy + Hessian only                | kernel (unchanged)      | inherited from `MetastableEngine.classify`              |
| RFC-001 §3.2 — every reset emits LandauerEvent             | kernel (unchanged)      | inherited from `MetastableEngine._trigger_reset`        |
| RFC-001 §7 — measurement holds no Substrate/Bus            | metareasoner            | bus stored only as `_attached_bus` for diagnostics      |
| RFC-001 §7 — measurement does not write to landscape       | metareasoner            | event handlers append/update internal dicts only        |
| RFC-001 §7 — observation socket holds neither              | z3_socket               | Z3 vars are sole external state                         |
| RFC-002 §3.2 — pack does not modify kernel files           | all three packs         | grep confirmation                                       |
| RFC-002 §3.2 — pack does not shadow kernel types           | all three packs         | event types defined in pack namespace where needed      |
| RFC-002 §3.2 — pack declares dependencies                  | symbolic_forebrain      | `declared_dependencies = ["metareasoner", "z3_socket"]` |
| RFC-002 §4.3 — Governor declares mutations                 | symbolic_forebrain      | `declared_mutations = [...]` in config                  |
| RFC-002 §3.3 — experiment declares kernel ver + manifest   | maze experiment         | `experiments/maze/manifest.py`                          |

---

## What's deferred

These items are NOT part of Session 5. They form the **S6 housekeeping pass** (provisionally `RFC-002-MIGRATION-A` if it warrants its own document):

1. **Carve out S2 contents into packs.** `JAXSubstrate` -> `mpc_packs/jax_substrate/`, `AutoCluster` -> `mpc_packs/auto_cluster/`, `LLMConstraintEncoder` -> `mpc_packs/llm_encoder/`. Update default pack manifest.
2. **Carve out S3 contents into packs.** `DecayingSubstrate`, `LateralCluster`, `ObservationSocket`, `AnthropicSocket`. Replace the transitional shims used by the maze experiment.
3. **Carve out S4 contents into packs.** `Effector` -> `mpc_packs/effector/`, `PersistenceSubstrate`/`PersistenceCluster` -> `mpc_packs/persistence/`. Delete the obsolete `InstrumentedEngine` (its purpose was the PhaseTransitionEvent shadow, now resolved).
4. **Remove the backward-compat shim in `mpc_engine_rfc001.py`.** All callers should import from `mpc_kernel.rfc001` after the carve-out.
5. **Auto-scale `E_STAR` to constraint magnitude** for AnthropicSocket (carryover from v1).
6. **Sliding-window EffectorEvent retention** in the Effector pack to avoid unbounded memory.
7. **Forebrain action provenance** — add `origin` field to LandauerEvent, threaded through Action.

---

## Forward look (Session 7+)

If Session 5's maze loop closes and Session 6's housekeeping completes:

- **Session 7** — Tolman experimental battery: latent learning (train without goal, test with goal), detour problems (close passage mid-run), shortcut problems (open passage mid-run), reversal learning (move goal). Each is a separate experiment under `experiments/`. If any of these requires a capability that lives in the maze experiment, that capability graduates to a pack at this point (see §3.2 §5.1).
- **Session 8** — Parallel mazes with cross-cluster routing tested on transfer. First experiment that requires multiple clusters with separate substrates.
- **Sessions 9+** — Persistence-doc packs land per Appendix A of RFC-002, exercised by experiments that need them.

The cleanest stopping condition has not changed from v2: if Session 7's behavioural curves qualitatively match Tolman's published rat data, the substrate is doing real cognitive work and we have something publishable. If they don't, we have specific mechanisms to fix — and under RFC-002, fixing them no longer means rewriting a 1000-line session file.

---

*End of SESSION-5-TASK-PROMPT-v3.*
