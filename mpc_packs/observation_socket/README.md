# observation_socket

AMEND-004 ObservationSocket family: the abstract `ObservationSocket`
contract, the `ConstraintSpec` return type, and `AnthropicSocket` —
an Anthropic-API-backed concrete implementation with a deterministic
word-hash fallback.

Carved from the Session-3 monolith.

## RFC-001 §7 contract

ObservationSocket implementations hold **neither Substrate nor Bus**.
They translate natural-language propositions into `ConstraintSpec`
objects that the caller feeds into a cluster via `.load()`. No event
subscription, no brain-side method calls.

## Structure

```
ObservationSocket           abstract base (observe, flush, connect,
                             register_fallback)
    ↓
AnthropicSocket             Anthropic Messages API (this pack)
Z3SymbolicSocket            Z3 SMT solver (mpc_packs.z3_socket — separate pack)
```

## AnthropicSocket

```python
from mpc_packs.observation_socket import AnthropicSocket

sock = AnthropicSocket(dim=32)
sock.connect()   # reads ANTHROPIC_API_KEY env if no kwarg

spec = sock.observe("the object is spherical and smooth")
# spec.fn: Callable[[np.ndarray], float], fn(v) >= 0
# spec.lambda_: 1.0 · strength
# spec.label: "the_object_is_spherical_and_smooth"
# spec.modality: "text"

specs = sock.flush()   # drain the buffer
```

Connected → calls the Anthropic API with a system prompt asking for
a Python `fn(v)` that returns `>= 0` and is zero at exactly one point.
Fallback → deterministic word-hash quadratic (MD5-seeded normalised
random vector per word, averaged into a centre).

## Declared dependencies

- `numpy`
- `anthropic` (optional — AnthropicSocket falls back to word-hash if
  the SDK or `ANTHROPIC_API_KEY` is missing)

## Declared mutations

None. Pure producer of `ConstraintSpec` values, buffered in
`self._buffer` until `flush()` drains it.

## Provenance

Verbatim port from `experiments/historical/mpc_session3.py`
lines 273–444, with the system-prompt template inlined (was
`LLMConstraintEncoder._SYSTEM_TEMPLATE`; kept as a constant here so
this pack has no dependency on the LLM encoder module).
