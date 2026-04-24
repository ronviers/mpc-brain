"""persistence_substrate pack configuration (RFC-002 §3.2).

Plug point: SubstrateExtension (PersistenceSubstrate) +
LateralCluster-subclass (PersistenceCluster).
"""

DECLARED_DEPENDENCIES = [
    "mpc_kernel.rfc001.events:EventBus",
    "mpc_kernel.rfc001.events:PhaseTransitionEvent",
    "mpc_kernel.rfc001.phase:Phase",
    "mpc_packs.decaying_substrate:DecayingSubstrate",
    "mpc_packs.lateral_cluster:LateralCluster",
    "mpc_packs.observation_socket:ObservationSocket",
    "mpc_session4:InstrumentedEngine",
]

DECLARED_MUTATIONS = [
    "self._traversal",
    "self._total_traversals",
    "self._original_eps",
    "self.sub",
    "self.ops.sub",
    "self.engines",
    "self._prev_pids",
]
