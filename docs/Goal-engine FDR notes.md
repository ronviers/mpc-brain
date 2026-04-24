# Goal-engine online-FDR notes

Shelved design idea for an online FDR *validation* probe using a
deterministic "goal" engine. Not applicable to the current substrate;
worth revisiting once RFC-004 §7 non-Markovian or active-drive
substrates land.

## The idea

Translation of a Maya predictive-VFX pattern: alongside the main
stochastic Langevin engine, run a second "goal" engine on the same
substrate with a **different solver** — specifically, deterministic
overdamped gradient descent, zero noise, same γ. Both start at `v(t)`.

Measure `δ = v_main − v_goal` over a short window. Project onto Hessian
eigenvectors `u_i` with eigenvalues `λ_i`. Compare measured per-mode
variance to the harmonic-well prediction:

```
ratio_i = Var(δ_i) / (k_BT / λ_i)
```

- `ratio ≈ 1` — equilibrium, equipartition holds, FDR valid.
- `ratio ≫ 1` — excess fluctuation, non-equilibrium, FDR violated.
- `ratio ≪ 1` — window too short for mode `i` to equilibrate.

## Why it is on the shelf

Three specific reasons it does not help for the current work.

1. **The C-vs-K gap it claims to fill is already closed by the
   topological classifier on our scenarios.** At Session-A conflict
   `v = (1, 0)`, the Hessian is `diag(120, 90)` (strictly positive
   definite), but `E ≈ 33.75 > E_s = 3.0`, so the rule `E > E_s ⇒ K`
   catches it. No residual "H ≻ 0 AND E < E_c AND actually K" case
   exists in our four scenarios.

2. **It misidentifies the signal.** In our conflict scenario, both
   engines start at the compromise point where `∇E = 0` by symmetry;
   the goal stays put, main orbits with thermal noise, and `Var(δ_i) →
   k_BT / λ_i` — ratio ≈ 1, same as committed. The narrative
   "goal slides into a competing well while main gets kicked across
   the saddle" assumes K ⇔ saddle geometry; our K is a high-energy
   locally-stable compromise, not a saddle.

3. **The streaming-τ gate already covers the release-trigger need.**
   25× separation in trip rate between pinned and mobile regimes on
   the four Session-A scenarios. FDR measurements release from there;
   `classify_phase_dynamical` separates C from K via the measured slope.

## When to revisit

What `Var(δ_i) / (k_BT / λ_i)` actually measures is whether the
fluctuation-dissipation relation `⟨δ²⟩ = k_BT / λ` holds locally.
That is *equipartition / FDR validity*, not regime classification.
Useful when:

- **Active driving / persistent currents.** Substrates with
  `D_active ≫ D_thermal` produce excess variance in soft modes.
  The ratio flags this directly.
- **Memory-kernel dynamics.** RFC-004 §7 non-Markovian substrates
  violate simple equipartition; the per-mode ratio reveals which
  modes have memory-kernel corrections.
- **Multi-temperature substrates.** If parts of the substrate see
  a different effective temperature (e.g., different coupling to
  an external bath), per-mode ratios decouple.

In all three cases the probe is a **diagnostic**, not a classifier.
It answers "is my FDR assumption intact here?" which is a different
question from "what phase am I in?"

## Rough implementation sketch

```python
class GoalEngine:
    """Deterministic overdamped companion. Zero noise."""
    def __init__(self, v_start, gamma, dt):
        self.v = v_start.copy()
        self.gamma = gamma
        self.dt = dt

    def step(self, grad_fn):
        self.v = self.v - (grad_fn(self.v) / self.gamma) * self.dt
        return self.v


def modal_fdr_validity(v_main_hist, v_goal_hist, H, kT):
    """
    Returns per-eigenmode ratio Var(δ_i) / (kT / λ_i).
    Ratios far from 1.0 flag FDR violation on that mode.
    """
    lambdas, U = np.linalg.eigh(H)
    delta = np.asarray(v_main_hist) - np.asarray(v_goal_hist)
    delta_modes = delta @ U  # project onto eigenbasis
    var_meas = np.var(delta_modes, axis=0)
    var_pred = kT / np.maximum(lambdas, 1e-12)
    return var_meas / var_pred
```

Cost in the pinned regime: one extra `∇E(v_goal)` per step — the goal
diverges from the main engine after step one, so no caching. That is
**2× gradient cost per pinned step**, not "free" as sometimes claimed.
Bearable for Langevin where `∇E` is `O(d)`–`O(d²)`, but not literally
free.

## Relationship to the shelved `mobility_detector`

Both the goal engine and the shelved `mobility_detector` are
reference-trajectory probes. `mobility_detector` uses a *linear drift
extrapolation* (one-step prediction); the goal engine uses a
*full deterministic evolution* (multi-step). The latter is strictly
more expressive but strictly more expensive. If we ever revisit this
area, the two share infrastructure: ring buffer of positions,
eigenbasis projection, per-mode variance accumulation.

## Credit

Idea: user pattern-matching from Maya nParticle goals with
differently-solved reference particles. Physics write-up and
modal-FDR formulation: Kimi.

---

*Status: shelved 2026-04-24. Not applicable to Markovian Session-A
scenarios. Revisit when a non-equilibrium or non-Markovian substrate
lands.*
