"""jax_substrate pack — sanity tests.

Runs in under a second. Exercises the RFC-001 §4.1 interface on a
simple quadratic constraint and confirms numerical agreement between
the JAX path and the finite-difference path.

Invocation:

    python -m mpc_packs.jax_substrate.test_pack
"""

from __future__ import annotations

import numpy as np

from mpc_engine_rfc001 import Substrate
from mpc_packs.jax_substrate import JAX_AVAILABLE, JAXSubstrate


def test_constructor_and_registration():
    """Construct, register a constraint, check energy matches finite-diff."""
    sub = JAXSubstrate(dim=4, E_c=0.5, E_s=2.0)
    sub.register("well", lambda v: np.sum(v * v), lam=0.3)
    v = np.array([0.5, -0.5, 0.25, -0.25])
    # E = 0.3 * (0.25 + 0.25 + 0.0625 + 0.0625) = 0.3 * 0.625 = 0.1875
    assert abs(sub.energy(v) - 0.1875) < 1e-9
    return sub


def test_gradient_matches_finite_difference():
    """JAXSubstrate.gradient() must numerically agree with base
    Substrate's finite-difference gradient on the same constraint set."""
    sub_jax = JAXSubstrate(dim=4)
    sub_fd = Substrate(dim=4)
    fn = lambda v: float(np.sum(v * v))
    sub_jax.register("q", fn, lam=0.5)
    sub_fd.register("q", fn, lam=0.5)
    v = np.array([0.3, -0.7, 0.1, 0.0])
    g_jax = sub_jax.gradient(v)
    g_fd = sub_fd.gradient(v)
    assert np.allclose(g_jax, g_fd, atol=1e-4), (
        f"gradient disagreement: jax={g_jax}, fd={g_fd}"
    )


def test_version_bump_triggers_recompile():
    """register / deregister / update_lambda must each bump the
    constraint_version so the JAX closure is rebuilt."""
    sub = JAXSubstrate(dim=3)
    v0 = sub._constraint_version
    h = sub.register("a", lambda v: float(np.sum(v * v)), lam=0.5)
    assert sub._constraint_version == v0 + 1
    sub.update_lambda(h, 0.7)
    assert sub._constraint_version == v0 + 2
    sub.deregister(h)
    assert sub._constraint_version == v0 + 3


if __name__ == "__main__":
    print("jax_substrate pack — sanity tests")
    print("=" * 62)
    print(f"JAX_AVAILABLE = {JAX_AVAILABLE}   "
          f"(finite-difference fallback {'not engaged' if JAX_AVAILABLE else 'ENGAGED'})")

    sub = test_constructor_and_registration()
    print(f"[1] constructor + register  E(v)=0.1875 as expected   OK")

    test_gradient_matches_finite_difference()
    print(f"[2] gradient vs finite-diff agreement within 1e-4   OK")

    test_version_bump_triggers_recompile()
    print(f"[3] version bumps on register / update_lambda / deregister   OK")

    print("\nAll tests pass.")
