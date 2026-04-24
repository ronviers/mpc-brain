"""llm_encoder pack — sanity tests.

Exercises the fallback path end-to-end (no API key required).

Invocation:

    python -m mpc_packs.llm_encoder.test_pack
"""

from __future__ import annotations

import numpy as np

from mpc_packs.llm_encoder import LLMConstraintEncoder


def test_fallback_no_api_key():
    """With no API key, encoder must use the deterministic fallback."""
    enc = LLMConstraintEncoder(dim=8, api_key="")
    assert enc._use_llm is False
    fn = enc.encode("any arbitrary proposition")
    assert callable(fn)
    val = fn(np.zeros(8))
    assert val >= 0
    return enc


def test_cache_reuse():
    """Repeated encode() for the same proposition returns the same
    cached callable."""
    enc = LLMConstraintEncoder(dim=4, api_key="")
    fn1 = enc.encode("test")
    fn2 = enc.encode("test")
    assert fn1 is fn2


def test_demo_proposition_map():
    """The hello-world propositions resolve to specific demo centres
    with non-trivial structure."""
    enc = LLMConstraintEncoder(dim=32, api_key="")
    fn_p1 = enc.encode("the object is spherical and smooth")
    # P1's centre is [2.0, 1.5, 1.0, 0.5, 0, ...]; so fn at origin is
    # sum(c^2) = 4 + 2.25 + 1 + 0.25 = 7.5.
    val = fn_p1(np.zeros(32))
    assert abs(val - 7.5) < 1e-9, f"expected 7.5, got {val}"


def test_word_hash_determinism():
    """Unknown propositions fall through to word-hash; same input ->
    same centre across encoder instances."""
    e1 = LLMConstraintEncoder(dim=4, api_key="")
    e2 = LLMConstraintEncoder(dim=4, api_key="")
    c1 = e1._resolve_center("foo bar baz")
    c2 = e2._resolve_center("foo bar baz")
    assert np.allclose(c1, c2)


if __name__ == "__main__":
    print("llm_encoder pack — sanity tests")
    print("=" * 62)

    enc = test_fallback_no_api_key()
    print(f"[1] fallback w/o API key    use_llm={enc._use_llm}   OK")

    test_cache_reuse()
    print("[2] cache reuse             same callable on repeat   OK")

    test_demo_proposition_map()
    print("[3] demo-proposition map    P1 fn(0)=7.5 as designed   OK")

    test_word_hash_determinism()
    print("[4] word-hash determinism   same input -> same centre   OK")

    print("\nAll tests pass.")
