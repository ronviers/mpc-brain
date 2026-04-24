"""effector pack configuration (RFC-002 §3.2).

Declared dependencies:
    - mpc_kernel.rfc001.events.EventBus, PhaseTransitionEvent,
      LandauerEvent, BudgetResetEvent
    - mpc_kernel.rfc001.phase.Phase

Declared mutations: none. The pack is measurement-layer (RFC-001 §7);
it subscribes to events and accumulates per-cluster state in private
dicts.
"""

DECLARED_DEPENDENCIES = [
    "mpc_kernel.rfc001.events:EventBus",
    "mpc_kernel.rfc001.events:PhaseTransitionEvent",
    "mpc_kernel.rfc001.events:LandauerEvent",
    "mpc_kernel.rfc001.events:BudgetResetEvent",
    "mpc_kernel.rfc001.phase:Phase",
]

DECLARED_MUTATIONS: list = []
