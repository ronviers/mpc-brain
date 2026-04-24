"""observation_socket pack — AMEND-004 ObservationSocket family.

Defines the abstract `ObservationSocket` contract, the structured
`ConstraintSpec` return type, and `AnthropicSocket` — a concrete
socket backed by the Anthropic Messages API with a deterministic
word-hash fallback.

RFC-001 §7 contract: ObservationSocket implementations hold neither
Substrate nor EventBus. They accept natural-language propositions,
return `ConstraintSpec`s that the caller feeds into a cluster.
"""

from __future__ import annotations

import hashlib
import logging
import os
import textwrap
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

import numpy as np

# ── Anthropic SDK availability ──────────────────────────────────────────────

try:
    import anthropic as _anthropic_mod
    _ANTHROPIC_LIB = True
except ImportError:
    _ANTHROPIC_LIB = False
    _anthropic_mod = None  # sentinel

log = logging.getLogger(__name__)


# ── System-prompt template for API-backed encoders ──────────────────────────
#
# Inlined here so this pack does not depend on LLMConstraintEncoder. Both
# this pack and the LLM encoder pack (when carved) use the same template;
# if they drift they'll drift together or independently as intended —
# the template is a prompt string, not a contract.

SYSTEM_TEMPLATE = textwrap.dedent("""\
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


# ── ConstraintSpec dataclass ────────────────────────────────────────────────


@dataclass
class ConstraintSpec:
    """Structured constraint specification produced by ObservationSocket."""

    fn: Callable[[np.ndarray], float]
    lambda_: float
    label: str
    modality: str


# ── Abstract ObservationSocket ──────────────────────────────────────────────


class ObservationSocket:
    """Abstract base for AMEND-004 ObservationSocket implementations.

    Concrete subclasses (`AnthropicSocket`, `mpc_packs.z3_socket.Z3SymbolicSocket`)
    hold neither Substrate nor Bus.
    """

    def observe(
        self, proposition: str, modality: str = "text", strength: float = 1.0
    ) -> ConstraintSpec:
        raise NotImplementedError

    def flush(self) -> List[ConstraintSpec]:
        raise NotImplementedError

    def connect(self, model_endpoint=None, **kwargs):
        raise NotImplementedError

    def register_fallback(self, modality: str, encoder: Callable):
        raise NotImplementedError


# ── Word-hash fallback helper (deterministic, no external deps) ─────────────


def _make_quadratic_constraint(center: np.ndarray) -> Callable:
    c = np.asarray(center, dtype=np.float64)
    def fn(v):
        diff = np.asarray(v, dtype=np.float64) - c
        return float(np.sum(diff * diff))
    return fn


def _word_hash_quadratic(proposition: str, dim: int) -> Callable:
    """Deterministic word-hash quadratic encoder. Used as the default
    text-modality fallback when the Anthropic API is unavailable."""
    words = proposition.lower().split()
    if not words:
        return _make_quadratic_constraint(np.zeros(dim))
    vecs = []
    for word in words:
        seed = int(hashlib.md5(word.encode()).hexdigest()[:8], 16) % (2 ** 31)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(dim)
        vec /= np.linalg.norm(vec) + 1e-9
        vecs.append(vec)
    center = np.mean(vecs, axis=0)
    norm = np.linalg.norm(center)
    center = center / norm if norm > 1e-9 else center
    return _make_quadratic_constraint(center)


# ── AnthropicSocket concrete implementation ─────────────────────────────────


class AnthropicSocket(ObservationSocket):
    """AMEND-004: ObservationSocket backed by an Anthropic Messages API
    model (default: `claude-sonnet-4-6`).

    Holds neither Substrate nor Bus.

    `connect()` reads `api_key` from kwargs or the `ANTHROPIC_API_KEY`
    environment variable. Sets `_connected=True` on success, `False`
    on failure — never raises. `observe()` uses the API when connected,
    otherwise falls back to the registered fallback encoder.
    """

    _SYSTEM_TEMPLATE = SYSTEM_TEMPLATE

    def __init__(self, dim: int):
        self.dim = dim
        self._connected = False
        self._client = None
        self._buffer: List[ConstraintSpec] = []
        self._fallback: Dict[str, Callable] = {}
        # Default text fallback: deterministic word-hash quadratic.
        self.register_fallback("text", self._default_text_fallback)

    # ── ObservationSocket interface ─────────────────────────────────────────

    def connect(self, model_endpoint=None, **kwargs) -> None:
        api_key = (
            kwargs.get("api_key", "")
            or os.environ.get("ANTHROPIC_API_KEY", "")
        )
        if api_key and _ANTHROPIC_LIB:
            try:
                self._client = _anthropic_mod.Anthropic(api_key=api_key)
                self._connected = True
                log.info("AnthropicSocket: connected to Anthropic API")
            except Exception as exc:
                log.warning(f"AnthropicSocket.connect failed: {exc}")
                self._connected = False
        else:
            self._connected = False

    def observe(
        self, proposition: str, modality: str = "text", strength: float = 1.0
    ) -> ConstraintSpec:
        """Encode proposition → ConstraintSpec.

        Primary: Anthropic API. Fallback: registered encoder for modality.
        `lambda_ = strength · 1.0`.
        """
        fn: Optional[Callable] = None

        if self._connected:
            fn = self._encode_via_api(proposition)

        if fn is None:
            enc = self._fallback.get(modality) or self._fallback.get("text")
            if enc is not None:
                try:
                    fn = enc(proposition, self.dim)
                except Exception as exc:
                    log.warning(f"Fallback encoder failed: {exc}")

        if fn is None:
            fn = _make_quadratic_constraint(np.zeros(self.dim))

        label = proposition[:48].strip().replace(" ", "_").replace("'", "")
        spec = ConstraintSpec(
            fn=fn, lambda_=float(strength), label=label, modality=modality
        )
        self._buffer.append(spec)
        return spec

    def flush(self) -> List[ConstraintSpec]:
        specs = list(self._buffer)
        self._buffer.clear()
        return specs

    def register_fallback(self, modality: str, encoder: Callable) -> None:
        """encoder: `(proposition: str, dim: int) → Callable[[np.ndarray], float]`."""
        self._fallback[modality] = encoder

    # ── Internal helpers ────────────────────────────────────────────────────

    def _encode_via_api(self, proposition: str) -> Optional[Callable]:
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
                v0 = np.zeros(self.dim)
                assert float(np.asarray(fn(v0))) >= 0
                return fn
        except Exception as exc:
            log.warning(f"AnthropicSocket API encode failed: {exc}")
        return None

    def _safe_eval(self, code: str) -> Optional[Callable]:
        if "```" in code:
            code = "\n".join(
                ln for ln in code.splitlines()
                if not ln.strip().startswith("```")
            )
        ns = {"np": np, "__builtins__": {}}
        try:
            exec(code, ns)  # noqa: S102
            fn = ns.get("fn")
            return fn if callable(fn) else None
        except Exception as exc:
            log.warning(f"AnthropicSocket safe_eval failed: {exc}")
            return None

    @staticmethod
    def _default_text_fallback(proposition: str, dim: int) -> Callable:
        """Deterministic word-hash quadratic encoder."""
        return _word_hash_quadratic(proposition, dim)
