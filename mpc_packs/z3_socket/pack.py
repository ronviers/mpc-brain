"""Z3SymbolicSocket — AMEND-007 normative implementation.

Spec source: SESSION-5-TASK-PROMPT-v2.md §AMEND-007.

Constructor:
    Z3SymbolicSocket(dim: int)

Public interface (all per spec):
    observe_symbolic(formula_fn, label, strength=1.0, well_width=1.0) -> ConstraintSpec
    observe(proposition, modality="text", strength=1.0)               -> ConstraintSpec
    flush()                                                            -> List[ConstraintSpec]
    connect(...)                                                       -> no-op
    register_fallback(...)                                             -> no-op

Determinism: Z3 solving is deterministic for the formulae the maze rule
library produces (axis-aligned bounds on Real vars).
"""

from __future__ import annotations

from typing import Any, Callable, List

import numpy as np
import z3

from mpc_session3 import ConstraintSpec, ObservationSocket


class Z3SymbolicSocket(ObservationSocket):
    """Symbolic constraint encoding via a Z3 solver.

    RFC-001 §7 compliance: holds neither Substrate nor Bus; produces
    ConstraintSpec records only.
    """

    def __init__(self, dim: int):
        """Allocate `dim` Z3 Real variables once; reused across observations."""
        self.dim: int = int(dim)
        self._vars: List[z3.ArithRef] = [z3.Real(f"v_{i}") for i in range(self.dim)]
        self._buffer: List[ConstraintSpec] = []

    # ── ObservationSocket interface ──────────────────────────────────────────

    def observe_symbolic(
        self,
        formula_fn: Callable[[List[z3.ArithRef]], List[z3.BoolRef]],
        label: str,
        strength: float = 1.0,
        well_width: float = 1.0,
    ) -> ConstraintSpec:
        """Solve `formula_fn(vars)` conjuncts; build a quadratic well around
        the satisfying point. Unsat branch emits a flat-zero fn.
        """
        solver = z3.Solver()
        try:
            conjuncts = formula_fn(self._vars)
            for c in conjuncts:
                solver.add(c)
            check = solver.check()
        except Exception:
            spec = ConstraintSpec(
                fn=_flat_zero,
                lambda_=float(strength),
                label=str(label),
                modality="symbolic_unsat",
            )
            self._buffer.append(spec)
            return spec

        if check != z3.sat:
            spec = ConstraintSpec(
                fn=_flat_zero,
                lambda_=float(strength),
                label=str(label),
                modality="symbolic_unsat",
            )
            self._buffer.append(spec)
            return spec

        model = solver.model()
        centre = np.zeros(self.dim, dtype=np.float64)
        for i, var in enumerate(self._vars):
            val = model.eval(var, model_completion=True)
            try:
                centre[i] = float(_rational_to_float(val))
            except Exception:
                centre[i] = 0.0

        w = float(well_width)
        c_vec = centre.copy()

        def fn(v: np.ndarray, _c=c_vec, _w=w, _d=self.dim) -> float:
            va = np.asarray(v, dtype=np.float64)
            n = min(len(va), _d)
            diff = va[:n] - _c[:n]
            return float(_w * np.sum(diff * diff))

        spec = ConstraintSpec(
            fn=fn,
            lambda_=float(strength),
            label=str(label),
            modality="symbolic",
        )
        self._buffer.append(spec)
        return spec

    def observe(
        self,
        proposition: str,
        modality: str = "text",
        strength: float = 1.0,
    ) -> ConstraintSpec:
        """Evaluate proposition string in a restricted namespace and dispatch.

        On eval failure: append flat-zero spec with modality='symbolic_eval_failed'.
        """
        try:
            result = eval(  # noqa: S307 — restricted namespace by design
                proposition,
                {"z3": z3, "v": self._vars, "__builtins__": {}},
                {},
            )
        except Exception:
            spec = ConstraintSpec(
                fn=_flat_zero,
                lambda_=float(strength),
                label=str(proposition),
                modality="symbolic_eval_failed",
            )
            self._buffer.append(spec)
            return spec

        conjuncts = result if isinstance(result, list) else [result]
        return self.observe_symbolic(
            formula_fn=lambda _vars: conjuncts,
            label=str(proposition),
            strength=strength,
        )

    def flush(self) -> List[ConstraintSpec]:
        """Return accumulated specs and clear the buffer."""
        out = list(self._buffer)
        self._buffer.clear()
        return out

    def connect(self, model_endpoint: Any = None, **kwargs: Any) -> None:
        """No-op — Z3 socket has no remote dependency."""
        return None

    def register_fallback(self, modality: str, encoder: Callable) -> None:
        """No-op — Z3 socket already emits concrete specs on all paths."""
        return None


# ── helpers ──────────────────────────────────────────────────────────────────

def _flat_zero(v: np.ndarray) -> float:
    """fn ≡ 0.0 — used by both unsat and eval-failed branches."""
    return 0.0


def _rational_to_float(val: Any) -> float:
    """Coerce a Z3 model value (RatNumRef/IntNumRef/etc.) to a Python float."""
    if hasattr(val, "as_fraction"):
        f = val.as_fraction()
        return float(f.numerator) / float(f.denominator)
    if hasattr(val, "as_decimal"):
        s = val.as_decimal(prec=30)
        if s.endswith("?"):
            s = s[:-1]
        return float(s)
    if hasattr(val, "numerator_as_long") and hasattr(val, "denominator_as_long"):
        return float(val.numerator_as_long()) / float(val.denominator_as_long())
    return float(str(val))


# ── AMEND-007 acceptance test ────────────────────────────────────────────────

def test_amend007() -> bool:
    """Seven assertions from v2 §AMEND-007 table."""
    socket = Z3SymbolicSocket(dim=4)

    socket.observe_symbolic(
        lambda v: [v[0] > 0.5, v[0] < 1.5, v[1] == 0],
        "region_A",
        strength=0.5,
    )
    specs = socket.flush()

    assert len(specs) == 1, f"#1 expected 1 spec, got {len(specs)}"
    spec = specs[0]
    assert spec.label == "region_A", f"#2 label={spec.label!r}"
    assert spec.modality == "symbolic", f"#3 modality={spec.modality!r}"
    assert abs(spec.lambda_ - 0.5) < 1e-9, f"#4 lambda_={spec.lambda_}"

    e_near = spec.fn(np.array([1.0, 0.0, 0.0, 0.0]))
    e_far = spec.fn(np.array([10.0, 10.0, 0.0, 0.0]))
    assert e_near < 0.01, f"#5 fn(near)={e_near} expected <0.01"
    assert e_far > 50.0, f"#6 fn(far)={e_far} expected >50"

    socket.observe_symbolic(
        lambda v: [v[0] > 1.0, v[0] < 0.5],
        "region_unsat",
        strength=0.5,
    )
    specs2 = socket.flush()
    assert len(specs2) == 1, f"#7a expected 1 unsat spec, got {len(specs2)}"
    u = specs2[0]
    assert u.modality == "symbolic_unsat", f"#7b modality={u.modality!r}"
    assert u.fn(np.zeros(4)) == 0.0, f"#7c fn(zeros)={u.fn(np.zeros(4))}"
    assert u.fn(np.array([100.0, -100.0, 5.5, -3.2])) == 0.0, "#7d fn(arb)!=0"

    return True


if __name__ == "__main__":
    print("AMEND-007:", "PASS" if test_amend007() else "FAIL")
