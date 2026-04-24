# mobility_detector

Cheap linear mobile-vs-pinned classifier. Per-engine companion that emits
both a boolean trip signal (`should_release()`) and a continuous tension
observable (`tension`). Not the FDR-release gate — see "Why it's shelved"
below. Retained because the signal is real, fast, and orthogonal to other
classifiers.

## The pattern

From a Maya predictive-VFX rig: linear forward/backward curves with a
wind field, an nParticle on the backward curve that drags in the field.
In MPC:

| Maya                            | MPC                                                         |
|---------------------------------|-------------------------------------------------------------|
| forward orthogonal curve        | linear drift extrapolation  `v_ghost = v − γ⁻¹ ∇E · Δt`    |
| backward orthogonal curve       | rolling recent-trajectory tail                              |
| wind field                      | local energy gradient ∇E                                    |
| nParticle drag                  | direction discrepancy `1 − cos(θ)` × min-magnitude          |

## Components

Three pure functions + one orchestrator:

1. `compute_ghost(v, grad_fn, gamma, dt)` — single-step linear drift, O(d).
2. `compute_tail(buffer, window)` — mean displacement over the window.
3. `gate_signal(ghost_delta, tail_delta, threshold, min_tail_mag)` —
   cosine-distance trip, with a magnitude filter to suppress sub-thermal
   noise.
4. `MobilityDetector` — ring buffer + per-step `observe()`. Exposes
   `should_release()` (boolean), `tension` (continuous), `trip_count`
   (cumulative), and `last_trip_step`.

## Calibration findings

Trip counts over 3000-step seeded Langevin trajectories on the four
Session-A scenarios, with `config.py` defaults (`window=50`,
`threshold=0.3`, `min_tail_factor=0.3`):

| Scenario  | Trips | Interpretation |
|-----------|-------|-----------------|
| conflict  |   0   | stiff disjoint wells pin the particle at the compromise point; per-step displacement below thermal floor; detector silent. |
| committed |   8   | stiff compatible wells; tight thermal fluctuations at the intersection minimum; detector rarely fires. |
| suspended |  81   | soft wells; thermal excursions large enough that per-window drift direction regularly disagrees with the instantaneous gradient. |
| reset     | 110   | softest potential; noise dominates drift; per-window tail direction uncorrelated with gradient. |

3+ orders of magnitude of spread. Mobile regimes fire ~100× more than
pinned ones.

## Why it's shelved

We originally scoped this as the gate for releasing expensive FDR
measurements ahead of the engine. It doesn't work for that use: on
Markovian substrates, FDR is needed *inside* the pinned regime to
separate C from K, and this detector is silent there. The semantics are
mobile-vs-pinned, not linear-approximation-valid-vs-broken.

What the detector does answer cleanly:

- **Is this engine exploring or settled?**  (Trip rate or integrated
  tension distinguishes.)
- **Resource allocation.** Settled engines have headroom for other work;
  exploring ones might warrant throttling or more compute.
- **Exploration/exploitation signalling.** Governors that want to shift
  mode can key off the tension trend.
- **Convergence heuristics.** A sustained drop in trip rate indicates
  the engine has entered a pinned state — useful for early-stop logic.

FDR-release gating moved to `mpc_packs/dynamical_gate/` (streaming-τ_A
approach). This pack remains available for consumers that want the
mobility signal directly.

## Declared dependencies

- `numpy`.

## Declared mutations

None. Pure observational pack; never writes to the substrate or emits
events.

## Invocation

```bash
python -m mpc_packs.mobility_detector.test_pack
```

Primitive checks run instantly. Four-scenario calibration takes 6–10 s;
set `MOBILITY_DETECTOR_SKIP_SCENARIOS=1` to skip.
