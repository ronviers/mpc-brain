# MPC Brain — Session 9 Report

**Date:** 2026-04-24
**Author:** Claude Opus 4.7 (1M context)
**Governing standards:** RFC-001-MPC-BRAIN, RFC-002-MPC-PROJECT-STRUCTURE (Rev. 1), RFC-004-MPC-DYNAMICAL
**Depends on:** `SESSION-8-REPORT.md` (DynamicalEngine in maze; types unified; jax_substrate / auto_cluster / effector / decaying_substrate carved)

---

## Executive summary

Session 9 closed the entire S2/S3/S4 monolith carve-out with five
commits. `mpc_packs/` now hosts twelve first-class packs and zero
transitional shims. Every brain capability that lived in the historical
session monoliths has a proper home, with declared dependencies, real
tests, and a README. `InstrumentedEngine` was retired to an alias of
the kernel `MetastableEngine` (the kernel already populates the
`energy` field that motivated InstrumentedEngine in Session 4).

The maze experiment continues to PASS all six TASK-5 acceptance
criteria after every individual carve. All 11 pack test suites are
green.

---

## Final summary table

| Deliverable | Status | Completion signature |
|---|---|---|
| 1. `observation_socket` pack — ConstraintSpec, ObservationSocket, AnthropicSocket | PASS | [`3a761f9`]; class identity unified across pack/session3; 5 sanity tests |
| 2. `lateral_cluster` pack — AMEND-003 lateral maintenance field | PASS | [`d66e37a`]; class identity unified pack/session3; 3 sanity tests |
| 3. `persistence_substrate` from shim → first-class (PersistenceSubstrate + PersistenceCluster) | PASS | [`2e114b4`]; class identity unified pack/session4; InstrumentedEngine relocated into the pack to break a circular import; 4 sanity tests |
| 4. `llm_encoder` pack — natural-language → constraint-function encoder | PASS | [`51b9570`]; class identity unified pack/session2; 4 sanity tests; demo P1 fn(0)=7.5 as designed |
| 5. Retire `InstrumentedEngine` | PASS | [`c153494`]; aliased to `MetastableEngine`; bus-level emission semantics confirmed via maze run |

Overall: **ALL PASS ✓**.

---

## What changed, by commit

| Commit | Shape |
|---|---|
| [`3a761f9`](../../mpc_packs/observation_socket/) | New pack with the AMEND-004 ObservationSocket family. SYSTEM_TEMPLATE inlined to avoid coupling to `LLMConstraintEncoder`; word-hash quadratic fallback included as a private helper. Five sanity tests (abstract base raises, fallback path, flush/drain, register_fallback, template parametricity). |
| [`d66e37a`](../../mpc_packs/lateral_cluster/) | New pack for `LateralCluster`. AutoCluster subclass; replaces JAXSubstrate with `DecayingSubstrate` at construction; lateral force `F = Σ w_ij(v_j − v_i)` over s-state engines in the same nearest-well, scaled by `lateral_scale / n_same` for O(1) magnitude. Three sanity tests. |
| [`2e114b4`](../../mpc_packs/persistence_substrate/) | The last transitional shim retired. Real implementations of `PersistenceSubstrate` (usage-modulated τ + apply_outcome reinforcement) and `PersistenceCluster` (LateralCluster backed by PersistenceSubstrate; traversal recording + active reinforcement on phase-C). `InstrumentedEngine` moved into this pack to break a circular import (session4 re-exports from here both ways). Four sanity tests. |
| [`51b9570`](../../mpc_packs/llm_encoder/) | New pack for the natural-language → constraint-function encoder. Anthropic API primary path, deterministic word-hash quadratic fallback, analytic overrides for the Session-2 hello-world demo (P1=ball, P2=prism, P3=pen). Four sanity tests including the P1 `fn(0)=7.5` cross-check. |
| [`c153494`](../../mpc_packs/persistence_substrate/pack.py) | `InstrumentedEngine = MetastableEngine` — alias retirement. The kernel already emits `PhaseTransitionEvent.energy` (Session 6); the post-update vs pre-update difference is documented and judged immaterial in practice (the maze runs `DynamicalEngine`, never an actual `InstrumentedEngine` instance). |

---

## Interpretation

**The carve-out is complete.** Every meaningful class from the
Session-2/3/4 monoliths now lives in a pack with declared dependencies,
its own test suite, and a README. The historical .py files remain in
`experiments/historical/` per RFC-002 §13.2(b), shrunken to ~1700 lines
total (was ~3300) and consisting almost entirely of re-export
statements, demo functions, and acceptance-test scaffolding.

**The shim era ended cleanly.** `decaying_substrate` (Session 8) and
`persistence_substrate` (this session) were the last two transitional
shims. Both went from "re-export from monolith" to "real implementation
in the pack, monolith re-exports from here" without breaking any
caller, because the type-identity move from Session 8
(`sys.modules[__name__] = _real`) and the canonical kernel events made
class identity transitive across import paths.

**One circular import bit us, and the fix was clean.** When
`persistence_substrate.pack` tried to `from mpc_session4 import
InstrumentedEngine`, the import cycle blew up because session4's
re-export of `PersistenceCluster` from this pack was not yet finished
when InstrumentedEngine was needed. Fix: move `InstrumentedEngine`
into the persistence_substrate pack itself, then have session4
re-export from the pack. Two-line change, no further dependencies.

**InstrumentedEngine retirement was simpler than expected.** The
class existed to populate the `energy` field on `PhaseTransitionEvent`
(AMEND-005, Session 4). When the kernel events were canonicalised in
Session 6, that field moved into the kernel `PhaseTransitionEvent`
with a default value, and the kernel `MetastableEngine.step()` already
populates it. So `InstrumentedEngine` had no remaining behaviour
distinct from `MetastableEngine` other than the post-update vs
pre-update energy choice — too small to matter for active code, since
the maze swaps the engine to `DynamicalEngine` before any
InstrumentedEngine step ever runs.

**Aliasing-as-retirement is the right move for backward compat.**
`InstrumentedEngine = MetastableEngine` preserves all existing
imports, all `isinstance(...)` checks, and all class references. New
code can use `MetastableEngine` directly. No breaking change for any
external caller.

---

## RFC-001 + RFC-002 conformance checklist

| Rule | Component | Evidence |
|---|---|---|
| RFC-001 §3 — phase by energy + Hessian only | every carved pack | None of the new packs override `Substrate.classify` |
| RFC-001 §6 — `PhaseTransitionEvent` canonical form | unified pre-Session 8 | All emissions use kernel-class events; verified via maze |
| RFC-001 §7 — measurement-layer holds no Substrate / Bus | observation_socket, llm_encoder | Both packs are pure producers; hold neither |
| RFC-002 §3.2 — pack does not modify kernel files | every carved pack | grep-clean; zero writes to `mpc_kernel/` |
| RFC-002 §3.2 — pack does not shadow kernel types | every carved pack | All kernel imports; no redeclaration |
| RFC-002 §3.2 — pack declares dependencies | every carved pack | `config.py:DECLARED_DEPENDENCIES` present |
| RFC-002 §4 — uses a documented plug point | every carved pack | SubstrateExtension (jax/decaying/persistence_substrate), Cluster subclass (auto/lateral/persistence_cluster), EventSubscriber/measurement (effector, observation_socket), Producer (llm_encoder) |

---

## What's open (carried forward to Session 10)

### Maze determinism

`experiments/maze/run.py` does not seed `np.random` so per-run metrics
(gate `release_count`, `cached_fdr_slope`, `tau_estimate`, exact
`action_log`) vary. Add an explicit `np.random.seed(SEED)` at the top
of `main()` for reproducibility in multi-run comparisons.

### Tolman experimental battery

Latent learning, detour problems, shortcut problems, reversal
learning. First full test of the cognitive-map claims. Originally
planned for Session 7; deferred each session in favour of
infrastructure work. Now the infrastructure is ready (full pack
suite, type-unified events, async release, DynamicalEngine swap
working in the maze) — Session 10 is the natural place to start.

### Audit `mpc_engine_rfc001.py`

The historical monolith still contains real implementations of
`MetastableEngine`, `MPCCluster`, `Network`, `Substrate`, plus a
handful of value objects (`EnergyState`, `TopologyResult`,
`ConstraintHandle`). The kernel `mpc_kernel.rfc001.*` modules have
their own copies of all of these (carved Session 6). It would be
worth either (a) dropping the historical copies and having the
monolith re-export the kernel versions, or (b) deleting the monolith
entirely and letting the historical sessions import from the kernel
directly. Currently it's a parallel implementation that nobody type-
checks.

### Visualizer integration

If the H:\mpc-visualizer sidequest produces a useful tool, the maze
run.py should grow an SSE-compatible step callback so the visualizer
can attach without re-running the maze internally.

---

## Reproducibility

```bash
# Eleven-pack test sweep (~25 s):
for p in physics_primitives dynamical_gate mobility_detector \
         effector jax_substrate auto_cluster decaying_substrate \
         observation_socket lateral_cluster persistence_substrate \
         llm_encoder; do
    python -m mpc_packs.$p.test_pack
done

# Maze end-to-end (~15 s; all six TASK-5 PASS):
PYTHONIOENCODING=utf-8 python -m experiments.maze.run
```

Pre-requisites unchanged from Session 8: Python 3.12+, numpy, scipy,
matplotlib, z3-solver, `mpc_engine_rfc001.py` at repo root, top-level
session shims at `mpc_session{2,3,4}.py`.

---

*End of Session 9 report.*
