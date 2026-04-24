# lateral_cluster

`AutoCluster` subclass with the AMEND-003 lateral maintenance field.
Engines sharing a nearest-well attract each other to preserve
intra-hypothesis coherence. Substrate is always `DecayingSubstrate`
so frustrations decay in time (AMEND-001).

Carved from the Session-3 monolith.

## Lateral force (s-state only)

```
F_lateral(i) = Σ_{j≠i, j∈s-state, same well}  w_ij · (v_j − v_i)
w_ij         = exp(−ε_ij / k_BT),  k_BT = 1.0
```

Scaled by `lateral_scale / max(n_same − 1, 1)` so the sum is O(1)
regardless of cluster size. Non-s-state engines get zero force
(RFC-001 §3.4 is intact).

Engines assigned to *different* wells do not exchange lateral forces
— cross-well coupling is `cross_cluster_compatibility()`, not this.

## API

```python
from mpc_packs.lateral_cluster import LateralCluster

cluster = LateralCluster(
    dim=8, E_star=10.0, max_engines=16, bus=bus,
    tau_base=50.0, lateral_scale=0.02,
    socket=my_observation_socket,   # optional
)
cluster.load(
    constraints={"A": fn_A, "B": fn_B},
    stiffnesses={"A": 0.5, "B": 0.5},
    centres={"A": center_A, "B": center_B},   # speeds up nearest-well
)
for _ in range(200):
    cluster.step()   # flushes socket, applies lateral forces, self-regulates
```

## Declared dependencies

- `numpy`
- `mpc_kernel.rfc001.events.EventBus`
- `mpc_kernel.rfc001.phase.Phase`
- `mpc_packs.auto_cluster.AutoCluster` (parent class)
- `mpc_packs.decaying_substrate.DecayingSubstrate` (substrate swap)
- `mpc_packs.observation_socket.ObservationSocket` (optional)

## Declared mutations

- `self.sub` / `self.ops.sub` — replaced with `DecayingSubstrate` at
  construction.
- `self._centres`, `self._socket`, `self._lateral_scale` — private state.
- Inherited: `self.engines`, `self._r_streak` (AutoCluster).

## Provenance

Verbatim port from `experiments/historical/mpc_session3.py`
lines 87–267.
