# On the Physical Limits of Boolean Algebra as a Theory of Inference
## Metastable Propositional Calculus as a Thermodynamic Extension

**Formal Framework · Resource-Bounded Inference**

---

### Core Contribution

MPC formalizes the distinction between what can be true together and what can be maintained together under finite resources. This distinction is absent from Boolean logic by design; MPC argues it is absent from Boolean logic by physical necessity.

---

### Abstract

Boolean algebra, the formal system underlying classical computation, rests on an implicit physical assumption: that information processing is costless, instantaneous, and atemporal. This assumption holds only in the limit of equilibrium systems with unlimited energetic reserves. Boolean logic remains formally closed under its own axioms; what fails under finite energetic and temporal budgets is the physical instantiation of its unconstrained compositional semantics. When that instantiation constraint is made explicit, Boolean logic is no longer an adequate model of physically realizable inference.

We introduce **Metastable Propositional Calculus (MPC)**, a resource-sensitive, four-valued logical system grounded in non-equilibrium thermodynamics. Rather than postulating truth values, MPC derives logical semantics from a variational process over a latent energy landscape, with potentials defined relative to the thermal energy scale $k_B T$. We prove a **Thermodynamic Separation Theorem** establishing that families of classically consistent inferences cannot be jointly maintained under a finite metastability budget.

---

## §1 — The Equilibrium Assumption and Its Physical Failure

Boolean algebra models a proposition as a system resting at a global energy minimum. This is a valid and useful abstraction under idealized conditions. To be precise: Boolean logic is not broken. It remains formally closed, consistent, and complete within its own axioms. What we claim is more specific: the unconstrained compositional semantics of Boolean logic — its assumption that any consistent set of propositions can be simultaneously instantiated without energetic cost — is not preserved under finite energetic and temporal budgets.

Physically realized inference systems violate three of Boolean logic's tacit physical assumptions in ways that are structural, not marginal.

#### Failure I — Sustained uncertainty carries a cost

A hypothesis that has not yet been resolved must be actively maintained in a metastable configuration against the tendency of the system to relax into a committed state. The energetic cost of holding unit $i$ in such a state is lower-bounded by:

$$P_i \gtrsim \frac{\Delta E_i}{\tau_i}$$

where $\Delta E_i$ is the barrier height (in units of $k_B T$) and $\tau_i$ is the natural relaxation timescale. A system with finite power cannot maintain this cost indefinitely.

#### Failure II — Negation is not free

Boolean negation treats $\neg p$ as a syntactically costless operation. Landauer's principle establishes otherwise: erasing a committed state from a physical system dissipates at minimum $Q \geq k_B T \ln 2$ of heat into the environment. This result is experimentally confirmed. Committing to $p$ and erasing $\neg p$ is a thermodynamic event, not a logical formalism.

#### Failure III — Contradiction is a physical state, not a logical halt

In systems with irreconcilable constraints, competing potentials do not produce a crash or an undefined value. They produce a high-energy local minimum — a structurally informative configuration that the system occupies and continues to operate within, at elevated energetic cost, until sufficient work is done to resolve it. Boolean logic has no representation for this state. MPC introduces one.

---

## §2 — Energy Functional, Normalization, and Compatibility

Let $\mathcal{X}$ denote a configuration space and $E_0(x)$ a base energy landscape. Each formula $A$ induces a constraint potential $V_A(x) \geq 0$, where $V_A(x) = 0$ precisely when configuration $x$ satisfies $A$.

### Normalization Axiom

Constraint potentials are defined in natural units of thermal energy: all energies are expressed as multiples of $k_B T$ at the operating temperature $T$ of the inference system. Formally, potentials are defined up to the equivalence class of transformations that preserve (i) the relative barrier structure between configurations and (ii) the Boltzmann-weighted accessibility of minima at temperature $T$.

The joint energy of realizing formulas $A$ and $B$ simultaneously is:

$$E(A, B) = \inf_{x \in \mathcal{X}} \left[ E_0(x) + V_A(x) + V_B(x) \right]$$

All energies are in units of $k_B T$. Two formulas are **logically compatible** ($A \parallel B$) if a finite joint minimum exists: $E(A, B) < \infty$. They are **thermodynamically accessible** ($A \approx B$) if $E(A, B) \leq E^*$, where $E^*$ is the dimensionless energy budget of the system. These are not equivalent, and conflating them is the structural error MPC is designed to correct.

### Boundary Condition: Shared Embedding

MPC assumes that the set of propositions under consideration admits a joint embedding into a shared constraint space $\mathcal{X}$. This is a nontrivial assumption. The boundary of MPC's applicability is precisely the boundary at which a shared configuration space can or cannot be coherently constructed. Acknowledging this boundary is not a weakness of the framework; it is the condition that makes it scientifically tractable.

---

## §3 — Metastable Propositional Calculus: Truth Values

MPC is a four-valued logic in which the truth values $\mathcal{V} = \{c, s, k, r\}$ represent the canonical regimes of the constraint energy landscape. The values are derived from the topology of $V_A(x)$ under the normalization of Section 2, not postulated independently.

MPC truth values are **relational**. They are not intrinsic properties of a proposition but properties of the relationship between a proposition and the substrate realizing it. The same proposition may be committed ($c$) in a high-budget system and suspended ($s$) in a resource-constrained one.

### Table 1. The Four Truth Values of MPC

| Sym | Name | Energy Regime | Description | Thermodynamic Character |
|-----|------|---------------|-------------|------------------------|
| **c** | Committed | $E < E_c$ | A satisfying configuration $x^*$ exists and occupies a deep potential minimum. | Low holding cost. High revision cost. Barrier $\Delta E \gg k_B T$. |
| **s** | Suspended | $E_c \leq E \leq E_s$ | A satisfying configuration exists, but all minima are shallow; active maintenance required against thermal collapse. | Ongoing holding cost $\propto P_i \gtrsim \Delta E_i/\tau_i$. Barrier $\Delta E \sim k_B T$. |
| **k** | Conflict | $E > E_s$ (no min) | No satisfying configuration exists; the constraint landscape has no feasible minimum. A structurally informative defect state. | Elevated sustained cost. Persists until resolving work $\geq$ magnitude of frustration. |
| **r** | Reset | $V_A(x) \equiv 0$ | The constraint potential is identically zero. Consistent with all configurations; maximally entropic prior over $\mathcal{X}$. | No holding cost. Acts as identity element in the MPC algebra. |

*All energies in units of $k_B T$. Thresholds $E_c$ and $E_s$ are substrate-dependent system parameters.*

---

## §4 — Operator Algebra

The classical Boolean operators are replaced by thermodynamic operators induced by the stratification of the energy functional.

### Commitment (C) — replaces AND

$$C(A, B) = \begin{cases} 
c & \text{if } E(A,B) < E_c \\
s & \text{if } E_c \leq E(A,B) \leq E_s \\
k & \text{if } E(A,B) > E_s 
\end{cases}$$

Associative within each regime. Reduces to Boolean AND in the limit $E^* \to \infty$.

### Suspension (S) — replaces OR

$S(A, B)$ returns the state corresponding to maintaining two local minima separated by a barrier $\Delta E$. The system holds both potentials without committing to either, at cost $P \cdot \tau$.

### Conflict (K) — replaces XOR

$K(A, B) = k$ when $E(A, B) > E_s$. The conflict magnitude is quantifiable as $\inf_x \left[V_A(x) + V_B(x)\right]$, enabling graded resolution strategies proportional to the magnitude of constraint violation.

### Reset (R) — replaces NOT

$R$ maps every state to $r$, with associated heat dissipation $Q \geq k_B T \ln 2$ per bit erased. $R(r) = r$: resetting an already-unconstrained state is free. The operator is a projection, not an involution — the formal statement of Landauer's principle within the MPC algebra.

### Table 2. Commitment Operator — Truth Table

| $C(A,B)$ | **c** | **s** | **k** | **r** |
|----------|-------|-------|-------|-------|
| **c** | c | c | k | c |
| **s** | c | s | k | s |
| **k** | k | k | k | k |
| **r** | c | s | k | r |

*The $k$-absorbing property reflects the physical fact that joint energy minimization is infeasible when either argument has no satisfying configuration.*

### Note on the Character of the Algebra

$S$ is not a pure function of its propositional arguments — its output depends on $E^*$, the available energy budget, and $\tau$, the relevant timescale. This makes MPC a **state-dependent algebra**. The parameters $(E^*, \tau)$ should be understood as implicit arguments to $S$, made explicit when substrate-specific predictions are required.

---

## §5 — Structural Interpretation and Falsifiable Cognitive Mappings

The following mappings apply MPC to cognitive phenomena. Each is offered as a **falsifiable structural hypothesis**. None is offered as a metaphor, and each requires the empirical premise that the human brain is adequately modeled by an MPC-structured constraint system.

### Working Memory as Metastability

Maintaining an unresolved hypothesis — the $s$-state — requires continuous expenditure to prevent premature collapse into a committed value.

**Falsifiability Condition:** Metabolic cost should scale as $\mathcal{O}(N \cdot d)$, where $N$ is the number of concurrent suspended hypotheses and $d$ is the average constraint degree. If metabolic cost is independent of $d$, or scales superlinearly in $d$ for fixed $N$, the working memory mapping is disconfirmed.

### Cognitive Dissonance as Topological Frustration

Contradictory constraints produce a high-energy $k$-state that the system continues to occupy at elevated cost — the formal analog of cognitive dissonance: a structurally informative defect that persists until resolving work is performed.

**Falsifiability Condition:** The $k$-state predicts a sustained, not transient, metabolic signature during maintained incompatible commitments, distinguishable from the transient spike at conflict detection. If the metabolic signature is transient, or does not scale with constraint violation magnitude, the mapping is disconfirmed.

### Belief Revision as Barrier Crossing

A committed belief occupies a deep potential well. Revision requires surmounting barrier $\Delta E$ and paying the Landauer erasure cost of the prior commitment.

**Falsifiability Condition:** The neural relaxation timescale $\tau_i$ should scale with proxies for commitment depth: prior exposure duration and belief rehearsal frequency. Independence of $\tau_i$ from commitment depth disconfirms the potential-well model.

### Insight as Phase Transition

Convergence from multiple suspended hypotheses to a single coherent $c$-state is structurally analogous to an annealing transition.

**Falsifiability Condition:** If insight corresponds to a genuine phase transition, it should be accompanied by a measurable **decrease** — not increase — in relevant neural metabolic signature at the moment of resolution, reflecting the release of previously sustained $s$-state maintenance costs.

### Axioms as Zero-Temperature Limits

An axiom is a proposition for which the effective temperature in the relevant subspace has been taken to zero: the barrier to revision becomes functionally infinite within that subspace, and the proposition organizes all other inferences around it as a fixed topological feature of the landscape.

---

## §6 — The Thermodynamic Separation Theorem

### Theorem 6.1 (Generalized)

Let $\Gamma = \{H_1, \ldots, H_N\}$ be a classically consistent hypothesis set. Let the pairwise frustration between $H_i$ and $H_j$ be $\varepsilon_{ij} \geq 0$ (in units of $k_B T$), and let $G = (V, E)$ be the interaction graph. Let $d_{avg}$ denote the average degree of $G$ and $\alpha \in (0,1]$ a substrate-dependent scaling factor. Then the maximum size of any thermodynamically realizable subset $\Gamma^* \subseteq \Gamma$ satisfies:

$$|\Gamma^*| \leq N_{max} = \mathcal{O}\left( \sqrt{\frac{2E^*}{\alpha \varepsilon_{min} d_{avg}}} \right)$$

where $\varepsilon_{min} = \min_{(i,j)\in E} \varepsilon_{ij}$ is the minimum non-zero pairwise frustration.

#### Proof Sketch

The total joint energy of a realizable subset of size $N$ is bounded below by the sum over active edges in the induced subgraph:

$$E(\Gamma^*) \geq \alpha \cdot \sum_{(i,j)\in E(\Gamma^*)} \varepsilon_{ij} \geq \alpha \varepsilon_{min} \cdot |E(\Gamma^*)|$$

For a subgraph with $N$ nodes and average degree $d_{avg}$, the number of edges is $|E| = N \cdot d_{avg} / 2$. Thermodynamic realizability requires $E(\Gamma^*) \leq E^*$, giving:

$$\alpha \varepsilon_{min} \cdot \frac{N d_{avg}}{2} \leq E^* \implies N \leq \sqrt{\frac{2E^*}{\alpha \varepsilon_{min} d_{avg}}}$$

### Structural Consequences

Three consequences follow. First, the sustainable hypothesis count depends on the interaction topology, not just hypothesis count. Adding a proposition orthogonal to all existing ones costs nothing; adding one that couples to all carries the full quadratic cost — explaining why domain expertise extends cognitive capacity beyond the naïve bound.

Second, the bound is computable given measurable parameters: $\varepsilon_{min}$, $d_{avg}$, $E^*$, and $\alpha$.

Third, premature commitment — collapsing a suspended hypothesis on energetic rather than evidential grounds — is a thermodynamic prediction with a precise triggering condition: the system's accumulated $E(\Gamma^*)$ approaches $E^*$.

---

## §7 — A Concrete Instantiation on Binary Constraint Systems

### 7.1 Configuration Space and Propositions

Let the configuration space be $\mathcal{X} = \{0,1\}^n$. Each configuration $x \in \mathcal{X}$ is an assignment to $n$ binary variables $(x_1, \ldots, x_n)$. Propositions are defined as constraints, e.g.:

$$A: x_1 = 1 \quad\quad B: x_1 \oplus x_2 = 0 \quad\quad C: x_2 = 0$$

### 7.2 Constraint Potentials

Each proposition induces:

$$V_A(x) = \begin{cases} 
0 & \text{if } x \models A \\
\lambda_A & \text{otherwise}
\end{cases}$$

where $\lambda_A > 0$ is a penalty parameter in units of $k_B T$. This defines a fully explicit mapping from logical constraints to energetic cost.

### 7.4 Example: Three-Constraint System

Let $n = 2$, with $A: x_1 = 1$, $B: x_2 = 1$, $C': x_1 \oplus x_2 = 1$. With $\lambda_A = \lambda_B = \lambda_C = 1$:

- $A \land B$: satisfiable $(1,1) \to E = 0 \to c$
- $A \land C'$: satisfiable $(1,0) \to E = 0 \to c$
- $B \land C'$: satisfiable $(0,1) \to E = 0 \to c$
- $A \land B \land C'$: no satisfying assignment $\to E(A,B,C') = 1 \to k$

This is a concrete $k$-state: pairwise compatibility with global frustration. Pairwise consistency does not guarantee global realizability.

### 7.7 Relation to Existing Systems

This construction is equivalent to a weighted constraint satisfaction problem and admits direct correspondence with Ising models, Markov random fields, and energy-based models in machine learning. MPC can therefore be understood as an interpretive and algebraic layer over these well-defined systems, rather than a replacement for them.

---

## Addendum I — Differential Inference and Dissipation

### The Decision Differential

Define the operator $\partial_A$ acting on the energy landscape as:

$$\partial_A : s \mapsto c_A \otimes r_{\neg A}$$

This maps a suspended state to a product of the committed proposition and the erasure residue of its negation — formalizing the structure of a decision: not the selection of one value over another, but the commitment to one and the active erasure of the other.

### The Landauer Gap

Boolean logic treats $A \lor \neg A$ as trivially true at zero cost. MPC predicts a minimum energetic cost for any definite resolution of a suspended proposition:

$$\mathbb{E}\left[ S(A, \neg A) \to C(A \lor \neg A) \right] \geq k_B T \ln 2$$

This is the irreducible cost of becoming certain — not a practical limitation but a theoretical lower bound derivable from the second law of thermodynamics.

### Commitment Capacity

If the thermal bath has finite entropy capacity $S_{bath}^{max}$:

$$N_{commitments} \leq \frac{S_{bath}^{max}}{k_B \ln 2}$$

---

## Addendum II — The Frame Problem in AI

The frame problem concerns the difficulty of specifying which facts remain unchanged when an action is performed. In a Boolean inference system, any update potentially requires re-evaluating every proposition in the knowledge base. This is a structural consequence of Boolean logic's binary commitment requirement.

### The MPC Resolution

In MPC, propositions not thermodynamically linked to a given action remain in the $s$-state and require no evaluation, no commitment, and no erasure. Formally, proposition $H_j$ is frame-irrelevant with respect to action $A$ if:

$$\langle \|\Delta V_A \cdot \nabla V_{H_j}\|_2 \rangle_{\mathcal{X}} < \theta$$

where $\theta$ is a threshold set at the system's thermal noise floor.

### Energetic Savings: A Quantified Estimate

For knowledge base $N = 10,000$ and $K = 20$ action-relevant propositions:

$$\text{Cost}_{\text{Boolean}} = N \cdot c_{eval} = 10,000 \cdot c_{eval}$$

$$\text{Cost}_{\text{MPC}} = K \cdot (c_{eval} + c_L) = 20 \cdot (c_{eval} + c_L)$$

MPC requires approximately 0.2% of the Boolean system's update cost. Savings scale as $\mathcal{O}(K/N)$ and grow with knowledge base size.

### Falsifiability Condition

Update cost in an MPC-structured inference system should scale as $\mathcal{O}(K)$ with action-coupled proposition count, not as $\mathcal{O}(N)$ with knowledge base size. If MPC-structured systems do not exhibit the predicted sublinear scaling in $N$, the frame-problem application is disconfirmed.

---

## Addendum III — A Text Analysis Architecture

The MPC framework suggests a concrete pipeline for analyzing documents by the thermodynamic structure of their claims.

**Step 1: Atomic Partitioning**  
Parse the text into discrete propositional units $\{H_1, \ldots, H_N\}$ — a set of floating hypotheses.

**Step 2: Potential Assignment**  
Assign each hypothesis a constraint potential based on its linguistic register. Hard constraints (*must*, *never*, *cannot*, *strictly*) receive high $\Delta E \gg k_B T$. Soft constraints (*tends to*, *might*, *probably*) receive low $\Delta E \sim k_B T$.

**Step 3: Frustration Matrix**  
Evaluate the joint energy $E(H_i, H_j)$ for all pairs. In high-dimensional latent spaces of language models, semantic distance provides a computationally tractable proxy for energetic compatibility.

**Step 4: Phase Readout**  
Given a metastability budget $E^*$, assign each hypothesis its MPC phase. The $k$-states are analytically productive: they identify where a text simultaneously demands mutually incompatible commitments — the locations where the real intellectual work remains undone.

---

## A Structural Conjecture

*The following section presents a structural conjecture. It is not a theorem, not a derivation, and not a candidate physical interpretation in its current form. The formal results of Sections 1–6 are independent of it.*

### The Completion Hypothesis

If MPC is the correct formal framework for physically realizable inference, then Boolean logic and classical physics may be understood as two projections of the same underlying structure: the infinite-energy limit ($E^* \to \infty$) in which all suspension costs vanish, all conflicts resolve instantaneously, and all erasures are thermodynamically free. Under this limit, $s$ cannot exist, $k$ is impossible, and $r$ is reversible. This is the regime Boolean logic describes.

### Partial Structural Correspondence with Quantum Mechanics

At $T \to 0$, suspended propositions no longer decay stochastically — they persist coherently, maintaining multiple configurations simultaneously. This has partial formal correspondence with quantum superposition. We emphasize "partial": quantum mechanics involves complex amplitudes, interference, and unitary evolution — features not present in the current MPC formalism.

The aspect with the most genuine scientific interest is the cost of measurement. Under MPC, forcing a system from an $s$-state to a $c$-state carries a minimum cost of $k_B T \ln 2$. Quantum measurement similarly involves an irreducible physical interaction. Whether these are instances of the same underlying constraint is an open empirical question, not a conclusion of this paper.

### What Would Confirm or Disconfirm

The conjecture would gain significant support if: (i) a rigorous formal embedding of quantum mechanical amplitudes into an extended MPC framework were demonstrated; (ii) the thermodynamic cost of quantum measurement were shown to saturate the Landauer bound in a regime where MPC predictions are quantitatively precise; or (iii) a decoherence model were derived from MPC's finite-temperature dynamics rather than postulated.

---

## Addendum IV — A Field-Theoretic Interpretation of MPC (Heuristic)

Each proposition $A$ induces a scalar field over $\mathcal{X}$; inference corresponds to motion within the composite field generated by their superposition:

$$V_{\text{total}}(x) = \sum_{A \in \Gamma} V_A(x)$$

The gradient $\nabla V_{\text{total}}(x)$ defines the local direction of energetic descent, and the topology of the landscape determines the qualitative regime of the system. Under this interpretation, the MPC truth values correspond to canonical field configurations: committed ($c$) is a deep basin of attraction; suspended ($s$) is a shallow or weakly separated basin; conflict ($k$) is irreducible frustration; reset ($r$) is a flat field.

This is an interpretive layer, not a claim about fundamental physical fields in spacetime. The "field" is defined over the system's internal configuration space $\mathcal{X}$, and its status is that of an effective description induced by the constraint potentials.

---

## Addendum V — Historical Depth and the Time-Dependent Cost of Deletion

The preceding sections treat the cost of erasure as a function of instantaneous state. However, information that persists over time becomes correlated with other degrees of freedom through its participation in downstream inferences.

### Correlation-Dependent Deletion Cost

The minimal work required to delete $H$ can be expressed as:

$$W_{\text{delete}}(H) \geq k_B T \ln 2 + k_B T \ln 2 \cdot I(H; \{D_j\})$$

where $I(H; \{D_j\})$ is the total mutual information between $H$ and its dependent variables.

### Historical Depth as a State Variable

$$\eta_i \equiv k_B T \ln 2 \cdot I(H_i; \text{dep}(i))$$

This represents the additional work required to delete $H_i$ due to its embeddedness in the system's current correlation structure.

### Modified Energetic Constraint

$$L = \sum_{i \in \Gamma} (P_i \cdot \tau + \beta_i \eta_i) \leq E^*$$

This introduces **informational inertia**: propositions that have been extensively used become energetically "heavier," constraining the system's capacity to incorporate new hypotheses even if the instantaneous state is unchanged.

### Falsifiability Condition

In systems with persistent memory and reusable representations, the work required to remove or overwrite a representation should increase with prior usage, even when its instantaneous encoding is held fixed. Failure to observe any dependence of deletion cost on usage history would disconfirm this extension.

---

*Metastable Propositional Calculus — a contribution to the formal study of resource-bounded inference.*

*Correspondence and objections welcomed as tests, not obstacles.*