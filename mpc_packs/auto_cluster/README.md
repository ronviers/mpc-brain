# auto_cluster

Self-organising `MPCCluster` subclass. Grows and shrinks its engine
population based on the dominant cluster phase, per RFC-001 §4.3.
Uses `JAXSubstrate` for gradient/hessian when JAX is available.

Carved from the Session-2 monolith.

## Self-regulation rules

Applied on every `step()`:

| `dominant_phase` | Action |
|---|---|
| `r` (reset) | do nothing |
| `s` (suspended), `count_s < separation_bound` | spawn engine (up to `max_engines`) |
| `k` (conflict) | `shed_load(0.3)` |

Additionally: any engine in the r-state for ≥ 50 consecutive steps is
culled (at least one engine is always retained).

## API

```python
from mpc_kernel.rfc001.bus import EventBus
from mpc_packs.auto_cluster import AutoCluster

bus = EventBus()
cluster = AutoCluster(dim=8, E_star=10.0, max_engines=16, bus=bus)

cluster.load({
    "A": lambda v: float(np.sum((v - cA) ** 2)),
    "B": lambda v: float(np.sum((v - cB) ** 2)),
}, stiffnesses={"A": 0.5, "B": 0.5})

for _ in range(200):
    cluster.step()
print(cluster.population_report())
```

## Declared dependencies

- `numpy`, `uuid`
- `mpc_engine_rfc001.MPCCluster` (kernel base)
- `mpc_kernel.rfc001.phase.Phase` (kernel enum)
- `mpc_packs.jax_substrate.JAXSubstrate` (optional, falls back to base
  `Substrate` if JAX is unavailable)

## Declared mutations

- `self.engines` — spawn / cull engine population.
- `self._r_streak` — per-engine r-state step counter.
- `self.sub`, `self.ops.sub` — replaced with a JAXSubstrate at
  construction (before any engine is added) so every engine receives
  the JAX-enhanced substrate reference.

## Provenance

Verbatim port from `experiments/historical/mpc_session2.py` lines
368–473. The historical module now re-exports from this pack.
