# Session A State — Task A Outputs, Crystallized

*Read after `HANDOFF_B_PROMPT.md` and before opening the lattice code. This is the authoritative summary of what Task A measured, what decisions it forced, and what interface implications those decisions carry into RFC-002.*

---

## What was built

**`mpc_lattice.py`** — 1245 lines. Langevin validation rig on the four canonical scenarios (committed, suspended, conflict, reset). Imports `physics_primitives.py` for the core observable routines. Runs end-to-end in ~75 seconds on a laptop CPU. Entry point: `python3 mpc_lattice.py` (produces the four figures in the current working directory and prints a classification table).

**`physics_primitives.py`** — 305 lines, **unchanged from the prototyping session**. Provides: `run_langevin`, `run_paired` (matched-noise), `autocorr_fft`, `tau_integral`, `correlation_time`, `survival_margin`, `cross_dissipation`, `measure_fdr`. This module is the primitive layer; the lattice is a validation harness over it.

**Four figures** (saved PNGs):

- `mpc_trajectories.png` — 4 × 2 grid: phase portraits (top row) and V_A autocorrelations (bottom row) for each scenario. Clear visual separation of the four regimes: bimodal-locked [c], diffuse [s], tightly-pinned [k], wandering [r]. Includes regime tag showing both expected and classified symbols.
- `mpc_fdr_atlas.png` — **the money plot.** 2×2 grid of parametric FDR curves: χ(τ) vs [C(0)−C(τ)]/D_eff, with FDT reference line at unit slope. Panel shapes:
  - [c] collapsed to a narrow vertical locus — pinned variance, small response envelope
  - [s] **clean aging curve** — follows FDT diagonal, bends away, plateaus; paper-predicted shape
  - [k] flat/slight-negative late-slope — non-monotonic signature
  - [r] super-unity late slope, noisy at long τ — weakly-restored bath
- `mpc_separation.png` — three panels: ring geometry at N=4, Φ_required(N) vs Φ* threshold, γ_min and N_max_theory scaling. Restricted to N=2..4 because at N≥5 the Markovian substrate pins the joint potential too deeply for γ_min to be resolved above the noise floor.
- `mpc_hessian_probe.png` — equilibrium-baseline comparison. Log-scale bar chart of τ_measured vs τ_Hessian per scenario, plus eigenstructure table. **Caveat:** all four scenarios show τ_measured < τ_Hessian ("driven") because V_A isn't aligned with the Hessian's slow eigenmodes. The Hessian prediction assumes observable-eigenmode alignment; this is a subtlety not captured in the current figure. A correct reading: the RATIO direction (measured < Hessian) is consistent across scenarios and doesn't cleanly separate equilibrium from driven. Task B's RFC SHOULD specify that Hessian baseline comparison requires observable-Hessian alignment or an explicit projection.

---

## Physics results in a table

Final run, N_reps=6, n_steps=12000, FDR n_reps=32, n_burnin=2000, n_resp=5000:

| scenario  | τ_A     | τ_env | γ_A      | γ_ij    | FDR slope | classifier | ✓/✗ |
|-----------|---------|-------|----------|---------|-----------|------------|-----|
| committed | 0.008   | 1.387 | +118.5   | −21.1   | +0.96     | [c]        | ✓   |
| suspended | 0.426   | 1.387 | +1.67    | −1.20   | +1.35     | [s]        | ✓   |
| conflict  | 0.003   | 1.387 | +296.1   | −27.5   | −0.09     | [k]        | ✓   |
| reset     | 1.387   | 1.387 | +0.00    | +0.02   | −1.47     | [r]        | ✓   |

All four scenarios classify correctly. The classifier uses τ_A/τ_env ratio, |γ_ij|, and FDR slope in combination — no single observable distinguishes all four.

---

## Parameter choices (and why they differ from the prototype baseline)

`physics_primitives.py` runs at `DT = 0.01`, `D_EFF = 0.3`, `K_BT = 1.0` (unchanged). The lattice scenarios were re-tuned during Task A relative to `PROTOTYPE_FINDINGS.md §4`:

| parameter        | prototype | Task A  | reason                                                                                    |
|------------------|-----------|---------|-------------------------------------------------------------------------------------------|
| `LAM_COMMITTED`  | 100.0     | **20.0**| Euler–Maruyama unstable at DT=0.01, λ=100 (step·grad > noise scale; trajectories blow up in ~7000 steps). λ=20 stable. 25× contrast with LAM_SUSPENDED=0.8 preserves the committed/suspended separation. |
| `LAM_SUSPENDED`  | 0.8       | 0.8     | unchanged                                                                                 |
| `LAM_CONFLICT`   | 30.0      | 30.0    | unchanged                                                                                 |
| `LAM_RESET`      | 0.15      | 0.15    | unchanged                                                                                 |
| `FDR_H_MAG[reset]`| 0.30     | **0.05**| h=0.3 overshoots linear response over n_resp=5000 (system drifts ~6 units in the response phase) |
| `FDR_H_MAG[committed]`| 0.02 | **0.05**| variance of V_A is smaller than prototype expected at λ=20 (not 100); h=0.05 still within linear |
| `GAMMA_IJ_K_FLOOR`| n/a     | **5.0** | at Markovian noise floor, all pinned scenarios produce noisy γ_ij ≈ ±25; suspended shows ~1; 5.0 is a clean divider |

These substrate-specific calibrations are why the RFC must specify thresholds as substrate-dependent, not global constants.

---

## The Markovian sign caveat — load-bearing for §3.1 of RFC-002

This is the most important thing Task A confirmed, and it's already documented in FINDINGS §1 but now has live measurement data behind it:

**Claim.** On Markovian overdamped Langevin substrates with harmonic (or near-harmonic) well potentials:

1. `γ_A` for committed comes out POSITIVE (not the paper's Table 1 predicted "γ_A ≪ 0"). Cause: stiff wells give short thermal relaxation → short τ_A → 1/τ_A > 1/τ_env → positive γ_A.
2. `γ_ij` for conflict comes out NEGATIVE (not "γ_ij > 0"). Cause: deeply-pinned τ_i, τ_j, τ_ij all collapse to the noise floor; the sign of the tiny difference is numerically dominated.
3. In the committed and conflict regimes, **both** τ_A and τ_ij collapse to the noise floor, so trajectory observables alone cannot distinguish c from k. **The FDR slope DOES distinguish them** (committed → FDT-ish, conflict → flat/negative).

**Root cause per paper §7.** MPC's natural substrate is non-Markovian with active drive (`D_active ≫ D_thermal`). The paper's Table 1 signs are derived assuming memory kernels. Markovian approximation collapses the memory structure and inverts the sign patterns — while preserving the MAGNITUDES and the FDR shape-by-regime signature.

**Implications for RFC-002 §3.1.** The phase classifier in the new RFC:

- MUST classify using `|γ_A|` magnitude, not `γ_A` sign.
- MUST include FDR slope as a required input when discriminating c from k on substrates where τ_A can collapse to noise floor.
- MAY permit substrates with demonstrated non-Markovian (memory-kernel or active-drive) dynamics to use the paper's original sign-based classification; this is a substrate-compliance profile choice.
- MUST NOT hard-code numeric thresholds; these are substrate-dependent and require per-implementation calibration.

---

## Interface implications for RFC-002 §4

Things the Task A experience teaches about what the Substrate/Engine/Cluster interfaces need to expose:

### §4.1 Substrate — additions and reframings

Current RFC-001 methods: `energy`, `gradient`, `hessian`, `classify`, `register`, `update_λ`, `deregister`, `frustration`.

Additions implied by Task A:

```
autocorrelation(V_obs, traj) -> C(t)
    # FFT-based, unbiased, cutoff at C(τ*) < 0.05.
    # The cutoff is load-bearing: without it, noise-dominated tails
    # of low-variance signals produce garbage integral times.

survival_margin(V_obs, traj_constrained, traj_bath) -> (γ_A, τ_A, τ_env)
    # Requires BOTH a constrained trajectory AND a bath trajectory
    # (bath = trajectory under a weak bounded potential). The bath
    # is how τ_env is instantiated in practice; the RFC should specify
    # that a substrate MUST expose a `bath_trajectory()` method or
    # equivalent, because τ_env is not measurable from the constrained
    # trajectory alone.

cross_dissipation(V_i, V_j, traj) -> (γ_ij, τ_i, τ_j, τ_ij)
    # Uses the sum observable V_{i∧j}(v) = V_i(v) + V_j(v).
    # RFC should allow alternative joint-observable definitions for
    # substrates where V_i + V_j is not the right coupling (a
    # substrate-specific choice, documented per implementation).
```

Reframings of existing methods:

- `hessian(v)` — stays. Documentation changes: it is now the equilibrium-baseline predictor, not the phase classifier. Specifically, `τ^equilibrium ≈ 1/(2·D_eff·λ_min(H))` is the null hypothesis against which measured τ is compared. The `λ_min < 0 ⇒ phase = k` rule in RFC-001 §3.1 is REMOVED.
- `classify(v)` — stays but is no longer a pure function of `v`. It now requires a trajectory window and observable. Signature change: `classify(trajectory_window) -> Phase`.
- `frustration(v)` — stays but is no longer a pure function of `v`. Signature change: `frustration(trajectory_window) -> dict[(id,id), γ_ij]`. Upgrades AMEND-001 to INTRINSIC automatically: the method takes a window and produces window-time-resolved γ_ij's.

### §4.2 Engine — additions

```
fdr_profile(V_obs, h_mag, n_burnin, n_resp, n_reps) -> (tau_grid, C, chi)
    # Matched-noise paired-trajectory FDR measurement.
    # The matched-noise requirement is non-negotiable — vanilla
    # ensemble difference is too noisy at reasonable n_reps.
    # Implementation MUST use common random numbers across the
    # paired unperturbed/perturbed runs (see physics_primitives.run_paired).

autocorrelation_window -> int
    # The number of recent integration steps the engine retains
    # for correlation measurement. Must be ≥ several τ_env to
    # resolve any meaningful γ_A. Typical value: 10000 steps at
    # DT=0.01 (= 100 time units, covers ~70 τ_env on the lattice).
```

The `phase` attribute in RFC-001 becomes a method `phase()` that extracts regime from the current correlation window. Static "phase" doesn't make sense in the dynamical framework.

### §4.3 Cluster — minor

`separation_bound()` formula change is the only substantive edit: replace `ε_min` with `γ_min` and `E*` with `Φ*`. The measurement of `γ_min` SHOULD be the minimum over adjacent-constraint γ_ij's from the cluster's current correlation window. Emit a `MeasurementUnresolvedEvent` when γ_min falls below the noise floor (all three τ's pinned) — observed at N≥5 in the Task A separation test, bounds the validity of the theorem on a given substrate.

---

## Amendment implications

- **AMEND-001 (Temporal Frustration Decay)** → should upgrade to **INTRINSIC** in RFC-002. Task A's `cross_dissipation` measurement already operates on windowed trajectories; "temporal decay" is the semantics, not a bolt-on. The `τ_ij` decay-timescale from AMEND-001 becomes the `autocorrelation_window` length.
- **AMEND-002 (Commit-Driven Inhibitory Routing)** → stays **PROPOSED** but notation cleans up: replace `ε` with `γ`; on phase-c commit events, adjust the A-B γ_ij estimate's window weights.
- **AMEND-003 (Lateral Maintenance Field)** → stays **PROPOSED**. The Boltzmann-weight form `exp(-ε_ij/k_BT)` cleanly maps to a correlation-window form `exp(-|γ_ij|·τ_window)`. Task A did not exercise this; the derivation is straightforward but should be written carefully.
- **AMEND-004 (ObservationSocket)** → stays **RATIFIED** as-is; framework-agnostic.
- **A.1.1 JAXSubstrate** → stays **RATIFIED** with compatibility note: gradient/hessian remain JIT-able; observable extraction (autocorrelation, FDR) is NumPy/FFT. These are the right boundaries; don't try to JIT the trajectory-operator layer.
- **A.1.2 AutoCluster** → stays **RATIFIED** with re-tuning note: population rules reference `dominant_phase`, which is now a window-resolved computation. Thresholds will need per-substrate calibration.
- **A.1.3 LLMConstraintEncoder** → stays **RATIFIED**, framework-agnostic.
- **A.1.4 Scale Validation** → mark as **DEFERRED** pending re-run under the flux-budget framework. The energy-budget result remains valid in its framework; a parallel flux-budget test is part of the next RFC iteration's validation.

---

## One new event type earned by the dynamical framework

Task A's separation-theorem experience justifies adding a single event to §6:

```
MeasurementUnresolvedEvent:
    cluster_id    : str
    observable    : str            # which γ_A / γ_ij / FDR measurement
    reason        : str            # e.g., 'τ_below_noise_floor'
    window_span   : (t_start, t_end)
```

Emitted when an observable's autocorrelation cannot be resolved above the thermal noise floor (all τ's in the computation collapse). Enables the cluster/network to respond: extend the correlation window, reduce constraint stiffness, or shed load. Without this event, failures are silent — measurements just return noisy garbage. This is the one new event type the dynamical framework forces; no others need adding.

---

## What Task A did NOT do (scope-managed)

- Did not run the Scale Validation test under the flux-budget framework. Deferred to a future session; the A.1.4 ratified result stands as energy-budget baseline.
- Did not exercise AMEND-002 (commit-driven routing) or AMEND-003 (lateral maintenance field) empirically. These remain proposals; the RFC should present them as clean derivations from the new framework, not validated mechanisms.
- Did not port the brain's engine code to use the new observable methods. That's a separate implementation task, guided by RFC-002's interface spec.
- Did not write `RFC-002-MPC-BRAIN.md`. That is this next session's only deliverable.

---

## Files delivered from Session A

All six are in this session's attachment set:

- `mpc_lattice.py` (56 KB, 1245 lines)
- `physics_primitives.py` (11 KB, 305 lines, unchanged from prototyping)
- `mpc_trajectories.png`
- `mpc_fdr_atlas.png`
- `mpc_separation.png`
- `mpc_hessian_probe.png`

They are reference material for RFC-002. The RFC does not need to re-deliver them.

---

*End of state document. Open `HANDOFF_B_PROMPT.md` for the task specification.*
