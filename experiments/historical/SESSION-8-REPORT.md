# MPC Brain — Session 8 Report

**Date:** 2026-04-24
**Author:** Claude Opus 4.7 (1M context)
**Governing standards:** RFC-001-MPC-BRAIN, RFC-002-MPC-PROJECT-STRUCTURE (Rev. 1), RFC-004-MPC-DYNAMICAL
**Depends on:** `SESSION-7-REPORT.md` (dynamical_gate + DynamicalEngine stack landed; carry-forward was S2/S3/S4 pack carve-out, async release, maze integration)

---

## Executive summary

Session 8 closed the remaining Session-7 carry-forwards and carved four
packs out of the historical S2/S3/S4 monoliths. The dynamical-gate
stack now has asynchronous release (23× stepping speedup, slope
byte-identical). The maze experiment runs `DynamicalEngine` as a
drop-in for `InstrumentedEngine`, still PASSing all six TASK-5
criteria. Type-system duality is fully resolved — `PhaseTransitionEvent`,
`Phase`, `LandauerEvent`, `BudgetResetEvent`, `EventBus`,
and `Calorimeter` all yield the same class object across every import
path. Three of the four originally-listed carve-out targets
(`jax_substrate`, `auto_cluster`, `effector`, `calorimeter`) landed as
first-class packs; `decaying_substrate` was promoted from transitional
shim as a bonus.

Nine commits, all green. Eight packs with live test suites. The
infrastructure is ready; the remaining S3/S4 historical content
(`LateralCluster`, `ObservationSocket`/`AnthropicSocket`,
`LLMConstraintEncoder`, `PersistenceCluster`/`PersistenceSubstrate`,
`InstrumentedEngine`) is carry-forward to Session 9.

---

## Final summary table

| Deliverable | Status | Completion signature |
|---|---|---|
| 1. Async release worker on `DynamicalEngine` | PASS | [`76244a6`]; sync 7.91s → async stepping 0.35s, slope +0.9594 both paths |
| 2. Top-level shims for historical session monoliths | PASS | [`353a5f6`]; `mpc_session{2,3,4}.py` at repo root alias `experiments.historical.*` via `sys.modules[__name__] = _real` |
| 3. Import `mpc_engine_rfc001.py` (user-supplied) | PASS | [`6979172`]; placed at repo root |
| 4. Unify `PhaseTransitionEvent` / `Phase` / `Event*` / `EventBus` types | PASS | [`8af07b6`]; single class identity across kernel, monolith, S4 shadow |
| 5. Swap `InstrumentedEngine` → `DynamicalEngine` in maze | PASS | [`570b383`]; all six TASK-5 PASS with `async_release=True` |
| 6. Unify `Calorimeter` | PASS | [`6ec0da3`]; monolith re-exports from `mpc_kernel.rfc001.network` |
| 7. Carve `Effector` + `EffectorEvent` into first-class pack | PASS | [`b20072e`]; `mpc_packs/effector/`, 4 sanity tests green |
| 8. Carve `JAXSubstrate` + `AutoCluster` into first-class packs | PASS | [`f65b9f8`]; `mpc_packs/jax_substrate/` (3 tests), `mpc_packs/auto_cluster/` (2 tests), both green |
| 9. Promote `decaying_substrate` from shim to first-class pack | PASS | [`25cd773`]; 4 sanity tests green |

Overall: **ALL PASS ✓**.

---

## What changed, by commit

| Commit | Shape |
|---|---|
| [`76244a6`](../../mpc_packs/dynamical_gate/engine.py) | `DynamicalEngine(async_release=True)` submits `measure_fdr` to a single-worker `ThreadPoolExecutor`. Stepping no longer blocks on the ~8 s release. Overlapping releases suppressed. `wait_for_release()` / `close()` / `release_in_flight` added. Test asserts `|stepping_wall| < 3 s` and slope byte-equality sync↔async. |
| [`353a5f6`](../../mpc_session2.py) | `mpc_session2.py`, `mpc_session3.py`, `mpc_session4.py` at repo root. Each is a three-line shim that re-aliases `sys.modules[__name__] = experiments.historical.mpc_sessionN` so bare-name imports (`from mpc_session3 import X`) resolve to the same module object as the nested path. |
| [`6979172`](../../mpc_engine_rfc001.py) | Ron-supplied reference monolith at repo root. 1093 lines, the pre-RFC-002 kernel that Sessions 2–4 built against. Flagged the type-duality finding in its commit message. |
| [`8af07b6`](../../mpc_engine_rfc001.py) | Replace monolith's local `Phase`/`PhaseTransitionEvent`/`LandauerEvent`/`BudgetResetEvent`/`EventBus` with `from mpc_kernel.rfc001 import ...`. Retire `mpc_session4`'s S4 shadow `PhaseTransitionEvent`. One-time, non-invasive. Verified: kernel-subscribed handler receives 14 events from a monolith emitter on a K→S→C trajectory; was 0 before. |
| [`570b383`](../../experiments/maze/run.py) | Maze `run.py` gains `_upgrade_cluster_engines_to_dynamical(cluster, maze)` and a `USE_DYNAMICAL_ENGINE = True` toggle. Each engine created by `PersistenceCluster` is replaced with a `DynamicalEngine` carrying its own gate + observables. Bath trajectory for τ_env is a weak harmonic centred at maze centre. `wait_for_release()` drain at end of run. All six TASK-5 PASS. |
| [`6ec0da3`](../../mpc_engine_rfc001.py) | Monolith's 62-line local `Calorimeter` class replaced with `from mpc_kernel.rfc001.network import Calorimeter`. Two redundant definitions → one class identity. |
| [`b20072e`](../../mpc_packs/effector/) | New `mpc_packs/effector/` with `pack.py` + `config.py` + `README.md` + `test_pack.py`. `mpc_session4.py` now re-exports from it. Class identity unified across three import paths. Four sanity tests cover non-C no-op, C commit emission, Landauer accumulator reset, cluster-ID filter. |
| [`f65b9f8`](../../mpc_packs/jax_substrate/) | Two packs in one commit because `AutoCluster` depends on `JAXSubstrate`. `jax_substrate/` exposes `JAXSubstrate` and `JAX_AVAILABLE`; `auto_cluster/` uses the flag to decide whether to swap in `JAXSubstrate` at construction time. `mpc_session2.py` re-exports both. FD fallback verified on this Windows host (no JAX installed); `AutoCluster` seeds 1 → 16 engines under two overlapping wells. |
| [`25cd773`](../../mpc_packs/decaying_substrate/) | `mpc_packs/decaying_substrate/pack.py` replaced — was a one-line shim (`from mpc_session3 import DecayingSubstrate`), now contains the real 170-line AMEND-001 implementation. `mpc_session3.py` re-exports from the new pack. All four decay tests (construct + seed, decay shrinks, ping restamps, floor drop) green. |

---

## Interpretation

**The type-duality fix was the load-bearing move of the session.**
Before [`8af07b6`], the codebase had three distinct `PhaseTransitionEvent`
classes (kernel 7-field, monolith 5-field, S4 shadow 6-field).
Subscribers bound via one class never received events from emitters
using another — the bug SESSION-4-REPORT explicitly called out as "the
thing to fix." After that commit, every import path yields the same
class object; `DynamicalEngine` (kernel-class emitter) and
`InstrumentedEngine` (monolith-class emitter) publish identical events
and `Calorimeter` / `Effector` subscribers see everything. This was the
prerequisite for the maze integration to be meaningful at all.

**The carve-outs are cheaper than they look.** Once the type system is
unified, a carve-out is a mechanical three-step: copy the class body
into a new pack file, replace the historical definition with an import
from the pack, verify class identity across paths. Each of
`Effector`, `JAXSubstrate`, `AutoCluster`, `DecayingSubstrate` followed
this pattern; total new-code volume was dominated by docstrings and
tests, not physics. The monoliths themselves lost ~400 LOC.

**The maze run's gate behavior is now seed-dependent.** Before Session 7,
the maze's `InstrumentedEngine` was deterministic-enough across runs to
produce stable TASK-5 numbers. With the `DynamicalEngine` swap, the
gate's τ_E estimate drifts with each run's noise realization — we've
seen all of `release_count ∈ {0, 1}`, `cached_fdr_slope ∈ {None, −0.15}`,
`tau_estimate ∈ {0.09, 0.12, 0.22}`, `is_pinned ∈ {True, False}` across
consecutive runs with the same config. The six acceptance criteria all
remain PASS, but the finer per-run metrics are now Monte-Carlo
quantities. A future refinement could explicitly seed `np.random` in
the maze's `run.py` for reproducibility.

**One carve-out was unexpectedly trivial.** `Calorimeter` was already
in the kernel from Session 6, but the monolith kept its own copy;
nobody noticed because the unified-types fix made them identity-equivalent
at the site it mattered. Once the event types were unified, replacing
the monolith's local `Calorimeter` with an import was a six-line edit.

**Async release is the first cross-process-boundary move in the pack.**
The `ThreadPoolExecutor` is a thin boundary — Python's GIL still
serializes at the bytecode level — but numpy releases the GIL for most
computations, so `measure_fdr`'s inner loops actually run in parallel
with the main stepping loop. 23× stepping speedup is the proof. If a
future substrate demands *hard* parallelism (GPU-resident `measure_fdr`,
multi-engine simultaneous release), the single-worker queue is the
extension point.

---

## RFC-001 + RFC-002 conformance checklist

| Rule | Component | Evidence |
|---|---|---|
| RFC-001 §3 — phase by energy + Hessian only | all kernel + pack paths | `Substrate.classify` not overridden by any carved pack; `DynamicalEngine` and `InstrumentedEngine` both inherit classification from `MetastableEngine` |
| RFC-001 §6 — `PhaseTransitionEvent` canonical form | monolith + S4 + kernel | Post-[`8af07b6`], all three yield the same class object; verified by id equality |
| RFC-001 §7 — measurement holds no Substrate / Bus | `Effector`, `Calorimeter` | Both accept `bus` only via `attach()`; store no reference to any brain component |
| RFC-002 §3.2 — pack does not modify kernel files | every pack carved this session | grep-clean: zero writes to `mpc_kernel/` |
| RFC-002 §3.2 — pack does not shadow kernel types | all packs | Kernel events are imported, not redeclared |
| RFC-002 §3.2 — pack declares dependencies | all packs | `config.py:DECLARED_DEPENDENCIES` present in each |
| RFC-002 §4 — uses a documented plug point | all packs | `JAXSubstrate`/`DecayingSubstrate` = SubstrateExtension; `Effector`/`Calorimeter` = EventSubscriber; `AutoCluster` = MPCCluster subclass (RFC-001 §4.3, the same "governor-adjacent" pattern used by `DynamicalEngine`) |

---

## What's open (carried forward to Session 9)

### Remaining historical content

| Item | Location | Planned pack | Dependencies |
|---|---|---|---|
| `LateralCluster` | `mpc_session3.py:237` | `mpc_packs/lateral_cluster/` | `AutoCluster`, `DecayingSubstrate`, `ObservationSocket` |
| `ObservationSocket` (abstract) + `ConstraintSpec` + `AnthropicSocket` | `mpc_session3.py:425+` | `mpc_packs/observation_socket/` | `anthropic` SDK (optional for `AnthropicSocket`) |
| `LLMConstraintEncoder` | `mpc_session2.py:536` | `mpc_packs/llm_encoder/` | `anthropic` SDK |
| `PersistenceSubstrate` + `PersistenceCluster` | `mpc_session4.py` | `mpc_packs/persistence_substrate/` (upgrade from shim) | `DecayingSubstrate`, `LateralCluster` |
| `InstrumentedEngine` | `mpc_session4.py:108` | retire — `DynamicalEngine` supersedes it on the kernel side; audit call sites |

### Dynamical-gate open items (unchanged from Session 7)

- **Observable choice.** `V_obs` is caller-supplied; multi-proposition
  experiments may benefit from per-proposition violations or
  PCA-projected coordinates.

### Seeding

- **Maze determinism.** `experiments/maze/run.py` doesn't seed
  `np.random` so run-to-run metrics (including `gate.release_count` and
  `cached_fdr_slope`) vary. Add an explicit `np.random.seed(SEED)` at
  the top of `main()` for reproducibility in multi-run comparisons.

---

## Reproducibility

```bash
# Full pack test sweep (~20 s with FDR stalls, <1 s without):
for p in physics_primitives dynamical_gate mobility_detector \
         effector jax_substrate auto_cluster decaying_substrate; do
    python -m mpc_packs.$p.test_pack
done

# Maze end-to-end (~10-15 s; all six TASK-5 PASS):
PYTHONIOENCODING=utf-8 python -m experiments.maze.run
```

Pre-requisites:
- Python 3.12+ with numpy, scipy, matplotlib, z3-solver.
- `mpc_engine_rfc001.py` at repo root (Ron-supplied, commit `6979172`).
- Top-level session shims at `mpc_session{2,3,4}.py` (repo root).

---

*End of Session 8 report.*
