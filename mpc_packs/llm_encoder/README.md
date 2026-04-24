# llm_encoder

Natural-language → constraint-function encoder. Uses an Anthropic
Messages API primary path and a deterministic word-hash fallback, with
analytic overrides for the Session-2 hello-world demo propositions.

Carved from the Session-2 monolith.

## API

```python
from mpc_packs.llm_encoder import LLMConstraintEncoder

enc = LLMConstraintEncoder(dim=32)  # reads ANTHROPIC_API_KEY env

fn = enc.encode("the object is spherical and smooth")
# fn(v: np.ndarray) -> float, fn(v) >= 0, zero at exactly one point
```

Results are cached by proposition string on the encoder instance.

## Fallback hierarchy

1. If `ANTHROPIC_API_KEY` is set and the `anthropic` SDK is installed,
   the API path runs and its returned `fn` is used (with a sanity
   check that `fn(np.zeros(dim)) >= 0`).
2. Otherwise (or on API failure), the proposition is looked up in the
   built-in hello-world demo map and, if matched, a hand-tuned centre
   from `_DEMO_CENTERS` is used.
3. Otherwise, a deterministic word-hash quadratic: each word becomes
   an MD5-seeded normalised random vector; the centre is the averaged
   vector (renormalised).

## Declared dependencies

- `numpy`
- `anthropic` (optional — fallback runs cleanly without it)

## Declared mutations

None. Pure producer of `Callable` constraint functions. Internal
cache keyed by proposition string.

## Provenance

Verbatim port from `experiments/historical/mpc_session2.py`
lines 321–458, including the Session-2 demo centres and proposition
map.
