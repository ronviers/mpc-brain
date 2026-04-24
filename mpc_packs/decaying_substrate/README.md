# decaying_substrate

JAXSubstrate subclass with a temporal frustration decay cache
(AMEND-001). Edges in the pairwise-frustration graph decay
exponentially in time; decayed edges drop out of the active graph,
so `MPCCluster.separation_bound()` reports a growing `N_max` as
edges decay.

**Status:** first-class pack (Session 8 carve-out). Previously a
transitional shim over `mpc_session3.DecayingSubstrate`; now the
canonical implementation. `mpc_session3.DecayingSubstrate` re-exports
from here.

## Decay law

Per edge `(i, j)`:

```
ε_ij(t+1) = ε_ij(t) · exp(-1 / τ_ij)
τ_ij      = tau_base / min(λ_i, λ_j)
```

Edges falling below `epsilon_floor` are removed from the active
frustration graph. Constraints themselves stay registered.

## API

```python
from mpc_packs.decaying_substrate import DecayingSubstrate

sub = DecayingSubstrate(dim=8, tau_base=100.0, epsilon_floor=1e-4)
sub.register("A", fn_A, lam=0.5)
sub.register("B", fn_B, lam=0.5)

# Per step:
sub.decay_step()          # advance one decay tick
sub.ping("A", "B", 0.5)   # re-stamp a specific edge
```

## Declared dependencies

- `numpy`
- `mpc_engine_rfc001.ConstraintHandle`
- `mpc_packs.jax_substrate.JAXSubstrate` (parent class)

## Declared mutations

- `self._decay_cache`, `self._initial_eps`, `self._uid_to_pid`,
  `self._active_pairs` — internal per-edge decay state.

## Provenance

Verbatim port from `experiments/historical/mpc_session3.py`
lines 77–230.
