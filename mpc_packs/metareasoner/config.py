"""metareasoner pack manifest — RFC-002 §3.2 / §4.3.

declared_dependencies:
    - mpc_kernel.rfc001.events.BudgetResetEvent  (kernel-defined)
    - mpc_kernel.rfc001.events.EventBus          (kernel-defined)
    - mpc_session4.EffectorEvent                 (cross-pack; source module
      of persistence_substrate pack; see RFC-002 §3.2)

declared_mutations:
    NONE. Measurement-only. On attach(bus) the Metareasoner subscribes to
    BudgetResetEvent and EffectorEvent; handlers update only private dicts
    keyed by cluster_id. No outbound calls. Stores bus ONLY as
    _attached_bus for diagnostics.

no_modify_kernel: True
no_shadow:        True   (EventBus / BudgetResetEvent / EffectorEvent are
                         imported, not redeclared)

§7.2 measurement compliance:
    - Holds no Substrate, Engine, Cluster, or Effector reference.
    - Subscribes to exactly two event types.
    - Does not influence the energy landscape.
    - Does not call any method on any brain component.
"""

PACK_NAME = "metareasoner"
PACK_VERSION = "0.1.0"
DECLARED_DEPENDENCIES = [
    "mpc_kernel.rfc001.events:BudgetResetEvent",
    "mpc_kernel.rfc001.events:EventBus",
    "mpc_session4:EffectorEvent",  # cross-pack: persistence_substrate's source
]
DECLARED_MUTATIONS: list = []   # measurement-only pack
NO_MODIFY_KERNEL = True
NO_SHADOW = True
