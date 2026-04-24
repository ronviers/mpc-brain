# MPC Brain — Session 7 Report

**Date:** 2026-04-24
**Author:** Claude Opus 4.7 (1M context)
**Governing standards:** RFC-001-MPC-BRAIN, RFC-002-MPC-PROJECT-STRUCTURE (Rev. 1), RFC-004-MPC-DYNAMICAL
**Depends on:** `SESSION-6-REPORT.md` (physics_primitives pack + kernel events + fdr_slope field on PhaseTransitionEvent)

---

## Executive summary

Session 7 closed the FDR-release loop: the `PhaseTransitionEvent.fdr_slope`
field that Session 6 added is now automatically populated by a
gate-triggered measurement inside a drop-in `MetastableEngine` subclass.
The streaming τ_E gate fires once per basin entry (edge-triggered with
hysteresis), runs `measure_fdr` synchronously, caches the scaled
late-time slope, and every subsequent transition event carries it.

Ten commits, all green. One design detour (the Maya mobility gate)
shelved into a renamed pack rather than discarded — 3 orders of
magnitude of real signal, wrong semantic axis for FDR release, still
useful as a mobility observable. One Kimi proposal (deterministic
"goal engine" modal-FDR probe) reviewed and filed as a design note in
`docs/Goal-engine FDR notes.md` — elegant physics, wrong problem for
our current substrate.

---

## Final summary table

| Deliverable | Status | Completion signature |
|---|---|---|
| 1. Scaffold `dynamical_gate` pack (design plan for S7 pickup) | PASS | `[ebc3237]`; `python -c "import mpc_packs.dynamical_gate"` exits 0 |
| 2. Pure primitives `compute_ghost` / `compute_tail` / `gate_signal` | PASS | `[876f8c5]`; primitive unit tests green |
| 3. `DynamicalGate` orchestrator (mobility-detector version) | PASS | `[e4850c4]`; smooth-descent quiet, direction-flip trips |
| 4. Four-scenario calibration of the mobility gate | PASS | `[09284ba]`; 110:0 trip-count spread reset:conflict |
| 5. Shelf mobility gate — rename to `mobility_detector`, add `tension` | PASS | `[179495f]`; renamed pack still green, tension property added |
| 6. New `dynamical_gate` pack using streaming τ_E | PASS | `[1224eb9]`; pinned vs mobile 25× trip-rate separation |
| 7. Wire gate → `measure_fdr` → classifier → `PhaseTransitionEvent.fdr_slope` | PASS | `[7e4f9c1]`; committed slope +0.959 matches Session-A +0.96 to 3 dp |
| 8. Edge-triggered release with hysteresis | PASS | `[be546b0]`; 26 releases → 1 release per pinned trajectory |
| 9. `StreamingObservables` companion for τ_A / γ_A / γ_ij | PASS | `[d8f4196]`; end-to-end test uses it instead of hand-rolled calls |
| 10. `DynamicalEngine` — drop-in subclass populating event `fdr_slope` | PASS | `[48644e0]`; 68 events, 50 carry slope, release_count=1 |

Overall: **ALL PASS ✓**.

---

## What changed, by commit

| Commit | Shape |
|---|---|
| [`ebc3237`](../../mpc_packs/dynamical_gate/README.md) | Scaffold only. Directory + README + stubs that a fresh session could pick up and fill without re-deriving design. |
| [`876f8c5`](../../mpc_packs/mobility_detector/pack.py) | First three primitives. Sanity tests: harmonic-well τ, straight-line tail, direction disagreement trips. |
| [`e4850c4`](../../mpc_packs/mobility_detector/pack.py) | Orchestrator: ring buffer, per-step observe, warmup-is-quiet + direction-flip-trips. |
| [`09284ba`](../../mpc_packs/mobility_detector/pack.py) | Four-scenario calibration. Magnitude-gated cosine distance produces (0, 8, 81, 110) trip counts — useful signal, wrong semantic axis for FDR release. |
| [`179495f`](../../mpc_packs/mobility_detector/) | Shelf. Rename pack + class to `mobility_detector` / `MobilityDetector`. Add continuous `tension` property. README pivots from "FDR gate" to "mobility observable"; lists four use cases. |
| [`1224eb9`](../../mpc_packs/dynamical_gate/) | Fresh `dynamical_gate` pack. Streaming energy-autocorrelation τ_E estimator; trips when τ drops below floor (pinned regime). 25× separation pinned vs mobile. |
| [`7e4f9c1`](../../mpc_packs/dynamical_gate/release.py) | `release.py` — `release_fdr_slope` and `release_and_classify`. Slope formula matches `mpc_lattice.py`. End-to-end test on committed produces +0.959. Also files `docs/Goal-engine FDR notes.md`. |
| [`be546b0`](../../mpc_packs/dynamical_gate/pack.py) | Edge-triggered release with hysteresis (`tau_floor_exit = 2·tau_floor`). 26 → 1 release per pinned trajectory. New `is_pinned` observable. |
| [`d8f4196`](../../mpc_packs/dynamical_gate/observables.py) | `StreamingObservables` companion. Rolling buffer + one-shot bath reference for `tau_env`. Removes hand-rolled `correlation_time` / `survival_margin` from call sites. |
| [`48644e0`](../../mpc_packs/dynamical_gate/engine.py) | `DynamicalEngine(MetastableEngine)`. Session-4-style subclass that observes + releases + emits enriched events. RFC-001 §3 invariants preserved; only emission is enriched. |

---

## Interpretation

**What we actually built and why it took two passes.**

The pack started from a pattern (Maya predictive-VFX goal rig) and tried
to force it onto the FDR-release problem. The first implementation —
linear drift extrapolation + rolling trajectory tail + cosine-distance
gate — produced a beautifully discriminating signal but on the wrong
axis. It separated *mobile* from *pinned* regimes (3 orders of magnitude
of spread, 0 to 110 trips), where FDR release actually needs the
inverse: it wants to fire *inside* the pinned regime where trajectory-
only observables cannot separate C from K.

The correct signal was already in `mpc_lattice.classify_regime`: the
integral correlation time of a trajectory observable. When τ collapses
to the noise floor, we are pinned and FDR must be measured; when τ is
well above, the topological classifier suffices. Session 7's second
pass used `autocorr_fft` + `tau_integral` (which we had already moved
into the `physics_primitives` pack in Session 6) to maintain a rolling
online estimate. The semantics inverted correctly: committed and
conflict trip at 100% of recomputes, suspended and reset at 0% (or
~4% for one boundary-dip transient).

**The first pass was not wasted.** The mobility gate's signal is real,
fast, and useful for other questions — resource allocation, early-stop
heuristics, exploration/exploitation signalling. Renaming it to
`mobility_detector` and adding a continuous `tension` observable kept
it alive as a first-class pack rather than deleting it. This is the
second time this session we preserved a "failed" thing (the other:
Goal-engine FDR notes) because "failed for this use" is not the same
as "failed."

**Edge-triggering was the difference between "cute demo" and
"production-ready."** A level-triggered gate fires every recompute while
pinned. In the four-scenario test that was 26 fires per committed
trajectory — each costing 7-8 s of `measure_fdr` wall time. A 3000-step
committed run would spend ~200 s re-measuring the same pinned basin
state over and over. Edge-triggering with hysteresis cuts this to 1
release at basin entry, 26× reduction. Nothing about the scientific
content changed; the engineering discipline (fire on transition, not
while in state) made the difference between usable and unusable.

**The two Kimi collaborations.** The user brought proposals from a
second assistant twice, both translating Maya VFX patterns into MPC
physics. Kimi's first (the "spring probe") proposed a basin-integrity
test for distinguishing C from K in the pinned regime. It solved a gap
that doesn't exist on our scenarios — the topological `E > E_s` rule
already catches the high-energy conflict compromise. Kimi's second (the
deterministic "goal engine" + modal FDR ratio) was physically correct
but mis-described; in our scenarios both committed and conflict have
`Var(δ_i) ≈ kT/λ_i` (equipartition holds in both because both sit
near locally-quadratic minima). The modal-FDR ratio *is* useful — for
detecting non-equilibrium driving on active-substrate work we haven't
done yet. Filed as `docs/Goal-engine FDR notes.md` with clear
"when to revisit" criteria.

**The design chain, compressed.** The final working stack has four
layers, each doing one thing:

1. `physics_primitives.run_langevin` / `measure_fdr` / `classify_phase_dynamical`
   — the validated RFC-004 numerical core, unchanged since Session 6.
2. `DynamicalGate` — streams τ_E, edge-fires on transitions into the
   pinned regime, suppresses sub-thermal noise with hysteresis.
3. `StreamingObservables` — rolls up τ_A, γ_A, γ_ij on the engine's
   trajectory so the classifier gets its inputs without the caller
   hand-rolling NumPy.
4. `DynamicalEngine(MetastableEngine)` — ties them together, emits
   `PhaseTransitionEvent` with `fdr_slope` populated on transitions
   that occurred after a release.

Each layer is independently testable and separately shelveable. The
pack is cleanly composable: a caller who wants just the τ_E estimator
can use `DynamicalGate` alone; one who wants just the slope calculation
can use `release_fdr_slope`; the experiments that want the full wiring
can use `DynamicalEngine` as a drop-in.

---

## RFC-001 + RFC-002 conformance checklist

| Rule | Component | Evidence |
|---|---|---|
| RFC-001 §3 — phase by energy + Hessian only | kernel (unchanged) | `Substrate.classify` not overridden by `DynamicalEngine` |
| RFC-001 §3.2 — every reset emits LandauerEvent | kernel (unchanged) | `_trigger_reset` inherited |
| RFC-001 §3.3 — hard budget wall | kernel (unchanged) | `E_star` check inherited byte-for-byte |
| RFC-001 §3.4 — maintenance force active only in s-state | kernel (unchanged) | `_maint.force` gated on `prev_phase == Phase.S` |
| RFC-001 §6 — `PhaseTransitionEvent` canonical form | kernel events | `fdr_slope: Optional[float] = None` added Session 6; optional, backward-compatible |
| RFC-002 §3.2 — pack does not modify kernel files | `mpc_packs/dynamical_gate/` | grep-clean: zero writes to `mpc_kernel/` |
| RFC-002 §3.2 — pack does not shadow kernel types | `mpc_packs/dynamical_gate/` | `PhaseTransitionEvent` imported from `mpc_kernel.rfc001.events`, not redeclared |
| RFC-002 §3.2 — pack declares dependencies | README | `numpy`, `mpc_packs.physics_primitives`, `mpc_kernel.rfc001.phase.Phase`, `mpc_kernel.rfc001.events.PhaseTransitionEvent` |
| RFC-002 §4 — uses a documented plug point | `DynamicalEngine` | SubstrateExtension-adjacent — subclasses `MetastableEngine` in the InstrumentedEngine pattern; no new plug point required |

---

## What's open (carried forward to Session 8)

From Session 7 directly:

1. **Observable choice.** `DynamicalGate` buffers total substrate energy
   for its τ_E estimator; the caller chooses `V_obs` for the FDR
   measurement. Multi-proposition experiments may want per-proposition
   violations or PCA-projected coordinates.
2. **Asynchronous release.** `DynamicalEngine.step` currently stalls
   for ~8 s on each edge fire. Edge-triggering keeps this to ~1 stall
   per basin entry — fine for short experiments, bad for long ones. The
   natural refactor is a worker thread: engine caches the previous slope
   while a new measurement runs in the background, the cached value
   flips when the worker returns.
3. **`DynamicalEngine` in a real experiment.** So far it is tested only
   on single-engine synthetic scenarios. The maze experiment
   (`experiments/maze/`) is the obvious target for a first production
   run, but it currently wires the S4 `InstrumentedEngine` from
   `experiments/historical/mpc_session4.py`. Threading
   `DynamicalEngine` in requires either a dependency-injection point
   in the maze `run.py` or a composed wrapper that chooses which
   engine class to instantiate.

Carried over from Session 6 (still open):

4. **S2/S3/S4 pack carve-out.** `jax_substrate`, `auto_cluster`,
   `effector`, `calorimeter` still live inside the historical
   monoliths in `experiments/historical/`. `decaying_substrate` and
   `persistence_substrate` remain transitional shims.

Carried over from Session 5 (still open, lower priority):

5. Auto-scale `E_STAR` to constraint magnitude (v3 item 5).
6. Sliding-window `EffectorEvent` retention (v3 item 6).
7. Forebrain action provenance — `origin` field on `LandauerEvent`
   threaded through `Action` (v3 item 7).
8. M6 rule for maze traversal (remove-behind-cell).
9. Engine-level provenance on `PhaseTransitionEvent` / `EffectorEvent`
   (required for Session 8's parallel-maze work).

---

## Reproducibility

```bash
# From repo root, Python 3.12 with numpy/scipy/matplotlib.
python -m mpc_packs.dynamical_gate.test_pack             # 5 tests, ~20 s

# Skip the full-budget measure_fdr stalls for fast CI:
DYNAMICAL_GATE_SKIP_SCENARIOS=1 \
    python -m mpc_packs.dynamical_gate.test_pack         # primitives only, <1 s

# The shelved mobility detector still green:
python -m mpc_packs.mobility_detector.test_pack          # 5 tests, ~10 s
```

All three exit 0.

---

*End of Session 7 report.*
