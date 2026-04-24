# MPC Brain — Session 6 Report

**Date:** 2026-04-24
**Author:** Claude Opus 4.7 (1M context)
**Governing standards:** RFC-001-MPC-BRAIN, RFC-002-MPC-PROJECT-STRUCTURE (Rev. 1)
**Depends on:** `SESSION-5-REPORT.md` (kernel at v0.4.0, maze experiment green)

---

## Executive summary

Session 6 retired a speculative documentation detour, promoted the validated
dynamical primitives into a first-class pack, carved the kernel event types
out of a broken monolith shim, and wired the FDR-slope signal end-to-end
through `PhaseTransitionEvent`. The kernel now imports; the dynamical
classifier is reachable from experiments; the four Session-A rows classify
to their correct `Phase` via the new code path.

Five commits, all green. No scope expansion beyond the physics pickup the
user asked for.

---

## Final summary table

| Deliverable | Status | Completion signature |
|---|---|---|
| 1. Retire `MPC-SESSION-SOP.md`; revert RFC-002 to pre-SOP Rev. 1 | PASS | `test ! -f docs/MPC-SESSION-SOP.md && wc -l docs/RFC-002-MPC-PROJECT-STRUCTURE.md` → 663 |
| 2. Promote `physics_primitives` to a pack | PASS | `python -m mpc_packs.physics_primitives.test_pack` exits 0 |
| 3. Repoint `mpc_lattice.py`; reproduce Session-A table | PASS | `PYTHONPATH=. PYTHONIOENCODING=utf-8 python docs/dynamical-track/mpc_lattice.py` → all 4 scenarios classify ✓ |
| 4. Retire old `docs/dynamical-track/physics_primitives.py` | PASS | `test ! -f docs/dynamical-track/physics_primitives.py` |
| 5. Carve `mpc_kernel/rfc001/events.py` | PASS | `python -c "from mpc_kernel.rfc001 import MetastableEngine, Calorimeter"` exits 0 |
| 6. Add `classify_phase_dynamical` | PASS | Four Session-A rows → `{Phase.C, Phase.S, Phase.K, Phase.R}` |
| 7. Add `fdr_slope: Optional[float]` to `PhaseTransitionEvent` | PASS | Event with slope=+0.96 re-classifies to `Phase.C`; defaults to `None` |

Overall: ALL PASS ✓.

---

## What changed, by commit

| Commit | Shape |
|---|---|
| [`7cf633d`](../../docs/RFC-002-MPC-PROJECT-STRUCTURE.md) | Retire `MPC-SESSION-SOP.md` (−644 LOC); revert `RFC-002` from Rev. 3 back to Rev. 1 (−575 LOC net). No §12/§13/§14 in the project any more. |
| [`38922c6`](../../mpc_packs/physics_primitives/) | New pack `mpc_packs/physics_primitives/` (`pack.py`, `__init__.py`, `README.md`, `test_pack.py`). `mpc_lattice.py` repointed; old `docs/dynamical-track/physics_primitives.py` removed. Full Session-A rig regenerates the four figures. |
| [`c7838ce`](../../mpc_kernel/rfc001/events.py) | `events.py` replaced with real `@dataclass` definitions. Shim-to-`mpc_engine_rfc001` gone. `Calorimeter` re-sourced from `.network` in the package `__init__`. |
| [`9808ba7`](../../mpc_packs/physics_primitives/pack.py) | `classify_phase_dynamical(tau_A, tau_env, gamma_A, gamma_ij, fdr_slope) -> Phase` added to the pack. Thresholds `TAU_CONFLICT_FLOOR`, `GAMMA_A_RESET_BAND`, `GAMMA_IJ_K_FLOOR` exposed as keyword args. |
| [`b07da1d`](../../mpc_kernel/rfc001/events.py) | `PhaseTransitionEvent.fdr_slope: Optional[float] = None`. Backcompat: existing emitters that omit the field still work. |

---

## Interpretation

**Three interleaved things happened; disentangling them matters.**

1. **The SOP detour cost real time and produced no physics.** The
   `MPC-SESSION-SOP.md` / RFC-002 §§12–14 machinery was an attempt to
   bound session scope through procedure — prompt templates, hand-off
   templates, halt checkpoints, a preflight session type. Ron killed it
   and told us to move on. The retraction was surgical: delete one file,
   `git checkout` RFC-002 back to the Rev. 1 content (`cffe95e`), commit.
   The lesson here is not that procedure is always waste — it's that
   procedure written in advance of the work it governs accretes faster
   than the work itself. The actual discipline that worked this session
   came from three words ("small deliberate steps") applied step by step.

2. **The physics_primitives promotion finally gives the dynamical track
   a seat at the pack table.** Task A validated the Langevin observables
   in `docs/dynamical-track/` as research artefacts; they stayed there
   because nothing downstream imported them. Moving them into
   `mpc_packs/physics_primitives/` is a packaging change, not a physics
   change — but it's the change that lets any experiment or pack import
   `run_langevin`, `measure_fdr`, or the classifier without path hacks.
   The full 44.7-second four-scenario rig reproduces the SESSION_A_STATE
   table to three decimals from the new location, which is the strongest
   possible statement that no numerical drift slipped in.

3. **The kernel was silently broken, and wiring FDR-slope forced us to
   fix it.** `mpc_kernel/rfc001/events.py` was a shim importing from
   `mpc_engine_rfc001` — a file that lives on Ron's workstation but not
   in this repo. `python -c "from mpc_kernel.rfc001 import *"` failed at
   `ModuleNotFoundError` and had presumably been failing silently since
   the Session 5 carve-out was deferred. Writing real `@dataclass`
   definitions for `PhaseTransitionEvent`, `LandauerEvent`, and
   `BudgetResetEvent` was the bare-minimum work to make the kernel
   importable. SESSION-5 "What's open" item 1 called for a full
   S2/S3/S4 carve-out; we did only the minimum needed to unblock the
   FDR-slope wiring. The remainder is still carry-forward.

**Why the FDR-slope matters on this substrate.** Session A demonstrated
that Markovian overdamped Langevin with harmonic wells *inverts* the
paper's predicted sign for `γ_A` on committed scenarios (stiff wells have
short thermal relaxation, so `τ_A < τ_env` and `γ_A > 0`, opposite the
memory-kernel prediction in RFC-004 §7). The FDR slope is the observable
that *preserves* the paper's prediction across this substrate change:
FDT-ish slope → `[c]`, flat/negative → `[k]`. Without FDR, the classifier
has no way to separate committed from conflict in the pinned regime.
That's why the new event field is `fdr_slope`, not `gamma_A` —
`gamma_A`'s sign is already in `energy` implicitly via the topological
classifier, but the FDR slope carries information no existing field does.

**What is NOT done.** The engine still classifies via the topological
`Substrate.classify(v)` — scalar energy plus Hessian eigenvalues at a
single point. Nothing yet *measures* FDR online. A streaming-window FDR
estimator or a periodic batch probe is the next logical step, and it is
genuinely harder than anything done today: `measure_fdr` needs paired
matched-noise trajectories (~seconds of compute per classification
under current parameters), so a naive per-step call is not viable. The
interesting design question is whether to (a) run FDR in a background
pack that updates a cluster-level classification at e.g. every
100th step, (b) stream the parametric curve from the engine's own
trajectory and an injected ε-perturbation, or (c) defer until a
non-Markovian substrate (where the topological classifier agrees with
the paper's Table 1 and FDR is only needed as corroboration).

---

## What's open (carried forward to Session 7)

All Session 5 carry-forwards except those related to the SOP (now moot)
remain open. Additional items from today:

1. **Online FDR measurement.** Design choice above. The classifier
   function exists; the input to it does not.
2. **S2/S3/S4 carve-out, unfinished.** Today's `events.py` carve is
   minimal. The historical monoliths under `experiments/historical/` still
   hold `Calorimeter` (no — we have one in `network.py`), `MPCCluster`
   pieces, the S4 `Effector`, and the `PersistenceCluster` / `PersistenceSubstrate`
   behaviours behind the transitional shims. SESSION-5 "What's open" item 1.
3. **`GAMMA_IJ_K_FLOOR` etc. are Markovian-substrate-specific.** The
   thresholds in `classify_phase_dynamical` are keyword-argument overridable
   and should be per-substrate when non-Markovian substrates land.
4. **`dev_profile.json` is stale.** Untracked file; still references the
   deleted `MPC-SESSION-SOP.md`. Next regeneration by Ron's local script
   will clear it; no code action required.

---

## Reproducibility

```bash
# From repo root, Python 3.12 with numpy/scipy/matplotlib.
python -m mpc_packs.physics_primitives.test_pack           # 5 tests, ~1 s
PYTHONPATH=. PYTHONIOENCODING=utf-8 \
    python docs/dynamical-track/mpc_lattice.py             # full Session-A rig, ~45 s

python -c "from mpc_kernel.rfc001 import MetastableEngine, Calorimeter, \
    PhaseTransitionEvent, LandauerEvent, BudgetResetEvent, Phase, EventBus; \
    print('kernel imports OK')"
```

All three should exit 0. The lattice rig writes four PNGs alongside
`docs/dynamical-track/mpc_lattice.py`.

---

*End of Session 6 report.*
