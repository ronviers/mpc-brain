# On the Dynamical Limits of Boolean Algebra as a Theory of Inference
## Metastable Propositional Calculus as a Theory of Structural Survival under Dissipation

**Formal Framework · Resource-Bounded Inference · Non-Equilibrium Dynamics · Trail-Induced Advection**

*Version 3. The Trajectory Space Formulation (§7) is rebuilt on generalized Langevin dynamics with trail vectors, admitting an MSRJD path-integral representation and a tensorial Fluctuation–Dissipation signature. The formal apparatus of earlier versions — Theorem 6.1 with proof sketch, the falsifiability conditions of §5, the worked binary example of §8 — is preserved.*

---

### Core Contribution

MPC formalizes the distinction between what can be true together and what can be *kept coherent* together under a finite rate of negentropic supply. This distinction is absent from Boolean logic by design; MPC argues it is absent from Boolean logic by physical necessity.

---

### Abstract

Boolean algebra, the formal system underlying classical computation, rests on an implicit dynamical assumption: that propositions, once asserted, persist costlessly against the decorrelating action of their environment. This assumption holds only in the limit of systems with unbounded negentropic supply. Boolean logic remains formally closed under its own axioms; what fails under finite dissipative budgets is the physical instantiation of its unconstrained compositional semantics. When that instantiation constraint is made explicit, Boolean logic is no longer an adequate model of physically realizable inference.

We introduce **Metastable Propositional Calculus (MPC)**, a resource-sensitive, four-valued logical system grounded in the dynamics of active matter. Rather than postulating truth values, MPC derives logical semantics from the survival of constraint structures — conceptualized geometrically as history-induced *trail vectors* in trajectory space — against a dissipative bath, with timescales defined relative to the environmental decorrelation rate. We prove a **Survival Separation Theorem** establishing that families of classically consistent inferences cannot be jointly maintained under a finite negentropic flux, and we identify a regime-specific structure of the Fluctuation–Dissipation Ratio — both in its scalar per-regime signature and in its tensorial anisotropy along memory axes — as the primary empirical signature of the framework.

---

## §1 — The Equilibrium Assumption and Its Dynamical Failure

Boolean algebra models a proposition as a static object, indifferent to the passage of time. This is a valid and useful abstraction under idealized conditions. To be precise: Boolean logic is not broken. It remains formally closed, consistent, and complete within its own axioms. What we claim is more specific: the unconstrained compositional semantics of Boolean logic — its assumption that any consistent set of propositions can be simultaneously maintained without dynamical cost — is not preserved when propositions are physically instantiated against a dissipative environment.

Physically realized inference systems violate three of Boolean logic's tacit dynamical assumptions in ways that are structural, not marginal.

#### Failure I — Sustained structure requires negentropic flux

A proposition that has been asserted must be actively maintained against the decorrelating action of the bath. The minimum negentropic flux required to keep constraint $A$ coherent is lower-bounded by:

$$\Phi_A \gtrsim \gamma_A \quad \text{where} \quad \gamma_A \equiv \tau_A^{-1} - \tau_{env}^{-1}$$

A system with finite flux capacity $\Phi^*$ cannot maintain this cost indefinitely. $\tau_A$ is the integral relaxation time of the constraint's autocorrelation function, and $\tau_{env}$ is the decay time of the unconstrained bath. The proposition is viable exactly when $\gamma_A < 0$: the structure regenerates faster than the bath dissolves it.

#### Failure II — Erasure is not free, and its cost is history-dependent

Boolean negation treats $\neg p$ as a syntactically costless operation. Erasure of a structure that participates in the system's correlation network requires breaking its couplings. The minimum work required to delete a proposition $H$ is:

$$W_{\text{delete}}(H) \geq k_B T \ln 2 \cdot \big(1 + I(H; \{D_j\})\big)$$

where $I(H; \{D_j\})$ is the mutual information between $H$ and its dependent structures. The floor is the Landauer bound; the correction is the cost of dismantling the correlations the proposition has accumulated. Deletion is a dynamical event whose cost grows with historical embedding.

#### Failure III — Contradiction is a destructive-interference regime, not a logical halt

In systems with irreconcilable constraints, competing structures do not produce a crash or an undefined value. They produce *destructive cross-dissipation*: coupled constraints accelerate each other's decay, driving the joint structure into a regime where the cross-correlation is negative and the composite system acts as an entropy sink. Boolean logic has no representation for this state. MPC introduces one.

---

## §2 — Timescales, Trail Vectors, and the Empirical Substrate

Let $\mathcal{X}$ denote a configuration space and $\gamma \in \mathcal{X}^*$ a trajectory — a history of configurations indexed by time. Each proposition $A$ is operationalized through an observable $V_A$ that projects the constraint onto the trajectory, and through a causal memory kernel $K_A(t)$ that weighs past configurations in determining the constraint's current instantiation.

### The Two Fundamental Timescales

**Constraint timescale.** The integral relaxation time of the constraint's autocorrelation:

$$\tau_A = \int_0^\infty C_A(t)\, dt, \qquad C_A(t) = \langle V_A(x(t)) V_A(x(0)) \rangle$$

We assume the decay is exponentially bounded or stretched-exponential, so that $\tau_A$ is finite at the observation scale.

**Environmental timescale.** The decay time of the background correlation spectrum, measured by evaluating the same autocorrelation function in the unconstrained bath ($V_A \equiv 0$):

$$\tau_{env} = \int_0^\infty C_{env}(t)\, dt$$

### The Survival Margin

The survival margin of proposition $A$ against its environment is:

$$\gamma_A \equiv \tau_A^{-1} - \tau_{env}^{-1}$$

A proposition is *viable* when $\gamma_A < 0$ (it persists longer than the bath's decorrelation time). The magnitude of $\gamma_A$ quantifies its margin against dissipation. This definition replaces the energy-barrier formalism of static thermodynamics with quantities directly accessible via correlation spectroscopy.

### The Trail Vector

The memory kernel $K_A$ admits a useful geometric representation as a **trail vector** in the configuration space:

$$d_A(t) \equiv \int_{-\infty}^{t} K_A(t - s)\, \dot{x}(s)\, ds$$

The trail vector aggregates past motion into a direction and magnitude: its direction points from where the constraint has been — its crystallized history — toward where the system is now; its magnitude $\|d_A\|$ encodes the *memory tension*, or how strongly the past is pulling on the present. The trail vector is a low-dimensional projection of the full memory structure; different embeddings (exponential moving averages, kernel projections, latent-space trajectories) are equivalent up to coarse-graining. The correlation timescale $\tau_A$ emerges as the characteristic decay time of $\|d_A\|$ when the constraint is no longer reinforced.

### Cross-Dissipation

The joint behavior of constraints is not captured by their individual survival margins. We define cross-dissipation as the joint decay acceleration beyond the individual components:

$$\gamma_{ij} \equiv \tau_{i \land j}^{-1} - \max(\tau_i^{-1}, \tau_j^{-1})$$

When $\gamma_{ij} > 0$, coupling *accelerates* decay — the constraints destructively interfere. When $\gamma_{ij} < 0$, coupling stabilizes the joint structure. Geometrically (made precise in §7), positive $\gamma_{ij}$ corresponds to destructive shear between trail vectors, and negative $\gamma_{ij}$ to cooperative alignment. Cross-dissipation is the dynamical signature of logical interaction.

### Boundary Condition: Shared Trajectory Space

MPC assumes the propositions under consideration admit a joint embedding into a shared trajectory space $\mathcal{X}^*$ against a common bath with well-defined $\tau_{env}$. This is a nontrivial assumption. The boundary of MPC's applicability is the boundary at which a shared trajectory space and a common decorrelation scale can be coherently constructed. Acknowledging this boundary is not a weakness of the framework; it is the condition that makes it scientifically tractable.

---

## §3 — The Four Regimes of MPC

MPC is a four-valued logic in which the truth values $\mathcal{V} = \{c, s, k, r\}$ represent the canonical survival regimes of a constraint against its bath. The values are derived from the topology of the joint correlation spectrum, not postulated independently.

MPC truth values are **relational**. They are not intrinsic properties of a proposition but properties of the relationship between a proposition and the substrate realizing it. The same proposition may be committed ($c$) in a high-flux system and suspended ($s$) in a resource-constrained one.

### Table 1. The Four Regimes of MPC

| Sym | Name | Dynamical Signature | Description | Character |
|-----|------|--------------------|-------------|-----------|
| **c** | Committed | $\gamma_A \ll 0$, $\tau_A \gg \tau_{env}$, long stable $d_A$ | Autocatalytic stability. The constraint is self-reinforcing; perturbation recovery is exponential; the trail vector is persistent and dominant. | Low maintenance flux. High revision cost (deep memory kernel). FDR $X_\parallel \ll 1$. |
| **s** | Suspended | $\gamma_A \lesssim 0$, $\tau_A \sim \tau_{env}$, moderate $d_A$ replenished by flux | Dissipative maintenance. A Prigogine-type structure requiring active negentropy import. The trail persists only under continuous drive; autocorrelation decays as a stretched exponential. | Sustained maintenance flux $\Phi_A \gtrsim \gamma_A$. Intermediate, time-dependent FDR. |
| **k** | Conflict | $\gamma_{ij} > 0$ strongly; opposing trail projections | Destructive interference. Coupled trails apply geometric shear to one another; cross-correlation is negative; joint structure is an entropy sink. | Elevated sustained flux. Persists until resolving work dismantles the coupling. |
| **r** | Reset | $\gamma_A \approx 0$, $\tau_A \approx \tau_{env}$, $\|d_A\| \to 0$ | Equilibrated. The constraint has dissolved into the thermal bath; the trail has decayed; autocorrelation is delta-correlated at the observation scale. | No maintenance flux. $X = 1$ (FDT holds). Identity element of the algebra. |

*Thresholds defining the boundaries between regimes are substrate-dependent and must be measured, not stipulated.*

---

## §4 — Operator Algebra

The classical Boolean operators are replaced by dynamical operators induced by the survival structure of the joint correlation spectrum.

### Commitment (C) — replaces AND

$C(A, B)$ is determined by the survival margin of the joint structure:

$$C(A, B) = \begin{cases}
c & \text{if } \gamma_{A \land B} \ll 0 \\
s & \text{if } \gamma_{A \land B} \sim 0 \\
k & \text{if } \gamma_{AB} > 0 \text{ (destructive interference dominant)}
\end{cases}$$

Associative within each regime. Reduces to Boolean AND in the limit $\Phi^* \to \infty$, $\tau_{env} \to \infty$. Geometrically: when the trails $d_A$ and $d_B$ align, their joint potential deepens and $C(A,B) \to c$; when they are approximately orthogonal, neither reinforces the other and the joint state is suspended; when their projections oppose, coupling drives destructive interference.

### Suspension (S) — replaces OR

$S(A, B)$ returns the state corresponding to maintaining two viable substructures without collapse. The system pays continuous flux $\Phi \gtrsim \gamma_A + \gamma_B$ to hold both configurations coherent. Unlike Boolean OR, the cost is explicit and scales with how deeply the bath is trying to decorrelate each alternative.

### Conflict (K) — replaces XOR

$K(A, B) = k$ when cross-dissipation is destructive: $\gamma_{AB} > 0$. The conflict magnitude is quantifiable directly as $\gamma_{AB}$, enabling graded resolution strategies proportional to the rate of destructive interference.

### Reset (R) — replaces NOT

$R$ maps a structure to $r$ by severing its couplings and releasing it to the bath. The cost is the correlation-corrected Landauer bound:

$$W_R(H) \geq k_B T \ln 2 \cdot \big(1 + I(H; \{D_j\})\big)$$

$R(r) = r$: releasing an already-equilibrated state is free. The operator is a projection, not an involution — the formal statement of irreversibility within the MPC algebra.

### Table 2. Commitment Operator — Truth Table

| $C(A,B)$ | **c** | **s** | **k** | **r** |
|----------|-------|-------|-------|-------|
| **c** | c | c | k | c |
| **s** | c | s | k | s |
| **k** | k | k | k | k |
| **r** | c | s | k | r |

*The $k$-absorbing property reflects the physical fact that destructive cross-dissipation cannot be recovered by coupling to a stable or equilibrated partner: the entropy-sink character of the joint structure dominates.*

### Note on the Character of the Algebra

$S$ is not a pure function of its propositional arguments — its output depends on $\Phi^*$, the available negentropic flux, and on $\tau_{env}$, the environmental decorrelation timescale. This makes MPC a **state-dependent algebra** whose state is the substrate's dissipative regime. The parameters $(\Phi^*, \tau_{env})$ should be understood as implicit arguments to every operator, made explicit when substrate-specific predictions are required.

---

## §5 — Structural Interpretation and Falsifiable Cognitive Mappings

The following mappings apply MPC to cognitive phenomena. Each is offered as a **falsifiable structural hypothesis**. None is offered as a metaphor, and each requires the empirical premise that the human brain is adequately modeled by an MPC-structured dissipative system.

### Working Memory as Dissipative Maintenance

Maintaining an unresolved hypothesis — the $s$-state — requires continuous negentropic flux to sustain the constraint's autocorrelation against bath decorrelation.

**Falsifiability Condition:** Metabolic flux should scale as $\mathcal{O}(N \cdot d)$, where $N$ is the number of concurrent suspended hypotheses and $d$ is the average cross-coupling degree. Autocorrelation of working-memory-linked neural observables should exhibit stretched-exponential decay during the maintenance interval. If metabolic flux is independent of $d$, or scales superlinearly in $d$ for fixed $N$, or if decay profiles are purely exponential in the maintenance window, the mapping is disconfirmed.

### Cognitive Dissonance as Destructive Cross-Dissipation

Contradictory constraints produce a $k$-state in which coupled commitments accelerate each other's decay. The metabolic signature is sustained, not transient — the system is actively paying the ongoing cost of the entropy sink.

**Falsifiability Condition:** During maintained incompatible commitments, (i) the cross-correlation between neural correlates of the conflicting beliefs should be negative, (ii) the metabolic signature should scale with the cross-dissipation magnitude $\gamma_{ij}$, and (iii) the local Fluctuation–Dissipation Ratio should exhibit the $k$-regime signature — non-monotonic or negative response, distinguishable from the aging profile of an $s$-state and the depressed-stable profile of a $c$-state. A transient-only signature, absence of negative cross-correlation, or an FDR profile matching $s$- or $c$-regime behavior disconfirms the mapping.

### Belief Revision as Memory-Kernel Dismantling

A committed belief occupies a deep memory kernel (long $\tau_A$, large $\gamma_A$ magnitude, persistent $d_A$). Revision requires severing the kernel's couplings and paying the correlation-corrected erasure cost.

**Falsifiability Condition:** The time required to revise a belief should scale with proxies for its memory-kernel depth: prior exposure duration, rehearsal frequency, and the breadth of its coupling to other beliefs (measured via cross-correlation structure). Independence of revision timescale from these proxies disconfirms the kernel-depth model.

### Insight as Trail Alignment

Convergence from multiple suspended hypotheses to a single coherent $c$-state is not merely a drop in scalar energy; it is a structural phase transition in trajectory space. Prior to resolution the trail vectors of the competing hypotheses are misaligned — their projections onto one another produce destructive shear ($\gamma_{ij} > 0$), and the system pays a sustained dissipative penalty. An insight event occurs when a small perturbation — a disambiguating observation, a frame shift — causes previously conflicting trails to suddenly align. The destructive shear collapses, cooperative reinforcement ($\gamma_{ij} < 0$) takes over, and the trails pull each other forward, rapidly deepening the joint memory kernel into a stable commitment.

**Falsifiability Condition:** Three coincident signatures should accompany any true insight event: (i) a sudden, measurable spike in cosine similarity among the trail vectors of the previously-competing hypotheses; (ii) a sharp drop in total maintenance flux as the sustained $s$-state costs are released, followed by a lower steady-state cost for the unified $c$-structure; (iii) rapid stabilization of the Fluctuation–Dissipation Ratio to the $c$-regime value along the newly unified axis. An increase in sustained metabolic demand post-insight, or absence of the cosine-similarity spike, disconfirms the mapping.

### Axioms as Deepest Kernels

An axiom is a proposition whose memory kernel has become so deep that its survival margin $\gamma_A$ is effectively unbounded within the relevant subspace: the correlation timescale decouples from environmental perturbation, and the proposition functions as a fixed topological feature of the trajectory landscape. FDT violation for axiomatic structures is extreme ($X \to 0$ along the axiomatic axis).

---

## §6 — The Survival Separation Theorem

### Theorem 6.1

Let $\Gamma = \{H_1, \ldots, H_N\}$ be a classically consistent hypothesis set. Let the pairwise cross-dissipation between $H_i$ and $H_j$ be $\gamma_{ij} \geq 0$, and let $G = (V, E)$ be the interaction graph (with an edge wherever $\gamma_{ij} > 0$). Let $d_{avg}$ denote the average degree of $G$ and $\alpha \in (0,1]$ a substrate-dependent coupling factor. Then the maximum size of any dynamically realizable subset $\Gamma^* \subseteq \Gamma$ satisfies:

$$|\Gamma^*| \leq N_{max} = \mathcal{O}\!\left( \sqrt{\frac{2\Phi^*}{\alpha \gamma_{min} d_{avg}}} \right)$$

where $\gamma_{min} = \min_{(i,j)\in E} \gamma_{ij}$ is the minimum non-zero cross-dissipation, and $\Phi^*$ is the system's negentropic flux capacity.

#### Proof Sketch

The total negentropic flux required to maintain a constraint graph is the sum of individual decay offsets plus the cross-dissipation induced by coupling:

$$\Phi_{required} = \sum_{i \in V} \gamma_i + \alpha \sum_{(i,j) \in E} \gamma_{ij}$$

In the highly coupled regime characteristic of semantically rich hypothesis sets, edge-induced cross-dissipation strictly dominates baseline node decay ($\sum \gamma_{ij} \gg \sum \gamma_i$). The required flux is therefore lower-bounded by the edge sum:

$$\Phi_{required} \geq \alpha \cdot \gamma_{min} \cdot |E|$$

For a subgraph with $N$ nodes and average degree $d_{avg}$, the number of edges is $|E| = N \cdot d_{avg}/2$. Imposing the resource limit $\Phi_{required} \leq \Phi^*$ yields:

$$\alpha \gamma_{min} \cdot \frac{N d_{avg}}{2} \leq \Phi^* \implies N \leq \sqrt{\frac{2\Phi^*}{\alpha \gamma_{min} d_{avg}}}$$

The square-root scaling bound is a direct dynamical consequence of topological cross-dissipation in non-equilibrium steady states.

### Structural Consequences

Three consequences follow. First, the sustainable hypothesis count depends on the *coupling topology*, not just the hypothesis count. Adding a proposition orthogonal to all existing ones ($\gamma_{ij} \approx 0$ for all $j$) costs nothing; adding one that couples destructively to many carries the full quadratic cost — which explains why domain expertise, by shaping coupling topology, extends cognitive capacity beyond the naïve bound.

Second, the bound is computable given measurable parameters: $\gamma_{min}$, $d_{avg}$, $\Phi^*$, and $\alpha$. All four are observables of correlation spectroscopy.

Third, premature commitment — collapsing a suspended hypothesis on dissipative rather than evidential grounds — is a dynamical prediction with a precise triggering condition: accumulated $\Phi_{required}$ approaches $\Phi^*$ and the system sheds $s$-states to recover maintenance capacity.

---

## §7 — Trajectory Space and the Active Matter Measure

MPC is fundamentally **non-Markovian**. State is not a scalar attached to a configuration; it is the implicit structural deformation encoded within trajectories and their memory kernels. This section develops the formalism in three compatible layers: history-dependent constraint potentials (§7.1), a generalized Langevin equation in the trail vectors (§7.2–§7.3), and a path-integral / field-theoretic representation that unifies them (§7.4–§7.5). The remaining subsections identify the framework's empirical signatures and its internal resource-limit structure.

### §7.1 History-Dependent Constraint Potentials

Each constraint is explicitly history-dependent:

$$V_A^{(\beta)}(x(t)) = V_A(x(t)) + \int_{-\infty}^t K_A(t-s) \cdot \delta_A(x(s))\, ds$$

where $K_A$ is the memory kernel of constraint $A$ and $\delta_A$ tracks violations along the trajectory. Satisfying a constraint, releasing it, and re-satisfying it yields a non-zero integral over closed paths in history space:

$$\oint_\gamma V_A\, d\tau \neq 0$$

This is the formal origin of hysteresis, aging, and path-dependence in MPC. Older constraints possess deeper kernels — this is where structural aging enters the theory natively, not as a bolted-on extension. The trail vectors $d_A$ introduced in §2 are the geometric counterpart of the same memory structure: $V_A^{(\beta)}$ aggregates past *violations*; $d_A$ aggregates past *motion weighted by $K_A$*. They are two parameterizations of the same history, related by the kernel.

### §7.2 Generalized Langevin Equation in the Trail Vectors

Let $x(t) \in \mathcal{X}$ denote the system configuration. For each proposition $A$, the trail vector $d_A(t) = \int_{-\infty}^{t} K_A(t-s)\, \dot{x}(s)\, ds$ aggregates past motion into a direction of persistent structural influence. The system evolves according to a generalized Langevin equation (GLE):

$$\dot{x}(t) = \sum_{A} \eta_A\, d_A(t) + \sum_{A,B} \chi_{AB}\, \mathrm{proj}_{d_A(t)}\big(d_B(t)\big) + \eta(t)$$

where $\eta_A$ are drift gains (self-reinforcement along each trail), $\chi_{AB}$ are coupling coefficients (negative for cooperative alignment, positive for destructive interference), $\mathrm{proj}_{d_A}(d_B)$ is the component of $d_B$ along $d_A$, and $\eta(t)$ is zero-mean noise with covariance $\langle \eta(t)\eta(t')\rangle = \Sigma_\Phi(t,t')$ specified in §7.3.

This is a multi-kernel generalized Langevin system. Non-Markovianity enters through the trail vectors; inter-constraint interactions enter as projected couplings. The resulting drift is **history-induced advection** in trajectory space. The coupling coefficients $\chi_{AB}$ and the measured cross-dissipations $\gamma_{ij}$ (§2) share their sign structure: $\chi_{AB} > 0$ produces destructive shear, which manifests as $\gamma_{ij} > 0$ under correlation measurement, and similarly for the cooperative sign.

### §7.3 Active Noise and Flux-Coupled Fluctuations

Unlike equilibrium Langevin systems, the noise is resource-coupled. Its covariance is determined by the available negentropic flux $\Phi^*$ and environmental decorrelation scale $\tau_{env}$:

$$\Sigma_\Phi(t, t') \sim \mathcal{F}\!\left(\Phi^*,\ \tau_{env},\ \{\gamma_A\}\right)$$

with no requirement of fluctuation–dissipation balance. The effective diffusion coefficient has two components:

$$D_{\text{eff}} = D_{\text{thermal}} + D_{\text{active}}, \qquad D_{\text{thermal}} \sim k_B T / \gamma_{\text{fric}}, \quad D_{\text{active}} \sim \Phi^* / \gamma_{env}$$

$D_{\text{thermal}}$ is the standard Einstein-relation diffusion set by bath temperature; $D_{\text{active}}$ is the drive-induced fluctuation scale set by organized flux relative to environmental dissipation. MPC applies in the regime $D_{\text{active}} \gg D_{\text{thermal}}$, where flux — not temperature — is the dominant control parameter. In this regime the path measure departs from Onsager–Machlup equilibrium form and the Fluctuation–Dissipation Theorem is no longer expected to hold, with a regime-specific structure of violation described in §7.7.

Irreversible bookkeeping — Landauer erasure, the irreducible cost of decision resolution — is still set by the thermal floor $k_B T \ln 2$, because these quantities count minimum heat dumped into the bath to which the system is ultimately coupled. Steady-state trajectory dynamics are active-dominated; irreversible ledger entries remain thermal. No inconsistency arises because the two play different roles in the formalism.

### §7.4 Path Integral Representation (Martin–Siggia–Rose)

The stochastic dynamics of §7.2–§7.3 admit a field-theoretic representation via the Martin–Siggia–Rose / Janssen–De Dominicis functional. Introducing the response field $\hat{x}(t)$:

$$\mathcal{Z} = \int \mathcal{D}x\, \mathcal{D}\hat{x}\; \exp\!\left[-\int dt\; \left( \hat{x} \cdot \big(\dot{x} - v[x]\big) + \hat{x} \cdot \Sigma_\Phi \cdot \hat{x} \right)\right]$$

with drift

$$v[x](t) = \sum_{A} \eta_A\, d_A(t) + \sum_{A,B} \chi_{AB}\, \mathrm{proj}_{d_A(t)}\big(d_B(t)\big)$$

All non-Markovian structure is contained in the kernels defining $d_A$, making the action explicitly history-dependent. Response and correlation functions follow from functional derivatives in the standard MSRJD formalism, enabling direct computation of fluctuation–response relations. Because the noise is geometrically coupled, the MSRJD action assumes a specific discretization convention (typically Stratonovich, for physical systems driven by colored noise), which ensures standard chain rules apply.

### §7.5 Active Measure and Survival Lagrangian

The trajectory weight of §7.4 can be expressed equivalently in Onsager–Machlup form with an endogenous metric:

$$d\mu[\gamma] = \frac{1}{Z(t)} \exp\!\left(-\frac{1}{2}\int dt\; \|\dot{x}(t) - v[x]\|^2_{M[x]} - \int dt\; \Phi^*(s)\, \mathcal{L}_{survival}\right)$$

where the metric $M[x]$ is the inverse of the noise covariance $\Sigma_\Phi$. This metric is itself shaped by the trail geometry: diffusion is suppressed along dominant trail directions (high persistence) and enhanced transverse to them (exploratory degrees of freedom). Anisotropic fluctuation structure is induced, not imposed.

The survival Lagrangian penalizes constraint violation, weighted by the local memory kernel so that older constraints are prioritized. A sigmoidal saturation prevents any single deep constraint from accumulating unbounded local weight and paralyzing dynamical flexibility:

$$\mathcal{L}_{survival} = \sum_{A \in \Gamma} \lambda_A V_A(\gamma(t)) \cdot \sigma\!\left(-\int_{-\infty}^t \gamma_A(s)\, ds\right)$$

Deep commitments pull harder on the trajectory, but not infinitely hard — a necessary condition for a system capable of revising axioms in extremis. We assume memory kernels $K_A$ and penalty weights $\lambda_A$ are bounded such that the trajectory measure remains normalizable.

**Status of the sigmoid.** This saturation is provisional. It regulates *per-constraint local weight*, while the soft flux boundary in $Z(t)$ (§7.6) regulates *global trajectory feasibility*. The two act on different scales and are not strictly redundant: without $\sigma$, a single deep constraint can dominate locally even when the global trajectory measure is healthy. A more principled theory would derive saturation from competition for finite flux rather than from an inserted nonlinearity. The adjudicating test is direct: set $\sigma \equiv 1$ and observe whether the system exhibits catastrophic rigidity — inability to revise deep commitments even when survival demands it. If rigidity emerges, the sigmoid is load-bearing; if not, the flux penalty alone suffices and $\sigma$ should be eliminated.

### §7.6 Soft Flux Boundary

Real physical budgets are leaky and stochastic. Rigid global boundaries are replaced by a soft quadratic penalty embedded in the partition function, acting on the total trail mass $\mathcal{M}(t) = \sum_A \|d_A(t)\|$ as the direct proxy for required flux:

$$Z(t) = \int \mathcal{D}[\gamma] \exp\!\left(-\beta_\Phi \int_{-\infty}^t \max\!\big(0,\, \mathcal{M}(s) - \bar{\Phi}^*\big)^2\, ds\right)$$

Transient violations (borrowing against the bath) are permitted; sustained overdrafts are punished quadratically. This collapses the trajectory measure exactly as observed in biological fatigue and training instabilities in learning systems.

### §7.7 Regime-Specific Fluctuation–Dissipation Structure

FDT violation per se is generic in non-equilibrium systems — glasses, driven colloids, and active particles all exhibit it. The distinguishing empirical claim of MPC is not *that* FDT is violated but *what structure* the violation takes. MPC makes two linked claims: a **scalar per-regime signature** and a **tensorial anisotropy**, the latter being a refinement of the former in systems where the trail geometry is resolvable.

Define the Fluctuation–Dissipation Ratio

$$X(t, t') = \frac{k_B T \cdot R(t, t')}{\partial_{t'} C(t, t')}$$

where $R$ is the response function to a small perturbation and $C$ is the autocorrelation. In active-dominated regimes the effective temperature scale in the numerator is $D_{\text{eff}}$ rather than $k_B T$; the predictions below are stated in the dimensionless quantity.

**Scalar per-regime signature.**

- **$r$-regime:** $X = 1$. FDT holds; the constraint has equilibrated to the bath.
- **$s$-regime:** $X$ is *time-dependent* (the aging signature), settling toward a non-unit steady-state value as the system reaches its non-equilibrium steady state. Magnitude of deviation from unity scales with the survival margin $|\gamma_A|$.
- **$c$-regime:** $X$ is stable at a low value. The deeper the memory kernel, the smaller $X$ — the system resists structural change far beyond its spontaneous fluctuations. The qualitative claim is that $X$ decreases monotonically with the magnitude of the survival margin.
- **$k$-regime:** $X$ is *non-monotonic or negative*. Destructive cross-dissipation means the system's response to perturbation can be anticorrelated with its spontaneous fluctuations — a distinctive signature not predicted by generic aging or active-matter models.

**Tensorial anisotropy.** Because the induced metric $M[x]$ of §7.5 is anisotropic along the trail geometry, the FDR itself is a tensor with distinguishable components parallel and transverse to dominant trails:

$$X_{\parallel} \ll 1, \qquad X_{\perp} \approx 1$$

Response is strongly suppressed along memory axes while remaining near-equilibrium in orthogonal subspaces. The scalar per-regime signature above is the diagonal projection of this tensor along the trail axis; the tensorial claim is sharper, and is the form expected to dominate in substrates where trail geometry is directly resolvable (e.g. high-dimensional neural codes, active polymer gels). Uniform FDT violation without either regime-dependent or axis-dependent structure would disconfirm MPC as a specific theory while remaining consistent with the generic non-equilibrium character of the substrate.

### §7.8 Emergent Forgetting (Obsolescence of Explicit Decay)

Earlier architectural drafts of physically-grounded inference systems posited the need for explicit "temporal frustration decay" rules to actively cull stale contradictions from the interaction graph. Under the trail-vector formulation, **explicit decay mechanisms are redundant**.

Cross-dissipation is the geometric projection of trail vectors, $\gamma_{ij} \propto \mathrm{proj}_{d_A}(d_B)$. If a hypothesis is no longer reinforced by incoming observations, its memory kernel window advances and its trail vector $d_A(t)$ naturally shrinks. As $\|d_A\|$ decays toward zero, its geometric projection onto any neighboring trail also approaches zero, and the associated $\gamma_{ij}$ falls below the noise floor. The system organically drops stale conflicts because the physical, advective footprint of the unreinforced hypothesis has simply evaporated into the bath. Explicit decay rules may be redundant in substrates exposing the trail geometry.

### §7.9 Summary

This formulation embeds MPC within established non-equilibrium statistical mechanics: generalized Langevin dynamics provide the non-Markovian evolution; MSRJD field theory provides the trajectory measure and response calculus; Onsager–Machlup geometry encodes anisotropic diffusion; flux constraints introduce resource-bounded persistence. MPC's novelty lies in interpreting these structures as a logic of survival under dissipation, where propositions correspond to dynamically maintained, history-bearing constraints rather than static truth assignments.

---

## §8 — A Concrete Instantiation on Binary Constraint Systems

### 8.1 Configuration and Trajectory Space

Let configurations live in $\mathcal{X} = \{0,1\}^n$, with trajectories $\gamma: \mathbb{R} \to \mathcal{X}$ generated by stochastic dynamics (e.g., Glauber or continuous-time Markov chains) against a thermal bath. Propositions are defined as constraints on configurations:

$$A: x_1 = 1 \qquad B: x_1 \oplus x_2 = 0 \qquad C: x_2 = 0$$

### 8.2 Constraint Potentials and Timescales

Each proposition induces a penalty:

$$V_A(x) = \begin{cases} 0 & \text{if } x \models A \\ \lambda_A & \text{otherwise}\end{cases}$$

These penalties modify transition rates; $\tau_A$ is then extracted from the autocorrelation of $V_A$ along trajectories, and $\tau_{env}$ from the same observable evaluated in the unconstrained bath ($\lambda_A = 0$).

### 8.3 Worked Example: Three-Constraint Frustration

Let $n = 2$, with $A: x_1 = 1$, $B: x_2 = 1$, $C': x_1 \oplus x_2 = 1$. Setting all penalties equal:

- $A \land B$: satisfiable at $(1,1)$; joint structure viable; $\gamma_{AB} < 0 \to c$
- $A \land C'$: satisfiable at $(1,0)$; viable; $\gamma_{AC'} < 0 \to c$
- $B \land C'$: satisfiable at $(0,1)$; viable; $\gamma_{BC'} < 0 \to c$
- $A \land B \land C'$: no satisfying assignment; the three constraints destructively interfere across the trajectory; $\gamma_{ABC'} > 0 \to k$

Pairwise survival is compatible with global destructive interference. This is the minimal concrete $k$-state.

### 8.4 Relation to Existing Systems

This construction maps onto weighted CSPs, Ising models with frustration, Markov random fields, and energy-based models in machine learning, with the crucial addition that dynamics, not just ground states, are the object of study. MPC can therefore be understood as an interpretive and algebraic layer over these systems operated in their non-equilibrium steady-state regime, rather than a replacement for them.

---

## Addendum I — Decisions, Differentials, and Irreducible Resolution Cost

### The Decision Differential

Define the operator $\partial_A$ on suspended trajectories:

$$\partial_A : s \mapsto c_A \otimes r_{\neg A}$$

This maps a suspended state to the product of a committed alternative and the released residue of the other — formalizing the structure of a decision as the simultaneous formation of one autocatalytic structure and the dissolution of another into the bath.

### The Irreducible Resolution Cost

Boolean logic treats $A \lor \neg A$ as trivially true at zero cost. MPC predicts a minimum cost for any definite resolution of a suspended proposition:

$$\mathbb{E}\!\left[ S(A, \neg A) \to C(A \lor \neg A) \right] \geq k_B T \ln 2$$

with the correction term for correlated structures:

$$W_{\text{resolve}} \geq k_B T \ln 2 \cdot \big(1 + I(\neg A; \{D_j\})\big)$$

This is the irreducible cost of becoming certain — the minimum quantity of bath entropy a system must produce to collapse a trajectory distribution onto a single committed branch, scaled by how deeply the rejected alternative had become entangled with dependent structures.

### Commitment Capacity

If the thermal bath has finite entropy capacity $S_{bath}^{max}$, and if we neglect the correlation correction (a lower bound):

$$N_{commitments} \leq \frac{S_{bath}^{max}}{k_B \ln 2}$$

In practice the correlation correction tightens this bound substantially for embedded systems.

---

## Addendum II — The Frame Problem in AI

The frame problem concerns the difficulty of specifying which facts remain unchanged when an action is performed. In a Boolean inference system, any update potentially requires re-evaluating every proposition in the knowledge base. This is a structural consequence of Boolean logic's binary commitment requirement and its indifference to trajectory.

### The MPC Resolution

In MPC, propositions not dynamically coupled to a given action remain in their current regime with no re-evaluation, no commitment, and no erasure. Formally, proposition $H_j$ is frame-irrelevant with respect to action $A$ if the cross-dissipation is below the environmental noise floor:

$$|\gamma_{A, H_j}| < \theta$$

Equivalently, the response of $H_j$'s autocorrelation to the perturbation induced by $A$ is below detection. Decoupling is empirically certified by correlation spectroscopy, not stipulated by hand.

### Scaling Estimate

For a knowledge base of $N = 10{,}000$ propositions and $K = 20$ action-coupled propositions:

- **Boolean update cost:** $N \cdot c_{eval}$
- **MPC update cost:** $K \cdot (c_{eval} + c_L)$, where $c_L$ is the correlation-corrected Landauer cost on the few structures that actually require modification.

MPC requires roughly 0.2% of the Boolean update cost in this regime. Savings scale as $\mathcal{O}(K/N)$ and grow with knowledge base size.

### Falsifiability Condition

Update cost in an MPC-structured inference system should scale as $\mathcal{O}(K)$ with the action-coupled proposition count, not as $\mathcal{O}(N)$. If MPC-structured systems do not exhibit the predicted sublinear scaling in $N$, the frame-problem application is disconfirmed.

---

## Addendum III — A Text Analysis Architecture

The MPC framework suggests a concrete pipeline for analyzing documents by the dynamical structure of their claims.

**Step 1: Atomic Partitioning.** Parse the text into discrete propositional units $\{H_1, \ldots, H_N\}$ — a set of floating hypotheses whose individual survival margins and mutual cross-dissipations will be evaluated.

**Step 2: Kernel-Weight Assignment.** Assign each hypothesis a memory-kernel depth based on its linguistic register and argumentative role. Hard commitments (*must*, *never*, *cannot*, *strictly*) receive deep kernels, long $\tau_A$, large magnitude $\gamma_A$, and correspondingly persistent trail vectors. Soft commitments (*tends to*, *might*, *probably*) receive shallow kernels.

**Step 3: Cross-Dissipation Matrix.** Evaluate $\gamma_{ij}$ for all pairs. In high-dimensional embeddings from language models, semantic incompatibility provides a tractable proxy for destructive cross-dissipation; directional implication structures can be read from asymmetries in kernel propagation.

**Step 4: Regime Readout.** Given a notional flux budget $\Phi^*$, assign each hypothesis its MPC regime. The $k$-states are analytically productive: they mark where the text simultaneously demands mutually destructive commitments — where real intellectual work remains undone. The $s$-states mark claims the text holds at ongoing cost but has not yet autocatalyzed into $c$. The $r$-regime marks where the text has equilibrated to the surrounding discourse and has no structural content.

---

## Addendum IV — A Field-Theoretic Reading (Heuristic)

Each proposition $A$ induces a scalar field $V_A$ over the trajectory space. Inference corresponds to motion within the composite field generated by their superposition, driven by the survival Lagrangian and the active measure of §7:

$$V_{\text{total}}[\gamma] = \sum_{A \in \Gamma} V_A^{(\beta)}[\gamma]$$

The functional gradient of $V_{\text{total}}$ over trajectory space defines the local direction of dissipative descent; the topology of the resulting landscape — now over paths, not points — determines the qualitative regime of the system. Under this reading, the MPC regimes correspond to canonical trajectory-space structures: $c$ is a deep autocatalytic basin with a persistent trail aligned along its axis; $s$ is a weakly stabilized ridge maintained by flux, with a replenished but decay-prone trail; $k$ is irreducible destructive interference between field components whose trails project against one another; $r$ is the flat field in which all trajectories relax to bath statistics and all trails vanish.

This is an interpretive layer, not a claim about fundamental fields in spacetime. The "field" is defined over the system's internal trajectory space, and its status is that of an effective description induced by constraint kernels and the active measure.

---

## A Structural Conjecture

*The following section presents a structural conjecture. It is not a theorem, not a derivation, and not a candidate physical interpretation in its current form. The formal results of Sections 1–7 are independent of it.*

### The Completion Hypothesis

If MPC is the correct formal framework for physically realizable inference, then Boolean logic and classical physics may be understood as projections of a richer dynamical structure: the limits $\Phi^* \to \infty$ and $\tau_{env} \to \infty$ in which all maintenance costs vanish, all cross-dissipations become orthogonal, and the active trajectory measure collapses onto a static configuration distribution. In these limits, $s$ cannot exist (no dissipative maintenance is ever required), $k$ is impossible (destructive interference cannot arise if dissipation is absent), and $r$ becomes reversible. This is the regime Boolean logic describes.

### Partial Structural Correspondence with Quantum Mechanics

At low-noise, high-coherence limits of active-matter dynamics, suspended structures no longer decay stochastically but persist as coherent superpositions of viable trajectories — with partial formal correspondence to quantum superposition. We emphasize "partial": quantum mechanics involves complex amplitudes, interference of phases, and unitary evolution — features not directly present in the real-valued trajectory measure of MPC as currently formulated.

The most scientifically suggestive point of contact is the irreducible cost of measurement. Under MPC, resolving an $s$-trajectory to a $c$-trajectory requires bath entropy production of at least $k_B T \ln 2$, corrected by the correlation structure being collapsed. Quantum measurement similarly involves an irreducible and dissipative interaction with a measurement apparatus. Whether these are instances of the same underlying constraint is an open empirical question, not a conclusion of this paper.

### What Would Confirm or Disconfirm

The conjecture would gain significant support if: (i) a rigorous formal embedding of quantum amplitudes into an extended (complex-valued) MPC trajectory measure were demonstrated; (ii) the dissipative cost of measurement were shown to saturate the correlation-corrected Landauer bound in a regime where MPC's quantitative predictions hold; or (iii) decoherence rates were derivable from the finite-temperature, finite-$\Phi^*$ dynamics of MPC rather than postulated.

---

*Metastable Propositional Calculus — a formal theory of resource-bounded inference in which propositions are dynamical structures, truth values are survival regimes, and logic is the algebra of what a finite system can keep alive against its environment.*

*Correspondence and objections welcomed as tests, not obstacles.*
