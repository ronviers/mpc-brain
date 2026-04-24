"""llm_encoder pack — natural-language → constraint-function encoder.

Translates natural-language propositions into callables
`fn: R^dim → float` that are non-negative and zero at exactly one point.
Primary path: Anthropic Messages API (claude-sonnet-4-6). Fallback:
deterministic word-hash quadratic encoder (plus analytic overrides for
the Session-2 hello-world demo propositions).

RFC-001 §7 contract: this is a producer of constraint functions for
the caller to feed into a `Substrate`. Holds no Substrate, no Bus, no
brain-side reference.
"""

from __future__ import annotations

import hashlib
import logging
import os
import textwrap
from typing import Callable, Dict, Optional

import numpy as np

# ── Anthropic SDK availability ──────────────────────────────────────────────

try:
    import anthropic as _anthropic_mod
    _ANTHROPIC_LIB = True
except ImportError:
    _ANTHROPIC_LIB = False
    _anthropic_mod = None

log = logging.getLogger(__name__)


# ── Session-2 hello-world demo fallback centres ─────────────────────────────
#
# Analytic overrides for the three propositions of the Session-2
# hello-world demo, used by _resolve_center when the API is absent
# (DEVIATE-001). Design: P1 and P2 are maximally incompatible
# (orthogonal wells); P3 reinforces P2's subspace so the system commits
# to P2 after P3 is added.

_DEMO_DIM = 32


def _build_demo_centers(dim: int) -> Dict[str, np.ndarray]:
    c1 = np.zeros(dim); c1[0:4] = [2.0, 1.5, 1.0, 0.5]
    c2 = np.zeros(dim); c2[4:8] = [2.0, 1.5, 1.0, 0.5]
    c3 = np.zeros(dim); c3[4:8] = [1.2, 0.9, 0.6, 0.3]; c3[8] = 0.3
    return {"P1": c1, "P2": c2, "P3": c3}


_DEMO_CENTERS: Dict[str, np.ndarray] = _build_demo_centers(_DEMO_DIM)

_DEMO_PROPOSITION_MAP: Dict[str, str] = {
    "the object is spherical and smooth": "P1",
    "the object has sharp corners and flat faces": "P2",
    "the object fits in one hand and is used for writing": "P3",
}


# ── Helpers ─────────────────────────────────────────────────────────────────


def _make_quadratic_constraint(center: np.ndarray) -> Callable[[np.ndarray], float]:
    c = np.asarray(center, dtype=np.float64)
    def fn(v):
        diff = np.asarray(v, dtype=np.float64) - c
        return float(np.sum(diff * diff))
    return fn


# ── LLMConstraintEncoder ────────────────────────────────────────────────────


class LLMConstraintEncoder:
    """Natural-language → constraint function translator.

    Primary: Anthropic Messages API (`claude-sonnet-4-6`). Key from
    `ANTHROPIC_API_KEY` env or the `api_key` ctor kwarg.
    Fallback: deterministic word-hash quadratic encoder, with analytic
    overrides for the Session-2 hello-world demo propositions.

    `encode(proposition)` returns a `Callable[[np.ndarray], float]`;
    results are cached by proposition string.
    """

    _SYSTEM_TEMPLATE = textwrap.dedent("""\
        You are a constraint function generator for a physical inference system
        operating over configuration space R^{dim}.

        Given a natural-language proposition, output ONLY a Python function
        named fn with signature: def fn(v): ...
        where v is a numpy array of length {dim}.

        Requirements:
          fn(v) >= 0 for all v
          fn(v) = 0 at exactly one point
          Use ONLY numpy (imported as np). No float(), int(), list() on traced values.
          No imports. No I/O. No markdown.

        Example for "position at origin":
            def fn(v):
                return np.sum(v ** 2)
    """)

    def __init__(self, dim: int, api_key: Optional[str] = None):
        self.dim = dim
        self._cache: Dict[str, Callable] = {}
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._use_llm = bool(self._api_key) and _ANTHROPIC_LIB
        self._client = (
            _anthropic_mod.Anthropic(api_key=self._api_key)
            if self._use_llm else None
        )

    def encode(self, proposition: str) -> Callable[[np.ndarray], float]:
        """Encode proposition → constraint function. Cached by proposition string."""
        if proposition in self._cache:
            return self._cache[proposition]
        fn = (
            self._encode_llm(proposition)
            if self._use_llm
            else self._encode_fallback(proposition)
        )
        self._cache[proposition] = fn
        return fn

    # ── LLM path ────────────────────────────────────────────────────────────

    def _encode_llm(self, proposition: str) -> Callable[[np.ndarray], float]:
        system = self._SYSTEM_TEMPLATE.replace("{dim}", str(self.dim))
        try:
            resp = self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=512,
                system=system,
                messages=[{"role": "user", "content": proposition}],
            )
            code = resp.content[0].text.strip()
            fn = self._safe_eval(code)
            if fn is not None:
                v_test = fn(np.zeros(self.dim))
                assert float(np.asarray(v_test)) >= 0
                return fn
        except Exception as exc:
            log.warning(
                f"LLM encode failed for '{proposition[:40]}': {exc}"
            )
        return self._encode_fallback(proposition)

    def _safe_eval(self, code: str) -> Optional[Callable]:
        if "```" in code:
            code = "\n".join(
                ln for ln in code.splitlines()
                if not ln.strip().startswith("```")
            )
        ns = {"np": np, "__builtins__": {}}
        try:
            exec(code, ns)   # noqa: S102
            fn = ns.get("fn")
            return fn if callable(fn) else None
        except Exception as exc:
            log.warning(f"safe_eval failed: {exc}")
            return None

    # ── Fallback path ───────────────────────────────────────────────────────

    def _encode_fallback(self, proposition: str) -> Callable[[np.ndarray], float]:
        center = self._resolve_center(proposition)
        return _make_quadratic_constraint(center)

    def _resolve_center(self, proposition: str) -> np.ndarray:
        key = proposition.strip().lower()
        label = _DEMO_PROPOSITION_MAP.get(key)
        if label:
            raw = _DEMO_CENTERS[label]
            center = np.zeros(self.dim)
            n = min(self.dim, len(raw))
            center[:n] = raw[:n]
            return center
        return self._word_hash_center(proposition)

    def _word_hash_center(self, proposition: str) -> np.ndarray:
        words = proposition.lower().split()
        if not words:
            return np.zeros(self.dim)
        vecs = []
        for word in words:
            seed = int(hashlib.md5(word.encode()).hexdigest()[:8], 16) % (2 ** 31)
            rng = np.random.default_rng(seed)
            vec = rng.standard_normal(self.dim)
            vec /= np.linalg.norm(vec) + 1e-9
            vecs.append(vec)
        center = np.mean(vecs, axis=0)
        norm = np.linalg.norm(center)
        return center / norm if norm > 1e-9 else center
