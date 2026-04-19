# Hand-off Prompt — RFC-002 Rework (Task B of the Two-Task Arc, Revised)

*This prompt supersedes `HANDOFF_B_PROMPT.md`. The differences are load-bearing: the foundational paper was reconciled between sessions, and the reconciliation changes the disposition of one amendment and the structure of the §3 FDR discussion. Read this prompt straight through before opening any other document.*

---

## What happened between sessions

The foundational paper `On the Dynamical Limits of Boolean Algebra as a Theory of Inference` was reworked into `v3_On_the_Dynamical_Limits_of_Boolean_Algebra_as_a_Theory_of_Inference.md`. The rework introduced a formal upgrade to §7 — a generalized Langevin equation in trail vectors $d_A(t)$, a Martin–Siggia–Rose / Janssen–De Dominicis path integral, and a tensorial Fluctuation–Dissipation signature — while preserving the full formal apparatus of v1 (Theorem 6.1 with proof sketch, §5 falsifiability conditions, §8 worked three-constraint frustration example).

Two downstream consequences for RFC-002:

1. **AMEND-001 (Temporal Frustration Decay) becomes OBSOLETE, not INTRINSIC.** §7.8 of the paper ("Emergent Forgetting") argues that under the trail-vector formulation, decay is a measurement consequence of the trail dynamics: unreinforced trails naturally shrink and their geometric projections onto neighboring trails go to zero, driving $\gamma_{ij}$ below the noise floor without any scheduled rule. An explicit decay scheme is redundant scaffolding over the physics. RFC-002 §9 MUST mark AMEND-001 as superseded by §7.8 of the paper, not upgraded to INTRINSIC as HANDOFF_B had proposed.

2. **The FDR signature is now stated at two levels: scalar per-regime and tensorial along trail axes.** The scalar per-regime signature (unity in r, aging in s, depressed stable in c, non-monotonic/negative in k) is what Task A validated on a Markovian overdamped Langevin substrate. The tensorial refinement ($X_\parallel \ll 1$, $X_\perp \approx 1$) is a sharper prediction that requires the substrate to expose trail geometry. The two are consistent: the scalar signature is the diagonal projection of the tensor along the dominant trail. RFC-002 MUST treat the scalar measurement as a valid special case and the tensorial measurement as an optional stronger test, not as competing claims.

Everything else in HANDOFF_B is carried forward. The task statement below is the consolidated version; use it rather than cross-referencing the old prompt.

---

## Files to attach to this session

All required, in this reading order:

1. **`HANDOFF_C_PROMPT.md`** — this file. Supersedes HANDOFF_B.
2. **`v3_On_the_Dynamical_Limits_of_Boolean_Algebra_as_a_Theory_of_Inference.md`** — the foundational paper. Reference for formal questions. Do not use the original or v2; v3 is the reconciled canonical version.
3. **`SESSION_A_STATE.md`** — crystallized output of Task A. Load-bearing on what the observables actually do on the substrate. Lists interface implications for RFC-002. Most of its guidance is still correct; the one exception is its AMEND-001 disposition (it follows HANDOFF_B on "INTRINSIC" — this prompt supersedes that point).
4. **`MPC_practical_notes.md`** — engineering companion. The six observables and the priority-ordered cut list.
5. **`RFC-001-MPC-BRAIN.md`** — the RFC to rework. Includes Amendment Set A (Session 2 ratifications: JAXSubstrate, AutoCluster, LLMConstraintEncoder, Scale Validation; plus AMEND-004 ObservationSocket).
6. **`mpc_lattice.py`** — the rebuilt lattice. Read it as reference — the interface you specify in RFC-002 should be something a Python port of `mpc_lattice.py` could satisfy.
7. **`physics_primitives.py`** — the validated observable primitives (`run_langevin`, `measure_fdr`, `survival_margin`, `cross_dissipation`). These are the primitives the RFC's substrate interface must ultimately expose.
8. **Four PNGs** (`mpc_trajectories.png`, `mpc_fdr_atlas.png`, `mpc_separation.png`, `mpc_hessian_probe.png`) — attach if the session supports image input; they illustrate the physics the new interface must surface. `mpc_fdr_atlas.png` is the scalar FDR atlas; note that it is the scalar-slice validation of the paper's tensorial claim, not the full empirical program.

If any of these are missing, stop and request them before starting. **Do not** attach the original paper or v2; v3 is the single source of truth.

---

## Task statement

Produce `RFC-002-MPC-BRAIN.md` that:

### 1. Inherits unchanged sections from RFC-001 by reference — do not copy-paste

- §2 Terminology (minor updates to add dynamical terms)
- §5 Observation Protocol (largely framework-agnostic; one clarification needed, see Interface Guidance below)
- §6 Event Protocol (add the single new event type)
- §7 Measurement Protocol (pure architecture; survives verbatim)
- §8 Interaction Rules (survives verbatim)
- §10 What This Protocol Deliberately Excludes (survives verbatim)
- The four-layer hierarchy substrate → engine → cluster → network (§4 shell)
- AMEND-004 ObservationSocket (preserved as-is, pure interface design)

### 2. Replaces §3 (Energy Invariant) wholesale

§3 in RFC-001 is written against static thresholds `E_c, E_s` and Hessian-eigenvalue classification. The replacement is a **Survival Invariant** built on `γ_A`, `γ_ij`, and FDR shape.

- **§3.1 Phase classification** — from the `(|γ_A|, τ_A/τ_env, γ_ij, FDR_slope)` tuple, NOT energy thresholds. See "Classifier learned in Task A" below.
- **§3.2 Landauer bound** — survives verbatim. Landauer erasure cost is a thermal-floor quantity, not active-matter; paper §7.3 "Irreversible bookkeeping".
- **§3.3 Budget enforcement** — reframe as **flux-budget** enforcement: engine MUST NOT maintain a constraint set whose `Φ_required` exceeds `Φ*`. Mathematical structure of the bound is unchanged; the bounded quantity changes from `E(Γ*)` to `Φ_required(Γ*)`. The soft-boundary form (quadratic penalty over sustained overdrafts) is what the paper §7.6 specifies; implementations MAY use either a hard cap or a soft penalty.
- **§3.4 Maintenance cost** — reframe against `|γ_A|`: maintenance force scales with survival margin, not with a barrier height. The `barrier_strength ∈ [0,1]` handle in RFC-001 maps naturally to `|γ_A| / γ_A^*` where `γ_A^*` is a substrate normalization.

### 3. Reworks §4 interfaces

- **§4.1 Substrate** — keep `energy`, `gradient`, `hessian`, `register`, `update_λ`, `deregister`, `frustration`. ADD:
  - `autocorrelation(V_obs, traj) -> C(t)`
  - `bath_trajectory() -> traj` (needed to measure `τ_env`; flagged in SESSION_A_STATE as a real interface implication)
  - `survival_margin(V_obs, traj, bath_traj) -> (γ_A, τ_A, τ_env)`
  - `cross_dissipation(V_i, V_j, traj) -> (γ_ij, τ_i, τ_j, τ_ij)`
  - `register_observable(constraint_id, fn) -> None` (V_obs need not equal V_potential; default is identity)
  - OPTIONAL: `trail_vector(constraint_id, window) -> vector`. Substrates with an explicit memory-kernel representation SHOULD expose this; substrates without one (pure overdamped Markovian) MAY omit it, in which case tensorial FDR measurement is unavailable and only the scalar signature is used.
- `hessian` stays. Documentation changes: it is now the **equilibrium baseline**, not the phase classifier. Specifically, `τ^equilibrium ≈ 1/(2·D_eff·λ_min(H))` is the null hypothesis against which measured τ is compared; disagreement is the `D_active ≫ D_thermal` detector (paper §7.3). The `λ_min < 0 ⇒ phase = k` rule in RFC-001 §3.1 is REMOVED.
- `classify(v)` is no longer a pure function of `v`. Signature change: `classify(trajectory_window) -> Phase`.
- `frustration(v)` is no longer a pure function of `v`. Signature change: `frustration(trajectory_window) -> dict[(id,id), γ_ij]`.

- **§4.2 Engine** — `phase` becomes `phase()` (a method, not a static attribute), derived from current correlation-window observables. ADD: `fdr_profile(V_obs, h_mag, n_burnin, n_resp, n_reps) -> (tau_grid, C, chi)`. Implementation MUST use matched-noise paired trajectories (common random numbers) — see `physics_primitives.run_paired` and the Interface Guidance §2 below. The Engine interface now implies the engine holds a rolling trajectory buffer sized to the correlation window — specify window length parameter and ring-buffer semantics.

- **§4.3 Cluster** — `separation_bound()` formula changes from `sqrt(2 E*/(α ε_min d_avg))` to `sqrt(2 Φ*/(α γ_min d_avg))`. Same shape, new quantities. `enforce_separation()` logic survives (it was already written against the bound, not the budget directly). At very high N on a finite substrate, all three τ's in the γ_ij computation can collapse to the noise floor, rendering γ_min unresolvable — emit `MeasurementUnresolvedEvent` (new event type, below) and fail safe.

- **§4.4 Network** — survives. The routing function uses `mean_frustration` between clusters; in the new framework this becomes `mean_cross_dissipation`. One-word-swap change to the spec.

### 4. Amendment dispositions

- **AMEND-001 (Temporal Frustration Decay) → OBSOLETE, superseded by paper §7.8.** The new framework makes temporal decay a consequence of trail-vector mechanics, not a scheduled rule. RFC-002 §9 MUST state this explicitly: implementations built on the trail-vector formulation SHOULD NOT include an explicit decay scheduler; `γ_ij` measurements over a sliding correlation window produce decay for free. The `τ_ij` decay-timescale parameter from AMEND-001 is absorbed into the engine's `correlation_window` length parameter (a single substrate-level knob, not a per-pair schedule).

- **AMEND-002 (Commit-Driven Inhibitory Routing) → PROPOSED, cleaned up.** Survives with notation cleanup. On phase-transition-to-c events from cluster A, the network adjusts `γ_ij` estimates for the A-B pair by narrowing or widening the correlation window. Keep the learning-rule structure; replace ε notation with γ notation.

- **AMEND-003 (Lateral Maintenance Field) → PROPOSED, derived not guessed.** The Boltzmann weight `exp(-ε_ij / k_BT)` in RFC-001 becomes a correlation-based coupling. Suggested form: `w_ij = exp(-|γ_ij| · τ_window)`. Derive rather than guess — the window-product form comes out of the joint-observable correlation spectrum directly. Note interaction with the window parameter: when `γ_ij` is re-measured on a new window, `w_ij` updates too.

- **AMEND-004 ObservationSocket → RATIFIED as-is.** Pure interface design, framework-agnostic.

### 5. Preserves Amendment Set A ratifications

Each requires a compatibility note for the new framework:

- **JAXSubstrate (A.1.1)** — `gradient` and `hessian` are unchanged signatures; still JIT-able. The new observable methods (`autocorrelation`, `survival_margin`, `cross_dissipation`) are NOT naturally JIT-able because they operate on trajectories (time-series), not single configurations. JAX acceleration is relevant to the Langevin STEP (which uses `gradient`), not to the observable extraction. Document this split: JAXSubstrate accelerates inner-loop integration; observable extraction is vanilla NumPy / FFT.
- **AutoCluster (A.1.2)** — self-regulation logic changes from `dominant_phase` thresholds to dynamical phase readout. Rules may need re-tuning. Mark as RATIFIED with re-tuning note.
- **LLMConstraintEncoder (A.1.3)** — survives; no framework dependency.
- **Scale Validation (A.1.4)** — mark as DEFERRED. The empirical result is still valid under the energy-based framework; a parallel validation under the flux-based framework is deferred to the next benchmark cycle.
- **AMEND-004 ObservationSocket** — survives as-is.

### 6. Add the one new event type

```
MeasurementUnresolvedEvent:
    cluster_id    : str
    observable    : str            # which γ_A / γ_ij / FDR measurement
    reason        : str            # e.g., 'τ_below_noise_floor'
    window_span   : (t_start, t_end)
```

Emitted when an observable's autocorrelation cannot be resolved above the thermal noise floor (all τ's in the computation collapse). Enables the cluster/network to respond: extend the correlation window, reduce constraint stiffness, or shed load. This is the ONE new event type permitted; no others should be added.

---

## Classifier learned in Task A — use this for §3.1

The rebuilt lattice's regime classifier correctly labels all four ground-truth scenarios on a Markovian overdamped Langevin substrate. Use its logic as the default §3.1 implementation:

```
given  stats_γ_A, stats_γ_ij, fdr_slope:

  if |γ_A| < GAMMA_A_RESET_BAND  AND  0.75 < τ_A/τ_env < 1.33:
      → r   (bath-equilibrated)

  if τ_A < TAU_CONFLICT_FLOOR  (system deeply pinned, τ_A collapsed):
      if fdr_slope is available:
          → k  if fdr_slope < 0.5
          → c  otherwise
      else:                              # fallback
          → k  if |γ_ij| > 3 × GAMMA_IJ_K_FLOOR
          → c  otherwise

  if γ_ij > GAMMA_IJ_K_FLOOR  (non-pinned destructive interference):
      → k

  → s   (everything else)
```

Thresholds in the lattice are calibrated to its substrate. The RFC MUST specify that thresholds are substrate-dependent and MUST be calibrated per-implementation. It MUST NOT hard-code numeric values.

### Load-bearing caveat for §3.1 — substrate profiles

On **Markovian overdamped Langevin substrates**, `γ_A` and `γ_ij` SIGNS can invert vs. the paper's Table 1 predictions. This is a substrate-level artifact: the paper's sign predictions presuppose memory-kernel (non-Markovian) dynamics per §7.1–§7.2 (generalized Langevin with trail vectors). Markovian approximation collapses the memory structure and inverts the sign patterns — while preserving the magnitudes and the FDR shape-by-regime signature.

The RFC MUST:

- Specify regime classification in terms of `|γ_A|` (magnitude) not `γ_A` (sign) as the substrate-profile-independent default.
- Specify that FDR slope is the primary c/k discriminator on Markovian substrates; γ_ij sign is a useful secondary signal on non-Markovian substrates.
- Define two **substrate compliance profiles**:
  - **Profile M (Markovian / overdamped)** — implements Langevin step with memoryless noise; classifier uses magnitudes and FDR slope; tensorial FDR unavailable; `trail_vector` method may be omitted.
  - **Profile G (generalized Langevin / non-Markovian)** — implements GLE with memory kernels; classifier MAY use the paper's sign-based rules; `trail_vector` method SHOULD be exposed; both scalar and tensorial FDR measurements are available.
- Be explicit that choice of profile is a substrate-implementation decision, not an amendment. Task A validates Profile M; Profile G is the target for future substrate implementations.

This split is the most important design decision in RFC-002. Do not bury it.

---

## Interface guidance — lessons from Task A

1. **`V_obs` is not the proposition.** The paper's γ_A and γ_ij are defined in terms of an observable `V_A` that "projects the constraint onto the trajectory". In practice there are many valid V_obs for a given constraint, and the choice affects numerical quality. The Substrate interface SHOULD expose `register_observable(constraint_id, fn)` and MUST document that `V_A` used for correlation measurement need not equal the constraint potential `fn_A` used for the Langevin force — though the default is `V_A ≡ fn_A`.

2. **FDR measurement requires matched-noise paired trajectories.** Non-negotiable. Without common-random-numbers variance reduction, the response signal is swamped by ensemble fluctuation at reasonable replica counts. `fdr_profile` MUST be specified in a way that permits the matched-noise implementation. Recommend signature: `fdr_profile(V_obs, h_mag, n_burnin, n_resp, n_reps) -> (tau, C, chi)`.

3. **Per-scenario perturbation scaling is substantive.** The `h_mag` for FDR measurement CANNOT be a single global constant; it must scale with per-constraint variance (heuristic: `h_mag ~ 0.3 × sqrt(C(0))`). The RFC should specify that `fdr_profile` accepts a per-call `h_mag` and that the implementation SHOULD auto-scale from a pilot measurement if not provided.

4. **Effective temperature in FDT is `D_eff`, not `k_BT`.** In active-matter regimes the FDT line on a parametric FDR plot has slope `1/D_eff`, not 1. The RFC's §3 discussion and §4.2 `fdr_profile` specification MUST be written in terms of `D_eff = D_thermal + D_active` per paper §7.3. The naïve substitution `k_BT → D_eff` in the FDR formula is correct and should be called out.

5. **Hessian is an equilibrium baseline, not a phase classifier.** The RFC-001 language "min eigenvalue of H(v) < 0 ⇒ phase = k" is wrong and MUST be removed. Hessian's new role: predict `τ_A^equilibrium = 1/(2·D_eff·λ_min(H))` as the null hypothesis for Profile M substrates. Disagreement between `τ_A^measured` and `τ_A^equilibrium` is the `D_active ≫ D_thermal` detector (paper §7.3). One subtlety: the Hessian prediction assumes observable-eigenmode alignment — if V_A is not aligned with the Hessian's slow eigenmode, the comparison is not clean. Document this; do not hand-wave it.

6. **Separation Theorem with dynamical γ_ij has a parameter regime.** At very high N on a finite substrate, all three τ's in the γ_ij computation collapse to the noise floor and `γ_ij` becomes unresolvable (observed in Task A at N ≥ 5 on a 2D ring). The RFC's §4.3 `separation_bound()` should specify that measurements are only valid in a parameter range where `τ_i`, `τ_j`, `τ_ij` are all resolvable. Implementations MUST emit `MeasurementUnresolvedEvent` when the bound cannot be reliably computed.

---

## Scope discipline

- RFC-002 is a **focused rework**, not a rewrite. Target length: 60%–100% of RFC-001's length. Not more.
- Do not introduce new amendments beyond what RFC-001/Amendment Set A already names. Upgrade or obsolete existing ones; don't invent.
- The `MeasurementUnresolvedEvent` noted above is the one permitted new event type.
- Write in RFC style. Terse, numbered, precise. Use "MUST / MUST NOT / SHOULD / MAY" with RFC 2119 rigor. Reference RFC-001 by section number where inheriting unchanged.
- The paper (v3) is the formal reference. This prompt supersedes SESSION_A_STATE on the AMEND-001 disposition specifically. For all other observable-implementation details, SESSION_A_STATE is current.

---

## Sequencing and output

Write the whole document in one pass; don't iterate section-by-section before the full draft exists. Target structure:

1. Front-matter (title, abstract, status-of-memo) — standard RFC boilerplate. Declare RFC-002 obsoletes the static §3 of RFC-001 but preserves Amendment Set A.
2. §1 Introduction — what changed and why, including the trail-vector / GLE upgrade to the paper and the Task A validation.
3. §2 Terminology — additions: `survival margin`, `cross-dissipation`, `FDR slope`, `effective diffusion`, `correlation window`, `trail vector`, `substrate profile`.
4. §3 The Survival Invariant — the replacement for Energy Invariant.
5. §4 The Brain Protocol — reworked interfaces, including substrate profiles M and G.
6. §§5–8 — inherited by reference with specified deltas.
7. §9 Amendments — updated statuses (AMEND-001 **OBSOLETE**, AMEND-002/003 PROPOSED-clean, AMEND-004 RATIFIED, Scale Validation DEFERRED).
8. §10 Exclusions — inherited verbatim.
9. §11 Reference Implementation — cite `mpc_lattice.py` as the Profile M validation rig. The reference implementation path for the production brain remains `mpc_engine_rfc001.py + mpc_session2.py` + pending RFC-002 port.

Output: single markdown file, `RFC-002-MPC-BRAIN.md`. Nothing else.

---

## If anything conflicts

- The paper (v3) is the formal reference for physics.
- This prompt supersedes SESSION_A_STATE on AMEND-001 only; SESSION_A_STATE is current for everything else.
- This prompt supersedes HANDOFF_B in its entirety.
- RFC-001 is the structural template — follow its section organization, preserve its phrasing style, inherit unchanged sections by reference not by copy.

When doubt persists, keep the interface minimal and cut the elaboration.

---

*End of hand-off. Go write.*
