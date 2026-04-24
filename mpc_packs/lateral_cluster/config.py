"""lateral_cluster pack configuration (RFC-002 §3.2).

Plug point: AutoCluster subclass (RFC-001 §4.3 extension).

Declared dependencies:
    - mpc_kernel.rfc001.events:EventBus
    - mpc_kernel.rfc001.phase:Phase
    - mpc_packs.auto_cluster:AutoCluster            (parent class)
    - mpc_packs.decaying_substrate:DecayingSubstrate (substrate swap)
    - mpc_packs.observation_socket:ObservationSocket (optional)

Declared mutations:
    - self.sub, self.ops.sub (replaced with DecayingSubstrate at init)
    - self._centres, self._socket, self._lateral_scale (private state)
    - inherited: self.engines, self._r_streak (from AutoCluster)
"""

DECLARED_DEPENDENCIES = [
    "mpc_kernel.rfc001.events:EventBus",
    "mpc_kernel.rfc001.phase:Phase",
    "mpc_packs.auto_cluster:AutoCluster",
    "mpc_packs.decaying_substrate:DecayingSubstrate",
    "mpc_packs.observation_socket:ObservationSocket",
]

DECLARED_MUTATIONS = [
    "self.sub",
    "self.ops.sub",
    "self._centres",
    "self._socket",
    "self._lateral_scale",
]
