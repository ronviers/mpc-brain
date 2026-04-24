"""jax_substrate pack — exact-derivative Substrate via JAX.

Overrides `gradient()` and `hessian()` on the kernel's `Substrate` to
use `jax.grad` / `jax.hessian`. On-the-fly recompilation when the
registered constraint set changes (register / deregister /
update_lambda each bump `_constraint_version`). Transparent
finite-difference fallback when JAX is not available or a trace fails.

RFC-001 §4.1 compliance: the public interface is unchanged. Callers
that use `Substrate.gradient(v)` / `Substrate.hessian(v)` get the same
results; only the numerical method changes.
"""

from __future__ import annotations

import numpy as np

from mpc_engine_rfc001 import Substrate

# ── JAX availability ────────────────────────────────────────────────────────

try:
    import jax
    import jax.numpy as jnp
    jax.config.update("jax_enable_x64", True)
    JAX_AVAILABLE = True
except ImportError:
    JAX_AVAILABLE = False
    jax = None        # sentinel; only referenced under `if JAX_AVAILABLE:`
    jnp = None


class JAXSubstrate(Substrate):
    """RFC-001 §4.1-conforming Substrate using JAX exact derivatives.

    Overrides `gradient()` and `hessian()` to use `jax.grad` / `jax.hessian`.
    All other methods are inherited unchanged.

    Fallback: if JAX is unavailable or a jit'd trace fails, `_jax_ok` is
    set to False and finite-difference code runs transparently from that
    point on (no re-attempts).

    Version protocol: `register`, `deregister`, and `update_lambda` each
    increment `_constraint_version`. `_ensure_compiled()` recompiles when
    the version advances, baking the current stiffness values into the
    XLA computation — so stiffness updates are never silently stale.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._jax_ok = JAX_AVAILABLE
        self._constraint_version = 0
        self._compiled_version = -1
        self._jax_grad_fn = None
        self._jax_hess_fn = None

    # ── RFC-001 §4.1 interface — unchanged signatures ──────────────────────

    def register(self, proposition_id, fn, lam=1.0):
        h = super().register(proposition_id, fn, lam)
        self._constraint_version += 1
        return h

    def deregister(self, handle):
        super().deregister(handle)
        self._constraint_version += 1

    def update_lambda(self, handle, lam):
        # Stiffness is baked into XLA at compile time — must recompile.
        super().update_lambda(handle, lam)
        self._constraint_version += 1

    def gradient(self, v):
        """Exact gradient via jax.grad; falls back to FD on any failure."""
        if self._jax_ok:
            try:
                return self._jax_gradient(v)
            except Exception:
                self._jax_ok = False
        return super().gradient(v)

    def hessian(self, v):
        """Exact Hessian via jax.hessian; symmetric by construction."""
        if self._jax_ok:
            try:
                return self._jax_hessian(v)
            except Exception:
                self._jax_ok = False
        return super().hessian(v)

    # ── Internal ───────────────────────────────────────────────────────────

    def _ensure_compiled(self):
        if self._compiled_version == self._constraint_version:
            return
        if not self._constraints:
            self._jax_grad_fn = self._jax_hess_fn = None
            self._compiled_version = self._constraint_version
            return
        # Snapshot stiffness values at compile time.
        snapshot = [
            (fn, float(h.stiffness)) for fn, h in self._constraints.values()
        ]

        def total_energy(v_jax):
            return sum(lam * fn(v_jax) for fn, lam in snapshot)

        self._jax_grad_fn = jax.jit(jax.grad(total_energy))
        self._jax_hess_fn = jax.jit(jax.hessian(total_energy))
        self._compiled_version = self._constraint_version

    def _jax_gradient(self, v):
        self._ensure_compiled()
        if self._jax_grad_fn is None:
            return np.zeros(self.dim)
        return np.asarray(
            self._jax_grad_fn(jnp.array(v, dtype=jnp.float64)),
            dtype=np.float64,
        )

    def _jax_hessian(self, v):
        self._ensure_compiled()
        if self._jax_hess_fn is None:
            return np.zeros((self.dim, self.dim))
        return np.asarray(
            self._jax_hess_fn(jnp.array(v, dtype=jnp.float64)),
            dtype=np.float64,
        )
