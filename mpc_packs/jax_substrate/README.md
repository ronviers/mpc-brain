# jax_substrate

JAX-accelerated `Substrate` subclass. Exact derivatives via
`jax.grad` / `jax.hessian`; transparent finite-difference fallback if
JAX is unavailable or a trace fails at runtime.

Carved from the Session-2 monolith.

## What changes

Nothing in the public API. `JAXSubstrate(dim=...)` is a drop-in for
`Substrate(dim=...)`; callers that use `.energy`, `.gradient`,
`.hessian`, `.classify`, `.register` / `.deregister` /
`.update_lambda` get the same results, but `.gradient` and `.hessian`
are computed via JIT-compiled `jax.grad` / `jax.hessian` when JAX is
available.

Versioning: `register`, `deregister`, and `update_lambda` bump an
internal `_constraint_version`. The JIT closure is rebuilt when the
version advances, baking the current `stiffness` values into the XLA
computation — so stiffness updates are never silently stale.

## API

```python
from mpc_packs.jax_substrate import JAXSubstrate, JAX_AVAILABLE

sub = JAXSubstrate(dim=8, E_c=0.5, E_s=2.0)
sub.register("p1", lambda v: np.sum(v ** 2), lam=0.3)

g = sub.gradient(v)   # jax.grad path if JAX_AVAILABLE, else FD
H = sub.hessian(v)    # jax.hessian path if JAX_AVAILABLE, else FD
```

## Runtime flag

`JAX_AVAILABLE: bool` — True if `import jax` succeeded at module load
time. Used by downstream packs (e.g. `auto_cluster`) to decide whether
to construct a `JAXSubstrate` or plain `Substrate`.

## Declared dependencies

- `numpy`
- `mpc_engine_rfc001.Substrate` (kernel base)
- `jax`, `jax.numpy` — **optional**. Missing → `JAX_AVAILABLE=False` and
  the finite-difference fallback runs.

## Declared mutations

None. Only overrides `gradient` / `hessian` on the existing interface.

## Provenance

Verbatim port from `experiments/historical/mpc_session2.py` lines
85–173. The historical module now re-exports from this pack.
