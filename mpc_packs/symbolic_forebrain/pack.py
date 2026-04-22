"""SymbolicForebrain — AMEND-009 normative implementation.

Spec source: SESSION-5-TASK-PROMPT-v2.md §AMEND-009 (plus part-2 §D4 for
the default rule library: reconstructed thresholds and ordering).

Default rule library (first-match-wins):

    Rule 1 (rebudget up):
        predicate: thermal_pressure > 0.3 AND under_budget > 0.3
        action:    rebudget to cluster.local_budget * 1.5

    Rule 2 (add_proposition):
        predicate: exploration_saturation > 0.7
        action:    add a fresh quadratic well at a near-origin position,
                   stiffness 1.0.

    Rule 3 (remove_proposition):
        predicate: distant_start > 0.6 AND len(cluster._handles) >= 1
        action:    remove the handle with the highest stiffness.

    Rule 4 (rebudget down):
        predicate: idle > 0.7 AND len(cluster.engines) >= 2
        action:    rebudget to cluster.local_budget * 0.7

    Rule 5 (catch-all):
        predicate: True
        action:    noop

A custom plan_library can be injected via the constructor argument;
TASK-5 uses this to supply maze-specific rules.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from mpc_engine_rfc001 import Network
from mpc_packs.metareasoner.pack import Metareasoner
from mpc_packs.z3_socket.pack import Z3SymbolicSocket


# ── Action record ────────────────────────────────────────────────────────────

@dataclass
class Action:
    """Planner-emitted action applied by SymbolicForebrain.execute().

    kind values and payload schemas:
        "add_proposition"    : {"label": str, "formula_fn": Callable, "strength": float}
        "remove_proposition" : {"label": str}
        "rebudget"           : {"new_budget": float}
        "noop"               : {}
    """
    kind: str
    cluster_id: str
    payload: Dict[str, Any] = field(default_factory=dict)


# ── Forebrain ───────────────────────────────────────────────────────────────

class SymbolicForebrain:
    """Rule-based planner that reads Metareasoner signals and emits Actions.

    RFC-001 compliance: reads substrate state only through public cluster
    attributes (`_handles`, `engines`, `local_budget`, `ops`) and never
    instantiates a Bus or Substrate of its own. Only mutation routes are
    the three documented in config.py.
    """

    def __init__(
        self,
        network: Network,
        metareasoner: Metareasoner,
        symbolic_socket: Z3SymbolicSocket,
        plan_library: Optional[List[Tuple[Callable, Callable]]] = None,
    ):
        self.network = network
        self.mr = metareasoner
        self.socket = symbolic_socket
        self.plan_library = (
            plan_library if plan_library is not None else self._default_rules()
        )

    # ── public interface ────────────────────────────────────────────────────

    def plan_step(self) -> Dict[str, Action]:
        """For each cluster registered in metareasoner, evaluate rules in
        order, execute the first matching action, and return the action
        map (no-match clusters get a noop).
        """
        out: Dict[str, Action] = {}
        for cid in sorted(self.mr._registered):
            cluster = self.network.clusters.get(cid)
            if cluster is None:
                continue

            signals = self.mr.snapshot(cid)
            chosen: Optional[Action] = None
            for predicate, factory in self.plan_library:
                try:
                    fires = bool(predicate(signals, cluster, self.network))
                except TypeError:
                    # Allow simple 1-arg predicates in addition to the full
                    # 3-arg signature; Test A uses 1-arg predicates.
                    try:
                        fires = bool(predicate(signals))
                    except Exception:
                        fires = False
                except Exception:
                    fires = False

                if not fires:
                    continue

                try:
                    action = factory(cid, signals, cluster, self.network)
                except Exception as exc:
                    # Factory guard failure → try next rule.
                    action = None
                    continue

                if action is None:
                    continue
                chosen = action
                break

            if chosen is None:
                chosen = Action(kind="noop", cluster_id=cid, payload={})

            out[cid] = chosen
            if chosen.kind != "noop":
                self.execute(chosen)

        return out

    def execute(self, action: Action) -> None:
        """Apply the action to the target cluster via the three public
        mutation routes.
        """
        cid = action.cluster_id
        cluster = self.network.clusters.get(cid)
        if cluster is None:
            return

        kind = action.kind
        p = action.payload

        if kind == "add_proposition":
            label = p["label"]
            formula_fn = p["formula_fn"]
            strength = float(p.get("strength", 1.0))
            well_width = float(p.get("well_width", 1.0))

            self.socket.observe_symbolic(
                formula_fn=formula_fn,
                label=label,
                strength=strength,
                well_width=well_width,
            )
            specs = self.socket.flush()
            if not specs:
                return
            # Pick the spec matching our label; fall back to last.
            spec = next((s for s in specs if s.label == label), specs[-1])
            # cluster.load expects Dict[pid -> fn], Dict[pid -> stiffness],
            # optional Dict[pid -> centre]. LateralCluster/PersistenceCluster
            # support the `centres` kwarg; plain MPCCluster does not.
            try:
                cluster.load(
                    {label: spec.fn},
                    stiffnesses={label: spec.lambda_},
                )
            except TypeError:
                cluster.load({label: spec.fn})

        elif kind == "remove_proposition":
            label = p["label"]
            handle = cluster._handles.get(label)
            if handle is None:
                return
            cluster.ops.reset(handle, cluster.cluster_id)
            cluster._handles.pop(label, None)

        elif kind == "rebudget":
            new = float(p.get("new_budget", cluster.local_budget))
            new = max(0.5, new)
            cluster.local_budget = new
            for eng in cluster.engines:
                eng.E_star = new

        elif kind == "noop":
            return

        else:
            # Unknown kind → no-op; stay defensive.
            return

    # ── default rule library (§D4) ──────────────────────────────────────────

    def _default_rules(self) -> List[Tuple[Callable, Callable]]:
        """Five-rule library reconstructed per part-2 §D4 thresholds."""

        def rule1_pred(signals, cluster=None, network=None) -> bool:
            return (
                signals.get("thermal_pressure", 0.0) > 0.3
                and signals.get("under_budget", 0.0) > 0.3
            )

        def rule1_factory(cid, signals, cluster, network) -> Action:
            return Action(
                kind="rebudget",
                cluster_id=cid,
                payload={"new_budget": cluster.local_budget * 1.5},
            )

        def rule2_pred(signals, cluster=None, network=None) -> bool:
            return signals.get("exploration_saturation", 0.0) > 0.7

        def rule2_factory(cid, signals, cluster, network) -> Action:
            label = f"explore_{uuid.uuid4().hex[:6]}"
            # Well centred at origin; encoded symbolically so the socket's
            # symbolic/unsat accounting applies uniformly.
            def formula_fn(v):
                return [v[0] == 0, v[1] == 0]
            return Action(
                kind="add_proposition",
                cluster_id=cid,
                payload={
                    "label": label,
                    "formula_fn": formula_fn,
                    "strength": 1.0,
                },
            )

        def rule3_pred(signals, cluster=None, network=None) -> bool:
            if signals.get("distant_start", 0.0) <= 0.6:
                return False
            if cluster is None:
                return False
            return len(cluster._handles) >= 1

        def rule3_factory(cid, signals, cluster, network) -> Action:
            handles = list(cluster._handles.values())
            if not handles:
                return Action(kind="noop", cluster_id=cid, payload={})
            target = max(handles, key=lambda h: h.stiffness)
            return Action(
                kind="remove_proposition",
                cluster_id=cid,
                payload={"label": target.proposition_id},
            )

        def rule4_pred(signals, cluster=None, network=None) -> bool:
            if signals.get("idle", 0.0) <= 0.7:
                return False
            if cluster is None:
                return False
            return len(cluster.engines) >= 2

        def rule4_factory(cid, signals, cluster, network) -> Action:
            return Action(
                kind="rebudget",
                cluster_id=cid,
                payload={"new_budget": cluster.local_budget * 0.7},
            )

        def rule5_pred(signals, cluster=None, network=None) -> bool:
            return True

        def rule5_factory(cid, signals, cluster, network) -> Action:
            return Action(kind="noop", cluster_id=cid, payload={})

        return [
            (rule1_pred, rule1_factory),
            (rule2_pred, rule2_factory),
            (rule3_pred, rule3_factory),
            (rule4_pred, rule4_factory),
            (rule5_pred, rule5_factory),
        ]


# ── AMEND-009 acceptance tests ───────────────────────────────────────────────

def _build_fixture(n_engines: int = 2):
    """Fresh bus + network + persistence cluster + mr + socket + forebrain.

    Returns (bus, network, cluster, mr, socket, forebrain).
    """
    from mpc_kernel.rfc001.events import EventBus as KEventBus  # noqa: F401
    from mpc_engine_rfc001 import EventBus, Network
    from mpc_session4 import PersistenceCluster, Effector

    bus = EventBus()
    network = Network(bus=bus)
    _ = Effector().attach(bus)  # lambda_avg registration not needed for tests

    cluster = PersistenceCluster(
        dim=4, E_star=8.0, max_engines=n_engines, bus=bus,
        E_c=0.5, E_s=3.0, tau_base=200.0,
        usage_coefficient=1.0, outcome_coefficient=0.3,
    )
    # Ensure at least n_engines engines (PersistenceCluster seeds 1).
    while len(cluster.engines) < n_engines:
        cluster.add_engine(E_star=cluster.local_budget, dt=0.01)

    network.clusters["main"] = cluster

    mr = Metareasoner(window=50).attach(bus)
    mr.register_cluster("main", e_star=8.0)

    socket = Z3SymbolicSocket(dim=4)
    forebrain = SymbolicForebrain(network, mr, socket)

    return bus, network, cluster, mr, socket, forebrain


def _reset_mr_signals(mr: Metareasoner) -> None:
    """Wipe internal Metareasoner state so we can inject fresh signals."""
    for cid in list(mr._registered):
        mr._commit_history[cid].clear()
        mr._reset_history[cid].clear()
        mr._landauer_total[cid] = 0.0
        mr._total_cost_total[cid] = 0.0
        mr._steps_since_commit[cid] = 0


def _inject_signals_via_monkeypatch(mr: Metareasoner, cid: str, signals: Dict[str, float]):
    """Patch mr.snapshot so plan_step sees the injected signals for `cid`.

    The snapshot() path is the one the forebrain reads; overriding it is
    the cleanest way to inject without touching any private bucketing
    maths. All five signals default to 0.0.
    """
    full = {
        "under_budget": 0.0,
        "distant_start": 0.0,
        "exploration_saturation": 0.0,
        "thermal_pressure": 0.0,
        "idle": 0.0,
    }
    full.update(signals)
    original = mr.snapshot

    def patched(_cid: str) -> Dict[str, float]:
        if _cid == cid:
            return full
        return original(_cid)

    mr.snapshot = patched  # type: ignore[assignment]


def test_amend009() -> Tuple[bool, bool]:
    """Two sub-tests per v2 §AMEND-009; return (test_A_ok, test_B_ok)."""

    # ─── Test A — predicate firing ────────────────────────────────────────
    bus_A, net_A, cl_A, mr_A, sock_A, fb_A = _build_fixture(n_engines=2)

    old_budget = cl_A.local_budget

    # Rule 1: thermal_pressure=0.5, under_budget=0.5 → rebudget UP
    _inject_signals_via_monkeypatch(
        mr_A, "main",
        {"thermal_pressure": 0.5, "under_budget": 0.5},
    )
    actions = fb_A.plan_step()
    a1 = actions["main"]
    assert a1.kind == "rebudget", f"Rule1 expected 'rebudget', got {a1.kind!r}"
    new_after_1 = a1.payload.get("new_budget")
    assert new_after_1 > old_budget, (
        f"Rule1 expected new>old ({new_after_1} > {old_budget})"
    )

    # Re-inject Rule 2: exploration_saturation=0.9, idle=0.2 → add_proposition
    _inject_signals_via_monkeypatch(
        mr_A, "main",
        {"exploration_saturation": 0.9, "idle": 0.2},
    )
    a2 = fb_A.plan_step()["main"]
    assert a2.kind == "add_proposition", f"Rule2 got {a2.kind!r}"

    # Rule 3: distant_start=0.8, cluster has ≥1 handle (we just loaded one
    # via the rule-2 add). Expect remove_proposition.
    assert len(cl_A._handles) >= 1, "Rule3 precondition: ≥1 handle loaded"
    _inject_signals_via_monkeypatch(
        mr_A, "main",
        {"distant_start": 0.8},
    )
    a3 = fb_A.plan_step()["main"]
    assert a3.kind == "remove_proposition", f"Rule3 got {a3.kind!r}"

    # Rule 4: idle=0.9, cluster has 2 engines → rebudget DOWN
    before_budget = cl_A.local_budget
    _inject_signals_via_monkeypatch(
        mr_A, "main",
        {"idle": 0.9},
    )
    a4 = fb_A.plan_step()["main"]
    assert a4.kind == "rebudget", f"Rule4 got {a4.kind!r}"
    new_after_4 = a4.payload.get("new_budget")
    assert new_after_4 < before_budget, (
        f"Rule4 expected new<old ({new_after_4} < {before_budget})"
    )

    # Rule 5: all zero → noop
    _inject_signals_via_monkeypatch(
        mr_A, "main",
        {},  # all zero
    )
    a5 = fb_A.plan_step()["main"]
    assert a5.kind == "noop", f"Rule5 got {a5.kind!r}"

    test_A_ok = True

    # ─── Test B — execute side effects ────────────────────────────────────
    bus_B, net_B, cl_B, mr_B, sock_B, fb_B = _build_fixture(n_engines=2)

    label = "test_well"
    def ff_B(v):
        return [v[0] == 2, v[1] == 0]

    assert label not in cl_B._handles, "Test B: label must start absent"

    fb_B.execute(Action(
        kind="add_proposition",
        cluster_id="main",
        payload={"label": label, "formula_fn": ff_B, "strength": 1.0},
    ))
    assert label in cl_B._handles, (
        f"Test B: label {label!r} missing after add_proposition; "
        f"handles={list(cl_B._handles.keys())}"
    )

    fb_B.execute(Action(
        kind="remove_proposition",
        cluster_id="main",
        payload={"label": label},
    ))
    assert label not in cl_B._handles, (
        f"Test B: label {label!r} still present after remove_proposition"
    )

    test_B_ok = True

    return test_A_ok, test_B_ok


if __name__ == "__main__":
    a, b = test_amend009()
    print("AMEND-009A:", "PASS" if a else "FAIL")
    print("AMEND-009B:", "PASS" if b else "FAIL")
