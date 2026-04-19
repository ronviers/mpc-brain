MPC Working Group                                         Session Notes
Request for Comments: 004                                  April 2026
Obsoletes: RFC-001 §3 (Energy Invariant)
Preserves: RFC-001 Amendment Set A
Category: Standards Track (DRAFT / INACTIVE)


        MPC-BRAIN: The Survival Invariant and Dynamical Interfaces
              (Replacement for the Energy Invariant of RFC-001)


Abstract

   This document revises MPC-BRAIN to reflect the dynamical
   reformulation of the foundational paper (v3, §7).  The static
   energy-threshold invariant of RFC-001 §3 is replaced wholesale by
   a Survival Invariant defined on correlation-time observables:
   survival margin gamma_A, cross-dissipation gamma_ij, and the shape
   of the Fluctuation-Dissipation Ratio.  The four-valued MPC state
   space {c, s, k, r} is unchanged; the means by which conforming
   implementations classify and enforce it are not.

   The substrate, engine, cluster, and network interfaces of
   RFC-001 §4 are reworked to expose trajectory-based observables
   while preserving the four-layer hierarchy and the event-bus
   architecture.  Two substrate compliance profiles are defined:
   Profile M (Markovian / overdamped Langevin) and Profile G
   (generalized Langevin with memory kernels).  Task A of the
   validation program has exercised Profile M.

   §§5 through 10 of RFC-001 are inherited with specified deltas.
   Amendment Set A of RFC-001 is preserved intact; dispositions of
   the four proposed amendments (AMEND-001..004) are updated in §9
   of this document.


Status of This Memo

   DRAFT SPECIFICATION - INACTIVE.

   This document is a draft specification for a future kernel
   major-version revision (mpc_kernel 0.x -> 1.0). It is complete,
   reviewed, and internally consistent, but it is NOT CURRENTLY
   ACTIVE. RFC-002-MPC-PROJECT-STRUCTURE §4.4 explicitly forbids
   packs from redefining phase classification outside of a kernel
   major-version increment.

   If you are opening RFC-004 to implement it: Stop. Check whether
   the activation preconditions below hold. If they do not, close
   the document and return to the RFC-002 migration plan.

   Activation Preconditions (Dependency Order):
      (a) Session 5 has shipped (maze experiment passing TASK-5.1
          through TASK-5.6).
      (b) S6 housekeeping has completed (RFC-002 §8, Steps 3-5).
      (c) The default pack manifest (RFC-002 §5.4) has settled.
      (d) An RFC-002 revision proposes activation of RFC-004 as a
          kernel major-version bump (0.x -> 1.0), reviewed per
          RFC-002 §5.3.

   When activated, this RFC is a focused rework of RFC-001 §3 and
   §4. It obsoletes the Energy Invariant; all other RFC-001 content
   is preserved, inherited by reference, or carried forward with
   small notational deltas called out in the relevant section.

   Document Identity Note: This file was originally drafted under
   the name RFC-002-MPC-BRAIN.md but was renamed to RFC-004 to
   resolve a naming collision with RFC-002-MPC-PROJECT-STRUCTURE.
   All internal text has been updated to reflect its identity as
   RFC-004.


Table of Contents

   1.  Introduction
   2.  Terminology (additions)
   3.  The Survival Invariant (Non-Amendable)
       3.1  Phase classification
       3.2  Landauer bound
       3.3  Flux-budget enforcement
       3.4  Maintenance cost
   4.  The Brain Protocol
       4.1  Substrate Interface
       4.2  Engine Interface
       4.3  Cluster Interface
       4.4  Network Interface
   5.  The Observation Protocol (inherited with clarification)
   6.  The Event Protocol (inherited; one new event type)
   7.  The Measurement Protocol (inherited verbatim)
   8.  Interaction Rules (inherited verbatim)
   9.  Amendments (updated dispositions)
   10. What This Protocol Deliberately Excludes (inherited verbatim)
   11. Reference Implementation
   12. Related Artifacts and Directory Structure


1.  Introduction

   Between the publication of RFC-001 and this document, the
   foundational paper was reworked (v3) to replace its informal
   Trajectory Space section with a formal non-equilibrium
   formulation: a generalized Langevin equation in trail vectors
   d_A(t) (paper §7.2), a Martin-Siggia-Rose / Janssen-De Dominicis
   path integral (paper §7.4), and a tensorial Fluctuation-
   Dissipation signature (paper §7.7).  The four-regime state
   space {c, s, k, r} is unchanged; what has changed is the nature
   of the quantities that identify a regime.

   Two downstream consequences for this RFC:

   (a) RFC-001 §3 classified phase by static thresholds on E(v)
       and on eigenvalues of H(v).  Under the dynamical
       formulation, phase is a property of a trajectory, not of a
       point.  The primary classifiers are correlation-time
       observables measured on a rolling trajectory window.  §3 is
       replaced; §4 exposes the measurement interfaces.

   (b) Paper §7.8 ("Emergent Forgetting") shows that unreinforced
       trail vectors naturally shrink, driving their geometric
       projections onto neighboring trails below the noise floor
       without any scheduled rule.  This obsoletes the motivation
       for AMEND-001 (Temporal Frustration Decay), marked
       superseded in §9.1.

   Validation Status:
   The dynamical framework was validated (Task A, April 2026) on a
   four-scenario Langevin lattice (committed, suspended, conflict,
   reset). The four-regime classifier of §3.1 labels all four
   ground-truth scenarios correctly on a Markovian overdamped
   Langevin substrate (Profile M, §4.1). The scalar per-regime FDR
   signature of paper §7.7 is reproduced. The Separation Theorem
   holds at N in {2, 3, 4} on a 2D ring.

   What was NOT validated (deferred):
   (a) The tensorial FDR signature (paper §7.7, X_parallel << 1,
       X_perp ~ 1) requires a Profile G substrate exposing trail
       geometry. Task A ran on Profile M.
   (b) The flux-budget enforcement of §3.3 was exercised at low N
       only. The at-scale rerun is deferred (see §9.5, A.1.4).

   The RFC-001 four-layer hierarchy substrate -> engine -> cluster
   -> network, the event bus, and the Measurement Protocol all
   survive unchanged.  AMEND-004 (ObservationSocket) is unaffected
   and remains RATIFIED.


2.  Terminology (additions to RFC-001 §2)

   The key words "MUST", "MUST NOT", "REQUIRED", "SHALL",
   "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and
   "OPTIONAL" are as in RFC 2119.

   All terms defined in RFC-001 §2 remain in force.  Additions and
   refinements follow.

   Survival margin  (gamma_A)
      gamma_A = 1/tau_A - 1/tau_env.  The difference between the
      decay rate of the constraint's autocorrelation (tau_A) and
      that of the unconstrained bath (tau_env).  The primary
      regime-depth observable.  Paper §2.

   Cross-dissipation  (gamma_ij)
      gamma_ij = 1/tau_{i and j} - max(1/tau_i, 1/tau_j), measured
      from the joint observable V_i + V_j along a shared
      trajectory.  Under Profile G, gamma_ij > 0 is the k-state
      signature (destructive interference); under Profile M,
      |gamma_ij| magnitude is load-bearing and sign MAY invert
      (§3.1).

   FDR slope
      Late-time slope of the parametric plot chi(tau) versus
      [C(0) - C(tau)] / D_eff.  Unity slope is the FDT reference
      (r-regime).  Per-regime shape signature: §3.1 and paper §7.7.

   Effective diffusion  (D_eff)
      D_eff = D_thermal + D_active, per paper §7.3.  MPC applies in
      the regime D_active >> D_thermal.  In the fluctuation-
      dissipation relation, the effective temperature scale is
      D_eff, not k_BT.

   Correlation window
      Contiguous trajectory segment over which autocorrelation-
      based observables are measured.  Substrate-level parameter
      on the engine; MUST be long enough to resolve several
      tau_env.

   Trail vector  (d_A(t))
      d_A(t) = integral from -infinity to t of
      K_A(t-s) * x_dot(s) ds, per paper §2 and §7.2.  Geometric
      aggregate of past motion weighted by the memory kernel.
      Exposed only by Profile G substrates (§4.1).

   Substrate profile
      A compliance profile.  Profile M (Markovian / overdamped
      Langevin) is the minimum level; Profile G (generalized
      Langevin, non-Markovian) is the strict superset required
      for tensorial FDR.  See §4.

   Measurement resolvability
      The condition that all tau values entering a given
      observable lie above the thermal noise floor.  When tau_i,
      tau_j, or tau_{i and j} collapse, the corresponding gamma
      is unresolvable and a MeasurementUnresolvedEvent (§6) MUST
      be emitted.

   Phase  (refined)
      One of {c, s, k, r}.  In RFC-001 this was derived from v;
      under this RFC it is derived from a trajectory window.  All
      RFC-001 uses of "phase" are reinterpreted accordingly.

   Frustration  (refined)
      RFC-001 epsilon_ij (pairwise joint energy) is replaced by
      gamma_ij (pairwise cross-dissipation, inverse time).  All
      RFC-001 uses of "frustration" are reinterpreted; notation
      is updated throughout.


3.  The Survival Invariant  (Non-Amendable)

   This section replaces RFC-001 §3 in full.  Its four parts are
   the physical content of MPC expressed in correlation-time
   observables.  They are not subject to amendment.

   3.1  Phase classification

      Given, for a trajectory window observed on a registered
      constraint A:

         |gamma_A|       -- magnitude of the survival margin
         tau_A / tau_env -- ratio of constraint to bath decay times
         gamma_ij        -- cross-dissipation with coupled constraints
         fdr_slope       -- late-time slope of the parametric FDR plot

      a conforming substrate MUST classify the constraint's phase
      by the following procedure:

         if |gamma_A| < GAMMA_A_RESET_BAND
            AND  0.75 < tau_A/tau_env < 1.33:
               -> r

         if tau_A < TAU_CONFLICT_FLOOR:
               # constraint is deeply pinned; tau_A has collapsed
               # to the substrate noise floor.  c and k are not
               # distinguishable from trajectory observables alone.
               if fdr_slope is available:
                  -> k  if fdr_slope < 0.5
                  -> c  otherwise
               else:
                  -> k  if |gamma_ij| > 3 * GAMMA_IJ_K_FLOOR
                  -> c  otherwise

         if gamma_ij > GAMMA_IJ_K_FLOOR
            (non-pinned destructive interference):
               -> k

         -> s   (otherwise)

      The constants GAMMA_A_RESET_BAND, TAU_CONFLICT_FLOOR, and
      GAMMA_IJ_K_FLOOR are substrate-dependent calibration
      quantities.  Implementations MUST calibrate them per
      substrate and MUST NOT hard-code cross-implementation
      numeric defaults.  They MAY be exposed as tuneables.

      Implementations MUST NOT classify phase by any other means.
      In particular, the RFC-001 §3.1 rule

         "min eigenvalue of H(v) < 0  =>  phase = k"

      is REMOVED.  The Hessian retains a role as the equilibrium
      baseline (§4.1), not as a classifier.

      Substrate-profile caveat.  On Profile M (Markovian overdamped
      Langevin) substrates, the signs of gamma_A and gamma_ij can
      invert relative to the paper's Table 1 predictions.  This is a
      substrate-level artifact: the paper's sign predictions assume
      memory-kernel dynamics (paper §7.1-§7.2).  Markovian
      approximation collapses the memory structure and inverts the
      sign patterns while preserving magnitudes and the FDR
      shape-by-regime signature.  For this reason, the classifier
      above is expressed in |gamma_A| and in the sign of gamma_ij
      only when gamma_A itself is resolvable above the noise floor;
      when it is not (the "deeply pinned" branch), FDR slope is the
      required c-versus-k discriminator.

      Implementations that expose Profile G (§4.1) MAY additionally
      classify using the paper's sign-based rules when memory kernels
      are resolved; the magnitude-and-FDR classifier above remains the
      substrate-profile-independent default and MUST be available.

   3.2  Landauer bound

      RFC-001 §3.2 survives verbatim.  The Landauer floor is a
      thermal-bath quantity, independent of the substrate's active
      dynamics, and is unchanged by the active-matter framework
      (paper §7.3, "irreversible bookkeeping").

      Any transition to phase r MUST be associated with a minimum
      energetic cost of k_BT * ln(2) per bit of information erased.
      This cost MUST be emitted as a LandauerEvent on the bus.  It
      MUST NOT be silently discarded.

      Erasure cost accounting MAY include the correlation correction
      k_BT * ln(2) * (1 + I(H; {D_j})) when the mutual-information
      term is computable; when it is not, the floor is emitted.

   3.3  Flux-budget enforcement

      The RFC-001 rule "an engine MUST NOT take a step that would
      place E(v) above E*" is reframed.  The bounded quantity is
      Phi_required (the rate of negentropic flux required to
      maintain the active constraint set), not the energy at the
      current configuration:

         Phi_required(Gamma*) = sum_{i in Gamma*} |gamma_i|
                              + alpha * sum_{(i,j) in E} |gamma_ij|

      where Gamma* is the currently active constraint set, E its
      coupled-pair edge set, and alpha in (0, 1] the substrate-
      dependent coupling factor of Theorem 6.1 (paper §6).

      A conforming engine MUST NOT maintain a constraint set whose
      measured Phi_required exceeds Phi*.  Two compliance forms:

         Hard cap.  On any window for which Phi_required > Phi*,
            shed the weakest coupled constraints (lowest |gamma_i|
            or highest |gamma_ij| in the non-viable set) until the
            bound holds, emitting a BudgetResetEvent per reset.

         Soft cap (paper §7.6).  Apply a quadratic penalty on
            sustained overdrafts, permitting transient violations;
            "sustained" means persisting beyond the correlation
            window.  A BudgetResetEvent MUST be emitted when
            shedding is ultimately triggered by the penalty.

      The Separation Theorem bound (§4.3) is structurally unchanged:
      the bounded quantity transitions E* -> Phi* and
      epsilon_min -> gamma_min, preserving the sqrt-form.

   3.4  Maintenance cost

      The RFC-001 §3.4 handle "barrier_strength in [0, 1]" is
      reframed against the survival margin.  An engine in phase s
      MUST exert a non-zero maintenance force resisting collapse
      toward c or k.  The magnitude of this force MUST scale
      monotonically with the relative depth of the survival margin:

         maintenance_force_magnitude proportional to
            |gamma_A| / gamma_A_star

      where gamma_A_star is a substrate-level normalization
      constant (typical scale of the deepest-supportable survival
      margin on that substrate).  Implementations MAY retain the
      barrier_strength notation from RFC-001 internally by
      identifying barrier_strength := |gamma_A| / gamma_A_star,
      clipped to [0, 1].

      The physical content of the rule (that a Prigogine-type
      dissipative structure requires active flux to persist) is
      unchanged from RFC-001.  Only the quantity indexing the
      required flux has changed.

   These four rules are the Survival Invariant.  They are the
   physical content of MPC expressed in the dynamical framework.
   Amendments that relax any of them are out of scope.


4.  The Brain Protocol

   Section 4 reworks the four interfaces to expose trajectory-based
   observables.  The four-layer hierarchy is unchanged.  The event
   bus is unchanged.  Only the substrate and engine interfaces
   require substantive interface additions; cluster and network
   interfaces change by notation and by one formula.

   Substrate compliance profiles.  A conforming Substrate MUST
   declare one of:

      Profile M  (Markovian / overdamped Langevin)
         Implements Langevin dynamics with memoryless noise.
         Provides all required observable methods in §4.1.
         MAY omit the OPTIONAL trail_vector method.
         Tensorial FDR measurement is unavailable; only the scalar
         per-regime FDR signature is exposed.

      Profile G  (generalized Langevin / non-Markovian)
         Implements a generalized Langevin equation with explicit
         memory kernels, per paper §7.2.  Provides all Profile M
         methods AND the trail_vector method.  Tensorial FDR
         measurement (paper §7.7) is available via response
         functions computed along resolved trail axes.

   Profile declaration is a substrate-implementation decision, not
   an amendment.  Task A of the validation program exercises
   Profile M; Profile G is the target for future substrate
   implementations.

   4.1  Substrate Interface

      A conforming Substrate MUST expose the methods below.  Methods
      inherited unchanged from RFC-001 §4.1 are noted; their
      documentation is updated in places.  New methods are marked
      NEW.  Methods whose signature has changed are marked CHANGED.

      energy(v)                  -> float
         Inherited from RFC-001 §4.1.  Total constraint energy at
         configuration v, in units of k_BT.  Used by the Langevin
         step for force computation (gradient of energy) and by
         diagnostic tooling.  No longer used for phase classification.

      gradient(v)                -> vector[n]
         Inherited from RFC-001 §4.1.  First derivative of energy.

      hessian(v)                 -> matrix[n, n]        [CHANGED ROLE]
         Inherited as a method; its interpretation changes.
         hessian(v) is now the EQUILIBRIUM BASELINE predictor, not
         a phase classifier.  The equilibrium prediction for the
         relaxation time is

            tau_A^equilibrium ~ 1 / (2 * D_eff * lambda_min(H))

         evaluated at the energy minimum.  Disagreement between
         tau_A^measured and tau_A^equilibrium is the
         D_active >> D_thermal detector of paper §7.3.

         CAVEAT: the prediction assumes V_A is aligned with the
         slow eigenmode of H.  When V_A is misaligned, the
         comparison is not clean; implementations SHOULD either
         project V_A onto the slow eigenmode before comparison or
         document the misalignment as an uncontrolled systematic.

         hessian MUST be symmetric.  The RFC-001 §3.1 rule
         "lambda_min(H) < 0 => phase = k" is REMOVED.

      register(id, fn, lam)      -> Handle
         Inherited from RFC-001 §4.1.  Register a constraint
         function with stiffness lambda.  Returns an opaque handle.

      update_lambda(handle, lam)
         Inherited from RFC-001 §4.1.

      deregister(handle)
         Inherited from RFC-001 §4.1.  MUST NOT emit any event
         directly; the calling layer is responsible for emitting
         LandauerEvent.

      register_observable(
          constraint_id, V_obs)  -> None                    [NEW]
         Register an observable function V_obs: R^n -> R to be used
         for correlation measurement on the named constraint.  The
         observable used for gamma_A and gamma_ij measurement need
         NOT equal the potential used for the Langevin force: a
         constraint may be instantiated by a stiff quadratic
         penalty while its correlation signature is read from a
         different functional of the configuration.

         Default: if register_observable is not called for a given
         constraint_id, V_obs is set to the potential fn passed to
         register().

         The available choices of V_obs affect numerical quality;
         substrate documentation SHOULD specify the recommended
         default form for its geometry.

      autocorrelation(
          V_obs, traj)           -> array[C(t)]              [NEW]
         Compute the normalized autocorrelation C(t)/C(0) of the
         observable V_obs evaluated along trajectory traj.
         Implementations SHOULD use an unbiased FFT-based estimator
         (Wiener-Khinchin).  The tail of C(t) MUST be cut at the
         first time C(t) drops below a specified threshold; without
         this cutoff the integral-time estimators in
         survival_margin and cross_dissipation produce noise-
         dominated output on low-variance signals.

      bath_trajectory()          -> array                    [NEW]
         Return a trajectory of the substrate evolved under a weak
         bounded potential that excludes the constraint-imposed
         structure, of duration at least several tau_env.  Used as
         the tau_env reference in survival_margin.  This method is
         load-bearing: tau_env is not measurable from the
         constrained trajectory alone.  Implementations MAY cache a
         recent bath trajectory across calls; the staleness policy
         is implementation-defined but SHOULD be documented.

      survival_margin(
          V_obs, traj,
          bath_traj)  -> (gamma_A, tau_A, tau_env)          [NEW]
         Return the survival margin of V_obs computed from the
         constrained trajectory traj against the bath trajectory
         bath_traj.  tau_A and tau_env are integral autocorrelation
         times; gamma_A = 1/tau_A - 1/tau_env.  See paper §2.

      cross_dissipation(
          V_i, V_j, traj)
                  -> (gamma_ij, tau_i, tau_j, tau_ij)        [NEW]
         Compute the cross-dissipation for observables V_i and V_j
         along a shared trajectory.  The joint observable is the
         sum V_i + V_j by default; substrates whose geometry
         demands an alternative joint form (e.g., product or
         product of projections) MUST document the choice.

      classify(
          trajectory_window)     -> Phase                   [CHANGED]
         Phase classification per §3.1.  Signature change from
         RFC-001: classify is NO LONGER a pure function of v.  It
         takes a trajectory window and produces a phase over that
         window by executing the §3.1 procedure on observables
         computed from the window.

      frustration(
          trajectory_window)
                  -> dict[(id,id), gamma_ij]                [CHANGED]
         Pairwise cross-dissipations for all registered constraint
         pairs on the given trajectory window.  Signature change
         from RFC-001: frustration is no longer a pure function of v.
         The returned quantity is gamma_ij (inverse time), not
         epsilon_ij (energy); users of the prior interface MUST
         update their thresholds accordingly.

      trail_vector(
          constraint_id, window) -> vector[n]       [OPTIONAL, NEW]
         Return the trail vector d_A aggregated over the given
         window.  REQUIRED for Profile G substrates.  Profile M
         substrates MAY omit this method, in which case tensorial
         FDR measurement is unavailable and only the scalar FDR
         signature is used.

      A conforming Substrate MUST NOT hold a reference to any bus,
      calorimeter, or measurement component.

   4.2  Engine Interface

      A conforming Engine MUST expose:

      step(external_force)       -> vector[n]
         Inherited from RFC-001 §4.2.  Advance v(t) by one
         integration step.  MUST enforce the flux-budget invariant
         (§3.3).  MUST apply the maintenance invariant (§3.4).
         MUST emit PhaseTransitionEvent when phase changes, as
         computed by phase() over the current correlation window.
         MUST emit BudgetResetEvent when a reset is triggered.

      run(n_steps)               -> trajectory[n_steps, dim]
         Inherited from RFC-001 §4.2.

      phase()                    -> Phase                   [CHANGED]
         Signature change from RFC-001: phase is no longer a static
         attribute read off a single configuration.  It is a method
         that returns the classification of the engine's current
         correlation window via Substrate.classify.  Callers MUST
         invoke phase() as a method.

      correlation_window         -> int                      [NEW]
         The length, in integration steps, of the rolling
         trajectory buffer retained by the engine for observable
         computation.  MUST be at least several tau_env.  The
         default value is implementation-defined, substrate-
         dependent, and MUST be documented.  On the Task A
         reference lattice this is ~10000 steps at DT=0.01
         (~100 time units).

         correlation_window MAY be set externally; changes take
         effect on the next full window and MAY invalidate the
         current phase output for one window.

      detect_insight()           -> bool
         Inherited from RFC-001 §4.2.  Definition of insight is
         reframed from "sustained s -> c energy drop" to
         "sustained drop in sum |gamma_i| across engines"
         (paper §7.8 applied; see practical notes §3.5).
         Implementations MUST document their "sustained" and
         "recent" criteria.

      v                          -> vector[n]
         Inherited from RFC-001 §4.2.

      attention_scarcity         -> float  [0, 1]
         Inherited from RFC-001 §4.2.  Remains the effective
         temperature of the Langevin dynamics.  Note:
         attention_scarcity modulates D_thermal; D_active is
         controlled separately by Phi*.

      fdr_profile(
          V_obs, h_mag,
          n_burnin, n_resp,
          n_reps)        -> (tau_grid, C, chi)             [NEW]
         Measure the parametric Fluctuation-Dissipation Ratio for
         V_obs.  Returns the time grid, the spontaneous
         autocorrelation C(tau), and the integrated susceptibility
         chi(tau), from which the parametric plot chi vs
         [C(0) - C(tau)] / D_eff is constructed.

         Implementation MUST use matched-noise paired trajectories
         (common random numbers across paired unperturbed and
         perturbed runs); without this variance reduction the
         response signal is swamped by ensemble fluctuation at
         reasonable replica counts.  See physics_primitives.
         run_paired for a reference implementation.

         h_mag is the perturbation magnitude and MUST scale with
         the per-constraint variance (heuristic:
         h_mag ~ 0.3 * sqrt(C(0))).  If h_mag is not provided,
         implementations SHOULD auto-scale from a pilot measurement
         of C(0) and MUST document the pilot protocol.

         In active-dominated regimes the effective temperature in
         the FDR is D_eff, not k_BT (paper §7.3); the substitution
         k_BT -> D_eff is correct and is load-bearing in §3.1.
         The FDT reference on the resulting plot has unit slope in
         the coordinates given above.

      An Engine MUST hold a reference to exactly one Substrate and
      exactly one Bus.  It MUST NOT hold a reference to a
      Calorimeter.  It MUST maintain a rolling trajectory buffer
      sized to correlation_window; buffer semantics are ring-buffer
      by default.

   4.3  Cluster Interface

      A conforming Cluster MUST expose:

      load(constraints)
         Inherited from RFC-001 §4.3.

      diffuse(n_steps)
         Inherited from RFC-001 §4.3.

      separation_bound()         -> float                   [CHANGED]
         Compute N_max per Theorem 6.1.  The formula is
         structurally identical to RFC-001 §4.3; the quantities
         change:

            N_max = sqrt( 2 * Phi* / (alpha * gamma_min * d_avg) )

         where gamma_min is the minimum non-zero cross-dissipation
         over the currently active edge set of the constraint
         graph, measured over the current correlation window.

         Measurement resolvability:  If any of tau_i, tau_j, or
         tau_{i and j} in the gamma_ij computation collapses to
         the substrate noise floor for ALL coupled pairs, gamma_min
         is unresolvable.  In this case the cluster MUST emit a
         MeasurementUnresolvedEvent (§6) and MUST NOT return a
         numeric separation_bound value; the return is an
         implementation-defined sentinel (typically +infinity or
         None), and enforce_separation() MUST short-circuit to a
         conservative fallback (e.g., shed one weakest constraint
         and re-measure).  This is the N-too-large-for-substrate
         failure mode observed in Task A at N >= 5 on a 2D ring.

      enforce_separation()
         Inherited from RFC-001 §4.3.  Logic survives unchanged:
         the bound is what has changed, not the enforcement.  Each
         reset MUST cause a LandauerEvent on the bus.

      dominant_phase()           -> Phase                    [CHANGED]
         Signature change to a method, consistent with §4.2.
         The most frequent phase among engines over the recent
         correlation window.

      extract_commitment()       -> vector[n] | None
         Inherited from RFC-001 §4.3.

      shed_load(factor)
         Inherited from RFC-001 §4.3.  When called in response to
         a flux-budget violation, shedding SHOULD preferentially
         remove constraints whose individual |gamma_i| is small
         (weakly supported) or whose |gamma_ij| to the remaining
         set is large (most expensive coupled maintenance).

      A Cluster MUST hold a reference to exactly one Substrate and
      exactly one Bus.  Engines within a Cluster MUST share the
      same Substrate and the same Bus.

   4.4  Network Interface

      The RFC-001 §4.4 interface survives with one notational
      substitution.  A conforming Network MUST expose:

      add_cluster(id, ...)       -> Cluster
         Inherited from RFC-001 §4.4.

      route(src_id, tgt_id, signal)               [CHANGED: quantity]
         Compute the mean cross-dissipation between the src and tgt
         clusters (rather than mean frustration epsilon).  If
         mean_cross_dissipation < compat_threshold, call
         tgt.integrate(signal); otherwise call
         tgt.inject_conflict(signal).

         The threshold compat_threshold is now in inverse-time
         units (dimensions of gamma) rather than energy; existing
         deployments MUST recalibrate.

      step()
         Inherited from RFC-001 §4.4.

      bus                        -> Bus
         Inherited from RFC-001 §4.4.

      A Network MUST NOT create or hold a Calorimeter.


5.  The Observation Protocol  (inherited with clarification)

   RFC-001 §5 is inherited unchanged.  Observations are converted
   to constraint functions fn: R^n -> R+ and to stiffness values
   lambda in units of k_BT, per RFC-001 §5.  The shared-embedding
   assumption is unchanged.

   Clarification.  Under this RFC, a constraint's observable V_obs
   (used for gamma_A and gamma_ij measurement, §4.1) is not
   necessarily the same as its potential fn (used for the Langevin
   force).  The Observation Protocol continues to specify only fn
   and lambda; V_obs defaults to fn unless explicitly registered
   via Substrate.register_observable.  An observation encoder MAY
   (but is NOT required to) provide a recommended V_obs alongside
   fn.

   AMEND-004 (ObservationSocket) is unaffected.  The ConstraintSpec
   it produces MAY be extended to carry an optional V_obs field; if
   absent, the default fn behavior applies.  This extension is not
   required by this RFC.


6.  The Event Protocol  (inherited; one new event type)

   All events from RFC-001 §6 (PhaseTransitionEvent, LandauerEvent,
   BudgetResetEvent) are inherited unchanged in structure.  Their
   interpretation is reinterpreted as follows:

      PhaseTransitionEvent.from_phase, .to_phase
         Now refer to phase() over a trajectory window
         (§4.2), not to classify(v) of a configuration.

      BudgetResetEvent
         Now emitted in response to Phi_required(Gamma*) > Phi*
         (§3.3), not E(v) > E*.

   One new event type is added:

      MeasurementUnresolvedEvent:                              [NEW]
         cluster_id    : str
         observable    : str            # which gamma_A / gamma_ij
                                        # / FDR measurement
         reason        : str            # e.g., 'tau_below_noise_floor'
         window_span   : (t_start, t_end)

      Emitted when an observable's autocorrelation cannot be
      resolved above the thermal noise floor (all tau values in the
      computation collapse).  Enables the cluster or network to
      respond: extend the correlation window, reduce constraint
      stiffness, or shed load.  Without this event, failures are
      silent and measurements return noisy garbage.

      This is the ONE new event type permitted by RFC-004; future
      events MUST be introduced by amendment.

   Implementations MUST NOT emit events synchronously in a way that
   blocks the integration step.  Event delivery MAY be deferred.


7.  The Measurement Protocol  (inherited verbatim)

   RFC-001 §7 survives verbatim.  The Calorimeter (or any successor
   measurement component) MUST attach to a bus by subscribing to
   event types; MUST NOT hold a reference to any brain component;
   MUST NOT call any method on any brain component; MUST NOT
   influence the energy landscape or phase classification.

   Any component that exposes get_heat_flux(cluster_id) -> float
   MAY be used by the ThermodynamicGovernor for quench decisions.
   This is the only permitted read-path from measurement back to
   governance, and it MUST go through the Governor.

   Note.  Under this RFC, heat flux is one of several diagnostic
   readings; others (gamma_A distributions, cross_dissipation
   matrices, FDR profiles) may be emitted on the bus as future
   event types or consumed by subscribing measurement components.
   The read-only discipline is unchanged.


8.  Interaction Rules  (inherited verbatim)

   RFC-001 §8 survives verbatim.  The five rules (engines within a
   cluster share a substrate and bus; clusters within a network
   share a bus but not a substrate; signal routing is the only
   permitted cross-cluster interaction; the Governor may read heat
   flux and may call shed_load/quench but not modify the landscape
   directly; no brain component may call any measurement method
   except through the Governor) are unchanged.


9.  Amendments  (updated dispositions)

   The following dispositions supersede those stated in RFC-001 §9
   and in RFC-001 Amendment Set A.  RFC-001 Amendment Set A remains
   in force for all amendments not explicitly updated here.

   9.1  AMEND-001: Temporal Frustration Decay  (OBSOLETE)

      Status: OBSOLETE.  Superseded by paper §7.8 ("Emergent
      Forgetting").

      Rationale:  Under the trail-vector formulation of paper §7.2,
      gamma_ij is the geometric projection of trail vectors; when a
      constraint is unreinforced its trail vector d_A(t) shrinks,
      and the associated gamma_ij falls below the noise floor
      without any scheduled decay rule.  The RFC-001 proposal of an
      explicit decay schedule
      epsilon_ij(t) = epsilon_ij(0) * exp(-t/tau_ij) is redundant
      scaffolding over the physics.

      Implementation guidance:  Implementations SHOULD NOT include
      an explicit decay scheduler.  The tau_ij parameter is absorbed
      into the engine's correlation_window (§4.2): a single
      substrate-level knob replaces the per-pair schedule.  gamma_ij
      measurements over a sliding window produce decay for free as
      old contributions roll out.

      The RFC-001 interface additions Substrate.update_frustration,
      Substrate.decay_step, and Engine.last_ping are NOT part of
      this RFC and SHOULD NOT be implemented in conforming brains.

      Interaction with AMEND-004:  The RFC-001 note that
      "ObservationSocket is the natural source of observation pings"
      is superseded.  Under this RFC, an incoming observation
      re-enters the correlation window naturally via register or
      update_lambda; no ping mechanism is required.

   9.2  AMEND-002: Commit-Driven Inhibitory Routing
                                          (PROPOSED, cleaned up)

      Status: PROPOSED.  Carried forward from RFC-001 §9.2 with
      notation cleanup.

      Summary (revised):  On PhaseTransitionEvent(to_phase=c) from
      cluster A, adjust the A-B gamma_ij estimate for each cluster
      B by reweighting the correlation-window evidence:

         Co-commit (B in phase c during A's commit window):
            effective gamma_ij for (A,B) is rescaled by (1 - eta)
            -- compatible channel, cross-dissipation attenuated.

         Co-conflict (B in phase k during A's commit window):
            effective gamma_ij for (A,B) is rescaled by (1 + eta)
            -- inhibitory, cross-dissipation amplified.

      Where eta is a small learning rate.  The rule structure of
      RFC-001 §9.2 is preserved; the quantity adjusted is
      gamma_ij (inverse time) rather than epsilon_ij (energy).

      Risk:  Runaway amplification in persistently-conflicting
      cluster pairs.  Requires a ceiling on the effective gamma_ij
      (gamma_ij_max) to prevent full decorrelation of the routing
      matrix.

      Required interface changes:
         Network.update_compatibility(src_id, tgt_id, delta_gamma)
         Network.commit_history    -- ring buffer of recent commits
         Bus subscription:  Network subscribes to
                            PhaseTransitionEvent

   9.3  AMEND-003: Lateral Maintenance Field
                                          (PROPOSED, derived)

      Status: PROPOSED.  Carried forward from RFC-001 §9.3 with the
      coupling weight derived from the new framework rather than
      inserted as an ansatz.

      Summary:  Replace the per-engine maintenance EMA with a
      shared lateral maintenance field across engines in a cluster:

         F_maint(i) = sum_j  w_ij * (v_j - v_i) *
                              (1 - barrier_strength_j)

      where barrier_strength_j = |gamma_j| / gamma_A_star (§3.4)
      and w_ij is derived from the correlation structure.  RFC-001
      §9.3 proposed w_ij = exp(-epsilon_ij / k_BT) as a Boltzmann
      weight.  Under the dynamical framework the natural form is

         w_ij = exp( - |gamma_ij| * tau_window )

      where tau_window is the integration time of the engine's
      correlation window.  The window-product form arises directly
      from the joint-observable correlation spectrum: pairs with
      large |gamma_ij| over the window are destructively
      interfering and SHOULD couple weakly; pairs with small
      |gamma_ij| are compatible and SHOULD couple strongly.

      Interaction with the correlation window:  When gamma_ij is
      re-measured on a new window, w_ij updates automatically.
      There is no separate learning rule required; the coupling
      learns from the measurement.

      Required interface changes:
         MaintenanceField becomes cluster-scoped.
         Engine.step() receives lateral_force as additional input.
         Cluster.diffuse() computes lateral forces before stepping
                           engines.

   9.4  AMEND-004: ObservationSocket  (RATIFIED, unchanged)

      Status: RATIFIED.  Carried forward from RFC-001 Amendment
      Set A.2 verbatim.  Framework-agnostic; no interaction with
      the RFC-004 changes beyond the Observation Protocol note
      in §5 above.


   9.5  Preservation of RFC-001 Amendment Set A.1

      Each of the four Session 2 ratifications is preserved with a
      compatibility note for this framework.

      A.1.1  JAXSubstrate  (RATIFIED, compatibility note added)

         gradient(v) and hessian(v) retain their RFC-001 signatures
         and remain JIT-able via jax.grad and jax.hessian.

         The new observable methods of §4.1 (autocorrelation,
         survival_margin, cross_dissipation, fdr_profile) are NOT
         naturally JIT-able: they operate on time-series trajectories
         rather than single configurations, and their FFT and
         paired-noise internals are library-bound.  JAX acceleration
         is relevant to the Langevin inner step (which uses
         gradient), not to the observable extraction.  Observable
         methods SHOULD be implemented in vanilla NumPy / SciPy FFT.

         Version counter, fallback, and traceability invariants of
         RFC-001 A.1.1 are unchanged.

      A.1.2  AutoCluster  (RATIFIED, re-tuning note)

         The self-regulation rules of RFC-001 A.1.2 reference
         dominant_phase, which is now a window-resolved computation
         (§4.3).  The rule structure (r: do nothing; s with
         n_s < separation_bound: spawn; k: shed 30%) is preserved;
         thresholds and window lengths will require per-substrate
         calibration under the dynamical classifier (§3.1).

         The known issue of RFC-001 A.1.2 (population rebalancing
         when separation_bound collapses after shedding) is
         carried forward as DEVIATE-003.  AMEND-005 remains a
         plausible future amendment for population rebalancing;
         RFC-004 does not introduce it.

      A.1.3  LLMConstraintEncoder  (RATIFIED, unchanged)

         Framework-agnostic.  Survives unchanged.  DEVIATE-001
         (fallback active without ANTHROPIC_API_KEY) is carried
         forward.

      A.1.4  Scale Validation (Empirical)  (DEFERRED)

         Status: DEFERRED pending re-run under the flux-budget
         framework.

         The RFC-001 A.1.4 empirical result (worst N_active / N_max
         = 0.4868, PASS at 1.15 threshold) remains valid under the
         energy-budget framework in which it was measured.  A
         parallel validation under the flux-budget framework of
         §3.3 of this RFC is required before the Separation
         Theorem can be said to be empirically confirmed in the
         dynamical formulation.  This is deferred to a future
         benchmark cycle.  Task A's Separation Theorem figure
         (mpc_separation.png) is a low-N preliminary; the flux-
         based at-scale rerun is the full re-validation.


10.  What This Protocol Deliberately Excludes

   RFC-001 §10 is inherited verbatim.  The following are
   implementation details and are NOT specified by this protocol:

   - The geometry of the configuration space X (R^n, binary,
     graph, etc.)
   - The specific form of constraint functions
   - The integration method (Euler-Maruyama, Symplectic,
     Runge-Kutta)
   - The learning rule for lambda (stiffness adaptation)
   - The encoder that converts observations to constraint
     functions
   - The decoder that converts committed positions to actions
   - Whether the substrate uses exact or approximate gradients
   - Training procedures, if any

   Additional exclusions specific to this RFC:

   - The specific correlation-time cutoff threshold used in
     autocorrelation tail truncation (§4.1) is implementation-
     defined.
   - The specific numeric calibration of GAMMA_A_RESET_BAND,
     TAU_CONFLICT_FLOOR, and GAMMA_IJ_K_FLOOR in §3.1 is
     substrate-dependent and MUST NOT be cross-implementation
     hard-coded.
   - Whether a substrate supports Profile M or Profile G is an
     implementation decision.  Neither is required; at least one
     MUST be declared.

   These are the responsibility of the implementation, not the
   protocol.


11.  Reference Implementation

   The reference implementations are:

      mpc_engine_rfc001.py   (Session 1, 14 April 2026)
      mpc_session2.py        (Session 2, 16 April 2026)

         Conformant to RFC-001 with deviations DEVIATE-001 through
         DEVIATE-003 as documented in RFC-001 Amendment Set A §11.
         Valid under the energy-budget framework and NOT obsoleted
         by this RFC; their port to the dynamical framework is
         DEVIATE-004, below.

      mpc_lattice.py         (Task A, April 2026)
      physics_primitives.py  (Task A)

         The Profile M validation rig.  Exercises the four
         scenarios (committed, suspended, conflict, reset) on an
         overdamped Langevin substrate and validates the §3.1
         classifier, the flux-budget formulation of §3.3, and the
         scalar per-regime FDR signature of paper §7.7.  Four
         diagnostic figures (mpc_trajectories.png, mpc_fdr_atlas.png,
         mpc_separation.png, mpc_hessian_probe.png) accompany the rig.

         mpc_lattice.py is a validation harness, not a conforming
         brain: it does not expose the cluster or network interfaces
         of §§4.3-4.4 and does not emit events on a bus.  A
         conforming RFC-004 brain is a port of mpc_session2.py
         adopting the observable methods of §4.1 and the
         method-form phase() and fdr_profile of §4.2.

   Planned port:

      mpc_brain_rfc004.py    (not delivered by this RFC)

         MUST declare a substrate profile (§4.1) and MUST emit
         MeasurementUnresolvedEvent (§6) per §4.3.

   Deviation tracking:

      DEVIATE-001  LLM fallback active without ANTHROPIC_API_KEY.
                   (RFC-001 A.1.3.  Carried forward.)
      DEVIATE-002  Calorimeter not fully separated from brain
                   classes.  (RFC-001 §11.  Carried forward.)
      DEVIATE-003  AutoCluster does not rebalance population when
                   separation_bound() collapses after constraint
                   shedding.  (RFC-001 A.1.2.  Carried forward.)
      DEVIATE-004  Production reference (mpc_engine_rfc001.py +
                   mpc_session2.py) not yet ported to the §4
                   observable interface.  Tracked as the planned
                   port above.


12.  Related Artifacts and Directory Structure

   The following artifacts are reference material for RFC-004.
   They should be preserved alongside it but are not required for
   any currently active session:

      SESSION_A_STATE.md               -- Task A crystallized state
      mpc_lattice.py                   -- Profile M validation rig
      physics_primitives.py            -- validated observable primitives
      mpc_trajectories.png             -- phase portraits per scenario
      mpc_fdr_atlas.png                -- parametric FDR plots
      mpc_separation.png               -- Separation Theorem low-N
      mpc_hessian_probe.png            -- equilibrium-baseline diagnostic
      MPC_practical_notes.md           -- engineering companion to the paper
      v3_On_the_Dynamical_Limits...md  -- foundational paper (v3)

   These SHOULD be filed in docs/dynamical-track/ or equivalent,
   not in the root docs/ directory, to keep the active-RFC set
   visually distinct from the parked one until activation.


Authors' Note

   RFC-001 and the energy-budget reference implementation were
   developed by a hobbyist researcher with Claude (Anthropic),
   14-16 April 2026.  Task A (lattice validation) and this RFC
   (Task B) continued the same arrangement.  The paper (v3) is the
   formal reference for physics and is the authority when doubt
   persists.  SESSION_A_STATE.md remains authoritative on Task A
   evidence, except that its AMEND-001 disposition ("INTRINSIC") is
   superseded by §9.1 of this document ("OBSOLETE").