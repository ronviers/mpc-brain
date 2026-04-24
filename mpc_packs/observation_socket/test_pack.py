"""observation_socket pack — sanity tests.

Exercises ConstraintSpec, AnthropicSocket fallback path (no API), and
the abstract base's not-implemented contract.

Invocation:

    python -m mpc_packs.observation_socket.test_pack
"""

from __future__ import annotations

import numpy as np

from mpc_packs.observation_socket import (
    AnthropicSocket,
    ConstraintSpec,
    ObservationSocket,
    SYSTEM_TEMPLATE,
)


def test_abstract_base_raises_notimplemented():
    """ObservationSocket is abstract; its methods must raise."""
    base = ObservationSocket()
    for name in ("observe", "flush", "connect", "register_fallback"):
        try:
            if name in ("observe",):
                getattr(base, name)("x")
            elif name == "register_fallback":
                getattr(base, name)("text", lambda p, d: None)
            else:
                getattr(base, name)()
        except NotImplementedError:
            continue
        assert False, f"{name} did not raise NotImplementedError"


def test_anthropic_socket_disconnected_fallback():
    """Without an API connection, observe() uses the registered
    fallback encoder. Default fallback is the word-hash quadratic."""
    sock = AnthropicSocket(dim=4)
    # Don't connect — ensure _connected is False.
    assert sock._connected is False
    spec = sock.observe("hello world")
    assert isinstance(spec, ConstraintSpec)
    assert spec.modality == "text"
    assert spec.lambda_ == 1.0
    assert callable(spec.fn)
    v = np.zeros(4)
    val = spec.fn(v)
    assert val >= 0
    return spec


def test_flush_drains_buffer():
    sock = AnthropicSocket(dim=4)
    sock.observe("a")
    sock.observe("b")
    specs = sock.flush()
    assert len(specs) == 2
    assert sock.flush() == []   # drained


def test_register_fallback_replaces_default():
    """A caller-supplied fallback must override the default encoder."""
    sock = AnthropicSocket(dim=3)
    captured = []
    def tracking(p, d):
        captured.append((p, d))
        return lambda v: 0.0
    sock.register_fallback("text", tracking)
    sock.observe("test proposition")
    assert captured == [("test proposition", 3)]


def test_system_template_parametric():
    """SYSTEM_TEMPLATE must have the {dim} placeholder for AnthropicSocket
    to substitute in `_encode_via_api`."""
    assert "{dim}" in SYSTEM_TEMPLATE
    rendered = SYSTEM_TEMPLATE.replace("{dim}", "7")
    assert "R^7" in rendered


if __name__ == "__main__":
    print("observation_socket pack — sanity tests")
    print("=" * 62)

    test_abstract_base_raises_notimplemented()
    print("[1] abstract base           raises NotImplementedError   OK")

    spec = test_anthropic_socket_disconnected_fallback()
    print(f"[2] disconnected fallback   label={spec.label!r}   OK")

    test_flush_drains_buffer()
    print("[3] flush                   drains buffer and resets   OK")

    test_register_fallback_replaces_default()
    print("[4] register_fallback       replaces default encoder   OK")

    test_system_template_parametric()
    print("[5] SYSTEM_TEMPLATE         has {dim} placeholder   OK")

    print("\nAll tests pass.")
