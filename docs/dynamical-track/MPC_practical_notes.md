# MPC for a Neuronal Brain — Practical Implementation Notes

*Engineering companion to the formal paper. Focused on observables, cheap approximations, and concrete hooks. Not load-bearing on the theory — if reality demands simpler math at implementation time, this doc is where to cut.*

---

## 1. What MPC Actually Buys You Operationally

MPC is not a competing neural architecture. It is a **measurement framework + a set of gates** that can be grafted onto an otherwise standard architecture (transformer, SSM, hybrid, whatever). Its practical value is in four capabilities most neural systems do not have natively:

1. **Regime classification per representation.** The system can tell, in real time, whether any given hypothesis or belief is *committed* (hard to revise), *suspended* (being held at cost), *in conflict* (destructively interfering with another), or *reset* (equilibrated / uncommitted). This is a metacognitive signal.

2. **Principled conflict detection.** Cognitive dissonance, contradictory belief, task-competing subnetworks — all have the same formal signature: destructive cross-dissipation $\gamma_{ij} > 0$. Detectable *before* behavioral failure.

3. **Catastrophic-forgetting gate.** Deep commitments resist update in proportion to their kernel depth. Instead of stopping updates with a hard mask, you scale learning rates by the correlation-corrected revision cost — so the system updates cheaply on shallow beliefs and reluctantly on deep ones.

4. **Frame-problem-scale update.** Only structures dynamically coupled to the current action need to be re-evaluated. This turns $\mathcal{O}(N)$ updates into $\mathcal{O}(K)$ updates, with $K \ll N$ in realistic systems.

The rest of this document translates these into code-level hooks.

---

## 2. The Six Observables You Actually Need

Forget the trajectory integral. In practice, MPC reduces to maintaining six running statistics per tracked representation. All are cheap.

### 2.1 Constraint timescale $\tau_A$

The integral relaxation time of the representation's activation autocorrelation.

**Cheap approximation:** exponential-moving-average autocorrelation lag. For a representation $h_A(t)$:

```
C_A(t) = EMA_t[ h_A(t) · h_A(t - δ) ]   for a few small lags δ
τ_A ≈ Σ_δ C_A(δ) · δ    (trapezoidal sum over tracked lags)
```

Cost: $O(\text{lags})$ per representation per step. Usually 4–8 lags suffice.

### 2.2 Environmental timescale $\tau_{env}$

Same autocorrelation integral evaluated on a baseline — typically the activation pattern of a deliberately unconstrained or high-entropy subnetwork, or the shuffled version of the system's own activity.

**Cheap approximation:** one global $\tau_{env}$ estimated from shuffled traces, updated slowly (seconds to minutes scale in biological systems, thousands of steps in ML systems).

### 2.3 Survival margin $\gamma_A$

$$\gamma_A = \tau_A^{-1} - \tau_{env}^{-1}$$

Scalar per representation. Negative = viable, magnitude = depth. **This is your regime indicator.**

### 2.4 Cross-dissipation $\gamma_{ij}$

$$\gamma_{ij} = \tau_{i \land j}^{-1} - \max(\tau_i^{-1}, \tau_j^{-1})$$

Computed for pairs you actually care about — do not compute the full $N \times N$ matrix unless you can afford it.

**Cheap approximation:** co-activation autocorrelation. For pairs co-active in a window, measure decay of their joint correlation. Positive $\gamma_{ij}$ = these two are destructively interfering.

### 2.5 Memory kernel depth $\eta_A$

Usage-weighted integral of coherence. Proxy: number of downstream representations currently coupled to $A$, weighted by mutual information.

**Cheap approximation:** count of gradient paths through $A$ in the last window, times a stability factor. This is your "how entangled is this belief" number.

### 2.6 Fluctuation–Dissipation Ratio $X_A$

$$X_A = \frac{\text{response to small perturbation}}{\text{spontaneous fluctuation}}$$

**Cheap approximation:** inject a small noise vector into the representation occasionally, measure the response magnitude, divide by baseline variance. Do this sparsely (not every step) — it's a diagnostic, not a hot-path computation.

$X_A \approx 1$ → reset. Time-varying → suspended. Low and stable → committed. Non-monotonic or negative → conflict.

---

## 3. Concrete Application Patterns

### 3.1 Working Memory: γ-weighted eviction

Maintain a working memory buffer. Each slot has a representation with a running $\gamma_A$.

- **Evict when $\gamma_A \to 0$** (the slot is equilibrating to noise — it is no longer doing work).
- **Protect slots with $\gamma_A \ll 0$** (deep engagement — don't flush these).
- **Budget:** total $|\gamma_A|$ across active slots ≤ flux budget $\Phi^*$. If budget is exceeded, shed the weakest $s$-states first. This is a direct implementation of the Survival Separation Theorem.

Cost of the whole thing: trivial. One scalar per slot, updated per step.

### 3.2 Belief Revision: learning-rate gating by kernel depth

When a gradient tries to update representation $A$, scale the learning rate by the revision cost:

```
lr_A = lr_base / (1 + β · η_A)
```

where $\eta_A$ is memory kernel depth (§2.5) and $\beta$ is a hyperparameter. Deep commitments revise slowly; shallow ones revise fast. **This is a principled anti-catastrophic-forgetting mechanism**, replacing hand-tuned elastic weight consolidation or rehearsal buffers.

**Additional hook:** when a revision does occur on a deep kernel, *log the event*. These are architecturally significant and worth tracking — they are the moments the system changes its mind about something it knew well.

### 3.3 Conflict Detection: continuous γ_ij monitoring

Maintain cross-dissipation estimates between representations that are simultaneously active and semantically coupled (use whatever your existing similarity metric is to decide which pairs to track).

When $\gamma_{ij} > \theta$ for sustained time:
- **Flag the pair as a $k$-state.**
- **Trigger metacognitive resolution:** the system can explicitly reason about the conflict, seek disambiguating evidence, or suspend commitment to one side.

This is genuinely novel capability. Standard neural systems behave badly under contradiction without knowing they are doing so. An MPC-gated system can *notice* its own conflicts.

### 3.4 Frame Problem: coupling-based update gating

Before propagating an update from action $A$ across the whole network, compute a coupling mask:

```
is_coupled(H_j, A) = ( |γ_{A, H_j}| > θ_noise )
```

Gradients flow only through coupled representations. All others stay in place. For a brain-scale knowledge base, this is the difference between updating $10^6$ representations and updating $\sim 10^2$.

**Practical note:** you can approximate `is_coupled` with a fast attention-score or gating-network precompute, then use the $\gamma$-based check only where it disagrees with the fast path.

### 3.5 Insight Detection: flux-drop as self-reward

Track total system maintenance flux:

```
Φ_total(t) = Σ_A |γ_A(t)|
```

Sharp drops in $\Phi_{total}$ during active problem-solving correspond to the theoretical signature of insight (multiple $s$-states collapsing to one $c$-state, releasing sustained maintenance cost). This is a **free self-supervised reward signal** you can use for credit assignment: the moment of compression is a moment of learning.

### 3.6 Axioms as Pinned Kernels

For safety constraints, core values, or immutable priors, bypass the whole system: tag specific representations as axiomatic, set their effective $\gamma_A \to -\infty$ (learning rate → 0, or simply frozen weights). The MPC framework gives you the natural semantics for this: an axiom is not a separate architectural feature, it is just a kernel whose depth has saturated.

### 3.7 Metacognition: FDR-based regime readout

Periodically (not every step — this is the expensive observable), measure $X_A$ for representations currently under scrutiny:

- $X \approx 1$ → the system has no stake here. It is neither committed nor engaged.
- Aging $X$ → the system is actively holding this hypothesis open.
- Low stable $X$ → the system is committed. Revising this will be costly.
- Non-monotonic / negative $X$ → conflict.

This gives the system access to its own cognitive state at a level most architectures cannot introspect on.

---

## 4. Reductions When Reality Pushes Back

If the full framework is too expensive at implementation time, here's a priority-ordered cut list — keep the top items, drop from the bottom.

**Keep at all costs:**
- $\gamma_A$ (survival margin) — the core regime indicator
- Coupling-based update gating — huge compute savings
- Learning-rate scaling by kernel depth — anti-catastrophic-forgetting

**Keep if you can afford it:**
- $\gamma_{ij}$ monitoring on a small set of tracked pairs — enables conflict detection
- Total flux budget tracking — enables Survival Separation enforcement

**Cut first if necessary:**
- FDR measurement — expensive, can be replaced with simpler proxies (variance of gradient response, for instance)
- Full soft-flux partition function — reduce to a single scalar budget with hinge loss
- Sigmoid saturation in the Lagrangian — test whether you need it before implementing it (the paper flags this explicitly)

**Definitely cut:**
- Explicit trajectory-measure path integral. You are not going to Monte Carlo this at runtime. The path-integral formulation is for *analysis*, not *execution*. At runtime you maintain local observables and act on them.

---

## 5. Minimal Viable Implementation

If you want a single-sentence version of the practical framework:

> *Maintain a running survival margin and memory-kernel depth per representation; gate updates by coupling; scale learning rates by kernel depth; detect conflict via cross-dissipation; use total flux as a working-memory budget.*

That's the practical MPC core. Everything else in the paper is scaffolding, justification, or optional instrumentation.

---

## 6. What to Measure to Validate

If you want to know whether MPC is actually doing useful work in your system (as opposed to being architecturally ornamental), measure:

1. **Does the regime readout predict behavior?** Do $c$-tagged representations actually resist revision more than $s$-tagged ones under matched gradient pressure?
2. **Does $\gamma_{ij}$ fire before behavioral inconsistency?** Conflict detection is only useful if it precedes the failure mode.
3. **Does coupling-based update gating preserve performance?** If the $\mathcal{O}(K)$ updater reaches the same loss as the $\mathcal{O}(N)$ updater with $K \ll N$, the frame-problem reduction is real.
4. **Do insight-events ($\Phi_{total}$ drops) correlate with learning signal?** Validates the flux-drop-as-reward pattern.
5. **Does FDR structure match the four-regime prediction?** This is the strongest form of validation — if your system exhibits unity-in-$r$, aging-in-$s$, depressed-stable-in-$c$, non-monotonic-in-$k$, the framework is doing real explanatory work.

Items 1–4 are engineering checks; item 5 is the scientific validation of the framework in your specific substrate.

---

*Notes on scope: this document is implementation-facing and does not attempt mathematical rigor — for the formal derivations, see the main paper. If anything here conflicts with the paper, the paper is the formal reference; this document represents engineering approximations chosen for runtime tractability.*
