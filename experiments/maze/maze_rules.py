"""experiments/maze/maze_rules.py — maze-specific plan_library for
SymbolicForebrain.

Spec source: SESSION-5-TASK-PROMPT-v2.md §TASK-5 → "Maze-specific rule
library". Five rules in priority order; first-match-wins. Each rule is a
(predicate, factory) pair with the signature the forebrain expects:
  predicate(signals, cluster, network) -> bool
  factory(cid, signals, cluster, network) -> Action

Design note — single source of truth
---------------------------------------
The v2 spec proposes a closure state dict {"current_focus", "loaded_labels",
"goal_loaded"}. This implementation derives all of that from `cluster._handles`
directly: the authoritative set of loaded propositions IS the cluster's handle
dict. Eliminating the shadow state removes a class of drift bugs where the
rule library's belief about what is loaded gets out of sync with the cluster.

Label convention:
    "goal_magnet"           — the one-time goal attractor (M1)
    "cell_{col}_{row}"      — a neighbourhood well (M2 / M3)
"""
from __future__ import annotations

from typing import Callable, List, Tuple

from mpc_packs.symbolic_forebrain.pack import Action

from experiments.maze.maze_world import Cell, MazeWorld


def _cell_label(cell: Cell) -> str:
    return f"cell_{cell[0]}_{cell[1]}"


def _label_to_cell(label: str) -> Cell:
    # "cell_C_R" → (C, R)
    parts = label.split("_")
    return (int(parts[1]), int(parts[2]))


def _loaded_cell_labels(cluster) -> set:
    """Subset of cluster._handles that represent cell wells (M2/M3 labels)."""
    return {lbl for lbl in cluster._handles if lbl.startswith("cell_")}


def _build_maze_rules(
    maze: MazeWorld,
    goal_stiffness: float = 0.05,
    neighbour_stiffness: float = 0.4,
) -> List[Tuple[Callable, Callable]]:
    """Return the five-rule plan_library for a SymbolicForebrain."""
    goal_col, goal_row = maze.goal

    # ── M1: one-time goal loading ────────────────────────────────────────────

    def m1_pred(signals, cluster, network) -> bool:
        return "goal_magnet" not in cluster._handles

    def m1_factory(cid, signals, cluster, network) -> Action:
        def ff(v, _c=goal_col, _r=goal_row):
            return [v[0] == _c, v[1] == _r]
        return Action(
            kind="add_proposition",
            cluster_id=cid,
            payload={
                "label": "goal_magnet",
                "formula_fn": ff,
                "strength": float(goal_stiffness),
                "well_width": 0.1,   # broad attractor
            },
        )

    # ── M2: advance focus (load agent's cell + neighbours one at a time) ─────

    def _desired_loaded(cluster):
        agent_cell = maze.position_to_cell(cluster.engines[0].v)
        desired = {_cell_label(c) for c in maze.neighbours(agent_cell)}
        desired.add(_cell_label(agent_cell))
        loaded = _loaded_cell_labels(cluster)
        return desired, loaded

    def m2_pred(signals, cluster, network) -> bool:
        desired, loaded = _desired_loaded(cluster)
        return desired != loaded

    def m2_factory(cid, signals, cluster, network) -> Action:
        desired, loaded = _desired_loaded(cluster)
        to_add = desired - loaded
        to_remove = loaded - desired

        if to_add:
            label = sorted(to_add)[0]
            col, row = _label_to_cell(label)

            def ff(v, _c=col, _r=row):
                return [v[0] == _c, v[1] == _r]

            return Action(
                kind="add_proposition",
                cluster_id=cid,
                payload={
                    "label": label,
                    "formula_fn": ff,
                    "strength": float(neighbour_stiffness),
                    "well_width": 1.0,
                },
            )

        if to_remove:
            label = sorted(to_remove)[0]
            return Action(
                kind="remove_proposition",
                cluster_id=cid,
                payload={"label": label},
            )

        # Predicate said "different" but diff is empty: defensive noop.
        return Action(kind="noop", cluster_id=cid, payload={})

    # ── M6: idle → prune farthest-from-goal loaded cell  (Session 10) ────────
    #
    # The agent settles at the centroid of the M2-loaded cells and stops
    # advancing because the basin is symmetric. M6 breaks the symmetry: when
    # idle, drop the cell label whose Manhattan distance to the goal is
    # largest, while leaving the agent's current cell loaded. Net effect:
    # the basin shifts forward, the agent has 20 substrate steps with the
    # asymmetric pull before M2's next plan_step re-adds the dropped cell.
    #
    # Priority is M2-then-M6: M2 always keeps the agent_cell + neighbours in
    # sync first, so M6 only fires once that bookkeeping settles. M6 is
    # before M3 because expanding (M3) without first contracting (M6) just
    # widens an already-stable basin.

    def m6_pred(signals, cluster, network) -> bool:
        if signals.get("idle", 0.0) <= 0.5:
            return False
        agent_cell = maze.position_to_cell(cluster.engines[0].v)
        cell_handles = _loaded_cell_labels(cluster)
        # Need a candidate that is NOT the agent's current cell.
        for label in cell_handles:
            if _label_to_cell(label) != agent_cell:
                return True
        return False

    def m6_factory(cid, signals, cluster, network) -> Action:
        agent_cell = maze.position_to_cell(cluster.engines[0].v)
        cell_handles = _loaded_cell_labels(cluster)
        candidates = [
            lbl for lbl in cell_handles
            if _label_to_cell(lbl) != agent_cell
        ]
        if not candidates:
            return Action(kind="noop", cluster_id=cid, payload={})
        gc, gr = maze.goal

        def goal_dist(label: str) -> int:
            c, r = _label_to_cell(label)
            return abs(c - gc) + abs(r - gr)

        farthest = max(candidates, key=goal_dist)
        return Action(
            kind="remove_proposition",
            cluster_id=cid,
            payload={"label": farthest},
        )

    # ── M3: idle + saturated exploration → expand 2-hop neighbourhood ────────

    def m3_pred(signals, cluster, network) -> bool:
        return (
            signals.get("idle", 0.0) > 0.5
            and signals.get("exploration_saturation", 0.0) > 0.7
        )

    def m3_factory(cid, signals, cluster, network) -> Action:
        agent_cell = maze.position_to_cell(cluster.engines[0].v)
        loaded = _loaded_cell_labels(cluster)
        one_hop = set(maze.neighbours(agent_cell))
        two_hop: set = set()
        for n1 in one_hop:
            for n2 in maze.neighbours(n1):
                two_hop.add(n2)
        two_hop -= {agent_cell}
        two_hop -= one_hop
        candidates = sorted(c for c in two_hop if _cell_label(c) not in loaded)
        if not candidates:
            return Action(kind="noop", cluster_id=cid, payload={})
        col, row = candidates[0]
        label = _cell_label((col, row))

        def ff(v, _c=col, _r=row):
            return [v[0] == _c, v[1] == _r]

        return Action(
            kind="add_proposition",
            cluster_id=cid,
            payload={
                "label": label,
                "formula_fn": ff,
                "strength": float(neighbour_stiffness) * 0.5,
                "well_width": 1.0,
            },
        )

    # ── M4: thermal pressure → rebudget up ───────────────────────────────────

    def m4_pred(signals, cluster, network) -> bool:
        return signals.get("thermal_pressure", 0.0) > 0.3

    def m4_factory(cid, signals, cluster, network) -> Action:
        return Action(
            kind="rebudget",
            cluster_id=cid,
            payload={"new_budget": cluster.local_budget * 1.3},
        )

    # ── M5: catch-all ────────────────────────────────────────────────────────

    def m5_pred(signals, cluster, network) -> bool:
        return True

    def m5_factory(cid, signals, cluster, network) -> Action:
        return Action(kind="noop", cluster_id=cid, payload={})

    return [
        (m1_pred, m1_factory),
        (m2_pred, m2_factory),
        (m6_pred, m6_factory),
        (m3_pred, m3_factory),
        (m4_pred, m4_factory),
        (m5_pred, m5_factory),
    ]
