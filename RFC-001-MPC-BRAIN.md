MPC Working Group                                         Session Notes
Request for Comments: 001                                  April 2026
Category: Standards Track


        MPC-BRAIN: A Protocol for Metastable Propositional Calculus
                         Brain Architecture

Abstract

   This document defines MPC-BRAIN, a protocol governing the
   architecture of physically-grounded inference systems built on
   Metastable Propositional Calculus (MPC).  MPC-BRAIN specifies the
   interfaces, invariants, and interaction rules that all conforming
   brain components MUST satisfy.  It does not specify implementation;
   it specifies what any implementation must expose and preserve.

   The four-valued MPC state space {c, s, k, r} is treated as
   primitive.  It is a consequence of non-equilibrium thermodynamics,
   not a design choice, and is therefore not open to amendment.
   Everything else is.

Status of This Memo

   This document is the first in a series of RFCs governing the MPC
   brain architecture.  It defines the stable core.  Mechanisms
   proposed for future amendments are listed in Section 9.

   Comments and objections are invited in the spirit stated in the
   MPC paper: as tests, not obstacles.

Table of Contents

   1.  Introduction
   2.  Terminology
   3.  The Energy Invariant (Non-Amendable)
   4.  The Brain Protocol
       4.1  Substrate Interface
       4.2  Engine Interface
       4.3  Cluster Interface
       4.4  Network Interface
   5.  The Observation Protocol
   6.  The Event Protocol
   7.  The Measurement Protocol
   8.  Interaction Rules
   9.  Proposed Amendments
       9.1  AMEND-001: Temporal Frustration Decay
       9.2  AMEND-002: Commit-Driven Inhibitory Routing
       9.3  AMEND-003: Lateral Maintenance Field
   10. What This Protocol Deliberately Excludes
   11. Reference Implementation


1.  Introduction

   MPC-BRAIN exists because the brain and the calorimeter are on
   separate development paths, and separate development paths require
   a shared contract.

   The contract has two hard constraints:

   (a) The energy invariant (Section 3) is thermodynamic and cannot
       be relaxed without abandoning MPC entirely.

   (b) Everything else — topology, routing, decay timescales, learning
       rules on the frustration graph — is implementation and is
       subject to amendment.

   The protocol is intentionally minimal.  It specifies interfaces and
   invariants.  It does not specify algorithms, learning rules, or
   substrate geometry.


2.  Terminology

   The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
   "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in
   this document are to be interpreted as described in RFC 2119.

   Phase
      One of {c, s, k, r} as defined in the MPC paper Section 3.
      Committed (c), Suspended (s), Conflict (k), Reset (r).

   Substrate
      A component that maintains a joint energy landscape over a
      shared configuration space X and classifies topology from it.

   Engine
      A component that evolves a position v(t) through that landscape
      via a stochastic dynamical process.

   Cluster
      A colony of engines sharing a local energy budget E*.

   Network
      A graph of clusters with a shared event bus.

   Frustration
      The pairwise joint energy ε_ij between two constraints,
      measured in units of k_BT.  Represents the energetic cost of
      maintaining both constraints simultaneously.

   Bus
      A publish-subscribe event channel.  Brain components emit events
      onto it.  Measurement components subscribe to it.  The bus is
      the only connection between them.


3.  The Energy Invariant  (Non-Amendable)

   This section defines the invariant that all conforming
   implementations MUST preserve.  It is not subject to amendment.

   3.1  Phase classification

      Given a configuration v and a substrate with thresholds E_c < E_s
      (both substrate-dependent, both in units of k_BT):

         E(v) < E_c  AND  min eigenvalue of H(v) > 0  =>  phase = c
         E(v) > E_s  OR   min eigenvalue of H(v) < 0  =>  phase = k
         no constraints registered                     =>  phase = r
         otherwise                                     =>  phase = s

      Implementations MUST NOT classify phase by any other means.

   3.2  Landauer bound

      Any transition to phase r MUST be associated with a minimum
      energetic cost of k_BT * ln(2) per bit of information erased.
      This cost MUST be emitted as a LandauerEvent on the bus.
      It MUST NOT be silently discarded.

   3.3  Budget enforcement

      An engine MUST NOT take a step that would place E(v) above E*.
      If the proposed step would do so, the engine MUST instead
      trigger a reset transition and emit a BudgetResetEvent.

   3.4  Maintenance cost

      An engine in phase s MUST exert a non-zero maintenance force
      resisting collapse toward c or k.  The magnitude of this force
      MUST be proportional to (1 - barrier_strength), where
      barrier_strength is in [0, 1].

   These four rules are the physical content of MPC.  They are
   consequences of non-equilibrium thermodynamics applied to inference.
   Amendments that relax any of them are out of scope for this protocol
   and would constitute a different framework.


4.  The Brain Protocol

   4.1  Substrate Interface

      A conforming Substrate MUST expose:

         energy(v)            -> float
            Total constraint energy at configuration v, in units of k_BT.

         gradient(v)          -> vector[n]
            First derivative of energy with respect to v.

         hessian(v)           -> matrix[n,n]
            Second derivative of energy with respect to v.
            MUST be symmetric.

         classify(v)          -> Phase
            Phase classification per Section 3.1.

         register(id, fn, λ)  -> Handle
            Register a constraint function fn: R^n -> R+ with
            stiffness λ.  Returns an opaque handle.

         update_λ(handle, λ)
            Modify stiffness of a registered constraint.
            This is the primary control parameter for budget regulation.

         deregister(handle)
            Remove a constraint.  MUST NOT emit any event directly;
            the calling layer is responsible for emitting LandauerEvent.

         frustration(v)       -> dict[(id,id), float]
            Pairwise joint energies for all registered constraint pairs.

      A conforming Substrate MUST NOT hold a reference to any bus,
      calorimeter, or measurement component.

   4.2  Engine Interface

      A conforming Engine MUST expose:

         step(external_force) -> vector[n]
            Advance v(t) by one integration step.
            MUST enforce the budget invariant (Section 3.3).
            MUST apply the maintenance invariant (Section 3.4).
            MUST emit PhaseTransitionEvent when phase changes.
            MUST emit BudgetResetEvent when reset is triggered.

         run(n_steps)         -> trajectory[n_steps, dim]
            Call step() n_steps times.  Returns positions.

         phase                -> Phase
            Current phase of v(t).

         detect_insight()     -> bool
            Returns True if a sustained s -> c energy drop is detected
            in the recent trajectory.  Definition of "sustained" and
            "recent" is implementation-defined, but MUST be documented.

         v                    -> vector[n]
            Current position.  MAY be read; MUST NOT be written
            externally except via step().

         attention_scarcity   -> float  [0, 1]
            The effective temperature T in the Langevin dynamics.
            MAY be set externally.  0 = focused, 1 = maximally distracted.

      An Engine MUST hold a reference to exactly one Substrate and
      exactly one Bus.  It MUST NOT hold a reference to a Calorimeter.

   4.3  Cluster Interface

      A conforming Cluster MUST expose:

         load(constraints)
            Register a set of constraint functions into the substrate.

         diffuse(n_steps)
            Advance all engines by n_steps.

         separation_bound()   -> float
            Compute N_max per Theorem 6.1:
               sqrt(2 * E* / (α * ε_min * d_avg))
            Using the current frustration graph.

         enforce_separation()
            If the count of s-state engines exceeds separation_bound(),
            reset the weakest constraints until the bound is satisfied.
            Each reset MUST cause a LandauerEvent on the bus.

         dominant_phase       -> Phase
            The most frequent phase among engines over the recent window.

         extract_commitment() -> vector[n] | None
            If any engine is in phase c, return its position.
            Otherwise return None.

         shed_load(factor)
            Reset the weakest (factor * 100)% of registered constraints.

      A Cluster MUST hold a reference to exactly one Substrate and
      exactly one Bus.  Engines within a Cluster MUST share the same
      Substrate and the same Bus.

   4.4  Network Interface

      A conforming Network MUST expose:

         add_cluster(id, ...)  -> Cluster

         route(src_id, tgt_id, signal)
            Compute mean frustration between src and tgt clusters.
            If frustration < compat_threshold: call tgt.integrate(signal).
            If frustration >= compat_threshold: call tgt.inject_conflict(signal).

         step()
            Advance all clusters by one step.
            Run governance checks.

         bus                  -> Bus
            The shared event bus.  Read-only externally.

      A Network MUST NOT create or hold a Calorimeter.  Measurement
      components attach to the Network's bus externally.


5.  The Observation Protocol

   Observations are converted to constraint functions before entering
   the brain.  This conversion is the embedding, and it is physical:
   each observation element becomes a potential over configuration space.

   A conforming observation encoder MUST:

   - Produce constraint functions fn: R^n -> R+ for each proposition.
   - Guarantee fn(v) = 0 at the satisfaction point.
   - Guarantee fn(v) > 0 everywhere else.
   - Produce stiffness values λ in units of k_BT.

   The encoder MUST NOT produce constraint functions that violate
   the shared embedding assumption (MPC paper Section 2): all
   constraints for a given cluster MUST be defined over the same
   configuration space X.

   Observation strength (how strongly reality pins a constraint) is
   expressed through λ, not through the shape of fn.  This is the
   handle that temporal decay (AMEND-001) will modulate.


6.  The Event Protocol

   All events emitted by brain components onto the bus MUST conform
   to the following types.  No other event types are defined by this
   RFC; future events MUST be introduced by amendment.

   PhaseTransitionEvent:
      cluster_id   : str
      from_phase   : Phase
      to_phase     : Phase
      position     : vector[n]
      timestamp    : float

   LandauerEvent:
      cluster_id   : str
      info_content : float        # bits erased, > 0
      kT           : float        # thermal energy scale

   BudgetResetEvent:
      cluster_id   : str
      position     : vector[n]
      timestamp    : float
      info_cost    : float        # always 1.0 in current implementation

   Implementations MUST NOT emit events synchronously in a way that
   blocks the integration step.  Event delivery MAY be deferred.


7.  The Measurement Protocol

   A conforming measurement component (Calorimeter or any successor):

   MUST attach to a bus by subscribing to event types.
   MUST NOT hold a reference to any brain component.
   MUST NOT call any method on any brain component.
   MUST NOT influence the energy landscape or phase classification.

   The Measurement Protocol is therefore a strict read-only interface.
   The calorimeter observes.  It does not participate.

   Any component that exposes get_heat_flux(cluster_id) -> float
   MAY be used by the ThermodynamicGovernor for quench decisions.
   This is the only permitted read-path from measurement back to
   governance, and it MUST go through the Governor, never directly
   from a brain component to a calorimeter.


8.  Interaction Rules

   8.1  Engines within a cluster share a substrate and a bus.
        They MAY observe each other's positions but MUST NOT
        write to each other's positions directly.

   8.2  Clusters within a network share a bus but NOT a substrate.
        Each cluster has its own independent energy landscape.

   8.3  Signal routing (Section 4.4) is the only permitted
        cross-cluster interaction in this RFC.  All proposed
        lateral mechanisms (AMEND-003) MUST operate through
        the routing interface, not by direct substrate coupling.

   8.4  The Governor MAY read heat flux from a measurement component
        and MAY call cluster.shed_load() or engine quench.
        It MUST NOT modify the energy landscape directly.

   8.5  No brain component MAY call any measurement component method
        other than those exposed through the Network interface
        (Section 4.4) via the Governor.


9.  Proposed Amendments

   The following amendments are proposed for the next RFC.  They are
   documented here to record design intent.  They are NOT part of
   this standard.

   9.1  AMEND-001: Temporal Frustration Decay

      Status: PROPOSED

      Summary:
         Replace static ε_ij with time-decaying frustrations:

            ε_ij(t) = ε_ij(0) * exp(-t / τ_ij) + α_obs * δ(t_ping)

         Frustrations not re-confirmed by observation decay toward zero.
         Decayed edges fall out of the interaction graph, reducing d_avg,
         loosening the Separation Theorem bound, and allowing the system
         to hold more hypotheses without hitting the budget wall.

      Decay timescale:
         τ_ij SHOULD be proportional to the stiffness λ of the
         softer of the two constraints.  High-λ (committed) constraints
         decay slowly.  Low-λ (tentative) constraints decay fast.

      Ping sources:
         (a) Observation ping: full strength α_obs.  Resets timer.
         (b) Commit ping: dampened strength α_commit * decay_factor^n,
             where n is the number of consecutive self-pings without
             an observation ping.  Prevents self-sustaining hallucination.

      Required interface changes:
         Substrate.update_frustration(i, j, new_ε)
         Substrate.decay_step(dt)    -- called once per engine step
         Engine.last_ping(i, j)      -- timestamp of last ping on edge

      Open question:
         Should τ_ij be a fixed parameter or itself learnable from
         commit history?

   9.2  AMEND-002: Commit-Driven Inhibitory Routing

      Status: PROPOSED

      Summary:
         The frustration graph doubles as the routing matrix.
         When a cluster commits, it updates ε toward neighbors:

            Co-commit  => decrease ε (compatible channel, clean signal)
            Co-conflict => increase ε (inhibitory, signal arrives as k)

         The routing matrix learns itself from commit history.
         Manual route specification is eliminated.

      Learning rule:
         On PhaseTransitionEvent(to_phase=c) from cluster A:
            For each cluster B that co-committed within window W:
               ε(A,B) *= (1 - η)       # increase compatibility
            For each cluster B in phase k during A's commit:
               ε(A,B) *= (1 + η)       # increase inhibition
         Where η is a small learning rate.

      Convergence property:
         Clusters that frequently co-commit converge toward low ε
         (strong compatible channel).  Clusters that frequently
         conflict converge toward high ε (strong inhibition).
         The network self-organizes its own routing topology.

      Required interface changes:
         Network.update_compatibility(src_id, tgt_id, delta_ε)
         Network.commit_history        -- ring buffer of recent commits
         Bus subscription: Network subscribes to PhaseTransitionEvent

      Risk:
         Runaway inhibition if two clusters are always in conflict.
         Requires ε ceiling (ε_max) to prevent complete disconnection.

   9.3  AMEND-003: Lateral Maintenance Field

      Status: PROPOSED

      Summary:
         Replace per-engine maintenance EMA with a shared lateral
         maintenance field across engines in a cluster:

            F_maint(i) = Σ_j  w_ij * (v_j - v_i) * (1 - barrier_j)

         where the sum is over neighboring s-state engines and w_ij
         is derived from the frustration graph (low ε = strong lateral
         coupling, high ε = weak or inhibitory coupling).

      Effect:
         Engines in suspension do not individually fight gravity.
         They hang together, pulled by their neighbors.  An engine
         drifting toward premature commitment is pulled back by the
         collective position.  This is collective working memory.

      Coupling weight:
         w_ij = exp(-ε_ij / k_BT)
         This is the Boltzmann weight of the inter-engine compatibility.
         It is computable from the existing frustration graph without
         new parameters.

      Required interface changes:
         MaintenanceField becomes cluster-scoped, not engine-scoped.
         Engine.step() receives lateral_force as additional input.
         Cluster.diffuse() computes lateral forces before stepping engines.

      Interaction with AMEND-001:
         If frustrations decay, lateral coupling weights also decay.
         Engines that are no longer constrained by the same observations
         naturally decouple.  This is correct behavior.


10.  What This Protocol Deliberately Excludes

   The following are implementation details and are NOT specified here:

   - The geometry of the configuration space X (R^n, binary, graph, etc.)
   - The specific form of constraint functions
   - The integration method (Euler-Maruyama, Symplectic, Runge-Kutta)
   - The learning rule for λ (stiffness adaptation)
   - The encoder that converts observations to constraint functions
   - The decoder that converts committed positions to actions
   - Whether the substrate uses exact or approximate gradients
   - Training procedures, if any

   These are the responsibility of the implementation, not the protocol.


11.  Reference Implementation

   The reference implementation is mpc_engine.py as of Session 1
   (14 April 2026).  It conforms to this RFC with the following
   known deviations:

   - The Calorimeter is not yet fully separated from brain classes.
     Tracked by the refactor instructions in REFACTOR_INSTRUCTIONS.md.

   - The frustration graph is static (AMEND-001 not yet implemented).

   - Routing is threshold-based with a fixed compat_threshold
     (AMEND-002 not yet implemented).

   - Maintenance is per-engine EMA (AMEND-003 not yet implemented).

   These deviations are the amendment backlog.  They do not invalidate
   the reference implementation; they define its upgrade path.


MPC Working Group                                         Session Notes
Request for Comments: 001 / Amendment Set A              April 2026
Category: Standards Track


        MPC-BRAIN RFC-001: Amendment Set A
        (Session 2 Baseline + AMEND-004 LLM Connector)


Status of This Document

   This document records amendments to RFC-001-MPC-BRAIN arising from
   Session 2 implementation (16 April 2026) and proposes one new
   amendment (AMEND-004) for implementation in Session 3.

   Amendments marked RATIFIED are in force in the reference implementation
   as of mpc_session2.py.  Amendments marked PROPOSED are not yet
   implemented.

   All amendments preserve the non-amendable invariants of RFC-001 §3.


────────────────────────────────────────────────────────────────────────
AMENDMENT SET A.1  ─  SESSION 2 RATIFICATIONS
────────────────────────────────────────────────────────────────────────

A.1.1  JAXSubstrate  (RATIFIED)

   Section affected: RFC-001 §4.1 (Substrate Interface), §11 (Reference
   Implementation)

   Change:

      Add JAXSubstrate as a conforming Substrate subclass that overrides
      gradient() and hessian() to use jax.grad / jax.hessian compiled
      via jax.jit.

   New invariants:

      (a) Version counter.  Calls to register(), deregister(), and
          update_lambda() each increment a substrate-internal version
          counter.  The compiled XLA function is invalidated and
          recompiled on the next gradient or hessian call when the
          version has advanced.  This ensures stiffness changes are
          never silently stale.

      (b) Fallback.  If JAX is unavailable or any constraint function
          raises a tracing exception, _jax_ok is set False permanently
          for that substrate instance.  All subsequent gradient/hessian
          calls fall through to the parent finite-difference
          implementation transparently.

      (c) Constraint functions MUST be JAX-traceable.  In practice this
          means: use np.sum(diff * diff), not float(np.sum(diff * diff)).
          np.sum is intercepted by JAX's numpy dispatch layer when the
          input is a traced array.

   Interface additions (JAXSubstrate only, not required by all Substrates):

      _jax_ok             : bool   -- False after any tracing failure
      _constraint_version : int    -- incremented on every register/
                                      deregister/update_lambda
      _compiled_version   : int    -- version at last successful compile

   Measured performance (CPU, no GPU):
      FD at dim=64:  ~400 s / 1000 steps (extrapolated, O(n^2))
      JAX at dim=64:   2.6 s / 1000 steps (actual, jax_ok=True)
      Extrapolated speedup: 156x.  GPU adds further hardware parallelism.

   Factory function:

      _make_jax_cluster(cluster_id, dim, local_budget, bus,
                        E_c, E_s, alpha)
         Creates an MPCCluster and replaces its substrate with a
         JAXSubstrate before any engines are added.  The OperatorAlgebra
         reference (ops.sub) is updated simultaneously.  This ordering
         is REQUIRED: the substrate must be replaced before the first
         engine is added.

   RFC-001 §11 update:
      The deviation "Whether the substrate uses exact or approximate
      gradients" is resolved.  JAXSubstrate provides exact gradients.
      Finite-difference fallback remains available.


A.1.2  AutoCluster  (RATIFIED)

   Section affected: RFC-001 §4.3 (Cluster Interface), §11

   Change:

      Add AutoCluster as a conforming Cluster subclass that manages its
      own engine population without external governance.

   Constructor signature:

      AutoCluster(dim, E_star, max_engines, bus, E_c=0.5, E_s=2.0)

   Self-regulation rules (applied once per step(), after diffuse()):

      dominant_phase == r:
         Do nothing.

      dominant_phase == s  AND  count_s_state() < separation_bound():
         Spawn one engine (up to max_engines).  New engine initialized
         at v ~ N(0, 0.05*I).

      dominant_phase == k:
         Call shed_load(0.3).  Removes the weakest 30% of constraints.

   Culling:

      An engine in phase r for CULL_THRESHOLD = 50 consecutive steps
      is removed.  At least one engine is always retained.

   New public methods:

      step()
         diffuse(1) → _update_r_streaks() → _cull_stale_engines()
         → _regulate().

      population_report() -> dict
         Returns: {n_engines, n_committed, n_suspended, n_conflict,
                   n_reset, separation_bound}.

   RFC-001 §4.3 compliance:
      step() calls only RFC-001 interface methods: diffuse, add_engine,
      shed_load, dominant_phase, count_s_state, separation_bound.
      No Calorimeter reference.  Holds exactly one Substrate and one Bus
      (both inherited from MPCCluster).

   Known issue (deferred to RFC-002):

      When separation_bound() returns a very large value (near-zero
      frustration after constraint shedding), AutoCluster spawns to
      max_engines in a single burst.  When new constraints are loaded and
      separation_bound() collapses to a small value, the engine count
      exceeds the new bound.  Population rebalancing (culling excess
      s-state engines, not just stale r-state engines) is NOT currently
      implemented.  This is deferred to AMEND-005 (RFC-002).


A.1.3  LLMConstraintEncoder  (RATIFIED, with DEVIATE-001)

   Section affected: RFC-001 §5 (Observation Protocol), §11

   Change:

      Add LLMConstraintEncoder as a conforming observation encoder that
      translates natural-language propositions into constraint functions.

   Primary path (requires ANTHROPIC_KEY in environment):

      Calls claude-sonnet-4-6 with a system prompt requiring:
         def fn(v):  (uses only numpy, returns >= 0, equals 0 at one point)
      Response is executed in restricted namespace {np, __builtins__: {}}.
      Output is sanity-checked: fn(zeros) >= 0 MUST hold.
      Markdown fences are stripped before execution.

   Cache:

      Encoded functions are cached by proposition string.  Identical
      propositions within a session do not trigger additional API calls.

   RFC-001 §5 compliance:
      Produces fn: R^n -> R+ for each proposition.
      fn(v) >= 0 everywhere; fn(v) = 0 at exactly one point (quadratic).
      Stiffness λ expressed in units of k_BT, passed separately.
      Does NOT embed λ inside fn.

   DEVIATE-001  (active when ANTHROPIC_KEY is absent):

      Status: Known deviation, acceptable for development.

      When ANTHROPIC_KEY is not set, the encoder substitutes a
      deterministic fallback:
         - For the three hello-world propositions, uses analytically-
           designed quadratic centres (orthogonal subspaces for P1/P2,
           P3 biased toward P2).
         - For all other propositions, uses a word-hash bag-of-words
           quadratic centre.

      Limitation: the fallback does not generalise.  It produces correct
      results for the demo but cannot encode arbitrary propositions.

      Resolution: set ANTHROPIC_KEY in the environment.  See README.md.


A.1.4  Scale Validation (Empirical)  (RATIFIED)

   Section affected: RFC-001 §4.3, Theorem 6.1

   Empirical verification of the Thermodynamic Separation Theorem across
   N = 5…50 constraints (dim=16, E*=50, 10 engines, 200 steps/N,
   lam=0.05, sigma_c=0.3, E_c=0.3, E_s=3.0):

      Worst N_active / N_max = 0.4868 <= 1.15  →  PASS

   Observation: the theorem exhibits two regimes.

      N <= 30: genuine s-state engines, N_active/N_max in range 0.28–0.49.
      N >= 35: E_min > E_s; all engines enter k-state; N_active = 0.

   The k-state regime self-enforces the theorem before the budget
   constraint acts.  A tighter test (showing N_max as the binding
   constraint, not E_s) requires a multi-well substrate with disjoint
   hypothesis regions.  Deferred to AMEND-006 (RFC-002).

   Note on parameter choice:
      The naive parameterisation (lam=0.5, sigma=0.5) places E_min >> E_s
      and yields trivially zero N_active at all N.  The chosen parameters
      (lam=0.05, sigma=0.3) place E_min ≈ 0.56 between E_c and E_s,
      producing non-trivial s-state engines for a genuine empirical test.


────────────────────────────────────────────────────────────────────────
AMENDMENT SET A.2  ─  NEW PROPOSED AMENDMENT
────────────────────────────────────────────────────────────────────────

AMEND-004: ObservationSocket — Formal LLM Connector Interface

   Status: PROPOSED (target: Session 3)

   Motivation:

      LLMConstraintEncoder currently fuses two concerns:
         (a) Calling an external model (API transport, prompt engineering,
             retry logic, caching).
         (b) Converting model output to a constraint function (parsing,
             safe-eval, fallback heuristic).

      As the system grows to support multiple observation modalities
      (text, image, sensor stream, structured data), the transport layer
      must be separable from the encoding layer.  AMEND-004 introduces
      an ObservationSocket interface that decouples them.

   Interface specification:

      ObservationSocket is the single entry point for all external
      observations entering the MPC brain.  It is not a brain component
      and does not hold a Substrate or Bus reference.

      A conforming ObservationSocket MUST expose:

         observe(proposition: str, modality: str = "text",
                 strength: float = 1.0)
            -> ConstraintSpec

            Accept a raw observation (proposition text, image bytes,
            sensor reading, etc.) with an optional modality tag and a
            strength hint.

            Returns a ConstraintSpec:
               fn       : Callable[[np.ndarray], float]  -- constraint function
               lambda_  : float                          -- stiffness in k_BT
               label    : str                            -- proposition identifier
               modality : str                            -- source modality

         flush() -> List[ConstraintSpec]
            Return all pending ConstraintSpecs accumulated since the
            last flush(), then clear the buffer.  This is the pull
            interface; the cluster calls flush() once per step.

         connect(model_endpoint: str, **kwargs)
            Set or update the external model endpoint.
            For the Anthropic API: model_endpoint = "claude-sonnet-4-6",
            kwargs = {"api_key": os.environ["ANTHROPIC_KEY"]}.
            MUST NOT raise on missing key; MUST mark self._connected = False
            and fall back to the registered fallback encoder.

         register_fallback(modality: str,
                           encoder: Callable[[str, int], Callable])
            Register a fallback encoder for a given modality.
            Called when the primary model endpoint is unavailable.

      An ObservationSocket MUST NOT:
         - Hold a reference to a Substrate, Bus, or Engine.
         - Call any brain component method directly.
         - Block the cluster step() call (flush() MUST return immediately,
           even if the model is slow; use async buffering or a local cache).

   Canonical implementation (Session 3 target):

      AnthropicSocket(ObservationSocket)
         - Primary:  calls claude-sonnet-4-6 via ANTHROPIC_KEY.
         - Fallback: the existing LLMConstraintEncoder word-hash heuristic.
         - Buffer:   a deque of pending ConstraintSpecs for flush().
         - Cache:    keyed by (proposition, modality, strength).
         - Retry:    exponential back-off on 5xx, max 3 attempts.

   Integration with AutoCluster:

      AutoCluster gains an optional socket: ObservationSocket = None.

      When socket is set, step() calls socket.flush() before diffuse()
      and passes any new ConstraintSpecs to cluster.load().

      This is a one-line change to step():
         specs = self._socket.flush() if self._socket else []
         if specs:
             self.load({s.label: s.fn for s in specs},
                       stiffnesses={s.label: s.lambda_ for s in specs})

      No other changes to the Cluster interface are required.

   Interaction with AMEND-001 (Temporal Frustration Decay):

      ObservationSocket is the natural source of "observation pings"
      (AMEND-001 §ping sources).  When flush() delivers a ConstraintSpec
      for an already-registered constraint, the substrate SHOULD call
      update_frustration(i, j, new_ε) to re-stamp the decay clock.
      The socket does not call this directly; it emits the ConstraintSpec
      and the cluster dispatches.

   Why not a push interface?

      A push interface (socket calls cluster.load() directly) would
      introduce a dependency from the socket into the brain component.
      flush() keeps the dependency arrow pointing inward: the cluster
      owns its observation cycle.


────────────────────────────────────────────────────────────────────────
SECTION 11 UPDATE  ─  REFERENCE IMPLEMENTATION STATUS
────────────────────────────────────────────────────────────────────────

   Replace RFC-001 §11 with the following:

   The reference implementation consists of two files:

      mpc_engine_rfc001.py   (Session 1, 14 April 2026)
         Substrate, MetastableEngine, MPCCluster, EventBus, Calorimeter.

      mpc_session2.py        (Session 2, 16 April 2026)
         JAXSubstrate, AutoCluster, LLMConstraintEncoder,
         _make_jax_cluster, hello_world.

   Known deviations from RFC-001 as of Session 2:

      DEVIATE-001  LLM fallback active without ANTHROPIC_KEY.
                   (See A.1.3 above.)

      DEVIATE-002  Calorimeter not fully separated from brain classes.
                   (Carried forward from Session 1.  Tracked.)

      DEVIATE-003  AutoCluster does not rebalance population when
                   separation_bound() collapses after constraint shedding.
                   (See A.1.2, "Known issue".)

   Pending amendments (not yet implemented):

      AMEND-001    Temporal Frustration Decay            (Session 3)
      AMEND-002    Commit-Driven Inhibitory Routing       (Session 4)
      AMEND-003    Lateral Maintenance Field              (Session 3)
      AMEND-004    ObservationSocket LLM Connector        (Session 3)

   Authors' Note update:

      Sessions 1–2 were developed collaboratively between a hobbyist
      researcher and Claude (Anthropic), 14–16 April 2026.
      This amendment document was produced at the close of Session 2.


────────────────────────────────────────────────────────────────────────
END OF AMENDMENT SET A
────────────────────────────────────────────────────────────────────────

