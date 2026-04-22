"""symbolic_forebrain pack manifest — RFC-002 §3.2 / §4.3.

declared_dependencies:
    - mpc_kernel.rfc001.events.EventBus          (kernel)
    - mpc_engine_rfc001.Network                  (kernel-defined; target
      surface for cluster resolution)
    - mpc_packs.metareasoner.Metareasoner        (same layer)
    - mpc_packs.z3_socket.Z3SymbolicSocket       (same layer)
    - mpc_session4.PersistenceCluster            (cross-pack; for type hints
      only, not for instance creation — the forebrain accepts whatever
      cluster the network provides)

declared_mutations (all and ONLY via the three routes named below):
    (a) cluster.load(constraints, stiffnesses, [centres])
          — add_proposition action.
    (b) cluster.ops.reset(handle, cluster.cluster_id) + _handles.pop(pid)
          — remove_proposition action.
    (c) cluster.local_budget = new  AND  engine.E_star = new  (per engine)
          — rebudget action.

The forebrain never writes directly to substrate state, never writes to
engine.v, and never short-circuits the bus. Every action routes through
the public cluster / ops interface.

no_modify_kernel: True
no_shadow:        True
"""

PACK_NAME = "symbolic_forebrain"
PACK_VERSION = "0.1.0"
DECLARED_DEPENDENCIES = [
    "mpc_kernel.rfc001.events:EventBus",
    "mpc_engine_rfc001:Network",
    "mpc_packs.metareasoner:Metareasoner",
    "mpc_packs.z3_socket:Z3SymbolicSocket",
]
DECLARED_MUTATIONS = [
    "cluster.load(constraints, stiffnesses[, centres])  # via Action(add_proposition)",
    "cluster.ops.reset(handle, cluster.cluster_id); cluster._handles.pop(pid)"
    "  # via Action(remove_proposition)",
    "cluster.local_budget = new; engine.E_star = new for each engine"
    "  # via Action(rebudget)",
]
NO_MODIFY_KERNEL = True
NO_SHADOW = True
