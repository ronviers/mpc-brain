"""effector pack — standalone sanity tests.

Runs in under a second. Exercises attach, event accumulation, commit
emission, and the cluster-filter API.

Invocation:

    python -m mpc_packs.effector.test_pack
"""

from __future__ import annotations

import numpy as np

from mpc_kernel.rfc001.bus import EventBus
from mpc_kernel.rfc001.events import (
    BudgetResetEvent,
    LandauerEvent,
    PhaseTransitionEvent,
)
from mpc_kernel.rfc001.phase import Phase
from mpc_packs.effector import Effector, EffectorEvent


def test_non_c_transition_does_nothing():
    """Non-C phase transitions must not emit an EffectorEvent."""
    bus = EventBus()
    eff = Effector().attach(bus)
    eff.register_cluster("A", lambda_avg=1.0)
    bus.emit(
        PhaseTransitionEvent(
            from_phase=Phase.C, to_phase=Phase.K,
            position=np.array([1.0, 0.0]),
            timestamp=0.5, cluster_id="A", energy=2.0,
        )
    )
    assert eff.effector_events() == []


def test_c_transition_emits_effector_event():
    """PhaseTransitionEvent.to_phase == Phase.C triggers an EffectorEvent."""
    bus = EventBus()
    eff = Effector().attach(bus)
    eff.register_cluster("A", lambda_avg=0.5)

    # Seed a reset at origin, then emit a LandauerEvent, then commit.
    bus.emit(
        BudgetResetEvent(
            cluster_id="A", position=np.zeros(2),
            timestamp=0.0, info_cost=1.0,
        )
    )
    bus.emit(LandauerEvent(cluster_id="A", info_content=2.0, kT=1.0))
    bus.emit(
        PhaseTransitionEvent(
            from_phase=Phase.S, to_phase=Phase.C,
            position=np.array([3.0, 4.0]),  # ‖v‖² = 25
            timestamp=0.7, cluster_id="A", energy=0.1,
        )
    )

    events = eff.effector_events("A")
    assert len(events) == 1
    e = events[0]
    assert isinstance(e, EffectorEvent)
    assert e.cluster_id == "A"
    assert e.energy_at_c == 0.1
    assert e.landauer_cost == 2.0               # info_content=2 × kT=1
    assert e.work_estimate == 25.0 * 0.5        # ‖v‖² · λ_avg
    assert abs(e.total_cost - (0.1 + 2.0 + 12.5)) < 1e-9
    return e


def test_landauer_accumulator_resets_after_commit():
    """The Landauer accumulator must reset to 0 after each commit emission,
    so the next commit starts fresh."""
    bus = EventBus()
    eff = Effector().attach(bus)
    eff.register_cluster("A", lambda_avg=1.0)

    bus.emit(LandauerEvent(cluster_id="A", info_content=3.0))
    bus.emit(PhaseTransitionEvent(
        from_phase=Phase.S, to_phase=Phase.C,
        position=np.zeros(2), timestamp=0.1, cluster_id="A", energy=0.0,
    ))
    bus.emit(PhaseTransitionEvent(
        from_phase=Phase.S, to_phase=Phase.C,
        position=np.zeros(2), timestamp=0.2, cluster_id="A", energy=0.0,
    ))

    events = eff.effector_events()
    assert events[0].landauer_cost == 3.0
    assert events[1].landauer_cost == 0.0


def test_cluster_filter():
    """effector_events(cluster_id=...) filters by cluster; bare call
    returns all."""
    bus = EventBus()
    eff = Effector().attach(bus)
    eff.register_cluster("A", lambda_avg=1.0)
    eff.register_cluster("B", lambda_avg=1.0)

    for cid in ("A", "B", "A"):
        bus.emit(PhaseTransitionEvent(
            from_phase=Phase.S, to_phase=Phase.C,
            position=np.zeros(2), timestamp=0.0, cluster_id=cid, energy=0.0,
        ))
    assert len(eff.effector_events()) == 3
    assert len(eff.effector_events("A")) == 2
    assert len(eff.effector_events("B")) == 1


if __name__ == "__main__":
    print("effector pack — sanity tests")
    print("=" * 62)

    test_non_c_transition_does_nothing()
    print("[1] non-C transition        no emit   OK")

    e = test_c_transition_emits_effector_event()
    print(
        f"[2] C transition emits      "
        f"total_cost={e.total_cost:.3f} "
        f"(energy=0.1 + landauer=2.0 + work=12.5)   OK"
    )

    test_landauer_accumulator_resets_after_commit()
    print("[3] landauer accumulator    resets after commit   OK")

    test_cluster_filter()
    print("[4] cluster filter          A=2, B=1, all=3   OK")

    print("\nAll tests pass.")
