"""experiments/maze/run.py — Session 5b TASK-5 driver.

Wires the five packs around a MazeWorld, runs the 1500-step substrate
loop, records traces, evaluates the six TASK-5 acceptance criteria,
prints informational metrics, and emits the 4-panel figure.

Spec: SESSION-5-TASK-PROMPT-v2.md §TASK-5 (Wiring + Loop + Plot);
SESSION-5-TASK-PROMPT-v3.md §4.2/§4.3/§4.4.
"""
from __future__ import annotations

# ── sys.path setup — must precede any mpc_* imports ──────────────────────────
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_UPLOADS = "/mnt/user-data/uploads"
for _p in (_REPO_ROOT, _UPLOADS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── stdlib + scientific ──────────────────────────────────────────────────────
from collections import Counter
from typing import Any, Dict, List, Tuple

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle

# ── MPC stack ────────────────────────────────────────────────────────────────
from mpc_engine_rfc001 import EventBus, Network
from mpc_packs.persistence_substrate.pack import PersistenceCluster, Effector
from mpc_packs.z3_socket.pack import Z3SymbolicSocket
from mpc_packs.metareasoner.pack import Metareasoner
from mpc_packs.symbolic_forebrain.pack import SymbolicForebrain
from mpc_packs.dynamical_gate import (
    DynamicalEngine,
    DynamicalGate,
    StreamingObservables,
)
from mpc_packs.physics_primitives import run_langevin

# ── local experiment modules ─────────────────────────────────────────────────
from experiments.maze.manifest import EXPERIMENT_CONFIG, check_kernel_version
from experiments.maze.maze_world import MazeWorld
from experiments.maze.maze_rules import _build_maze_rules


# ── config shortcuts ─────────────────────────────────────────────────────────

MAZE_W = EXPERIMENT_CONFIG["maze_w"]
MAZE_H = EXPERIMENT_CONFIG["maze_h"]
DIM = EXPERIMENT_CONFIG["dim"]
E_STAR_INIT = EXPERIMENT_CONFIG["e_star_init"]
MAX_ENGINES = EXPERIMENT_CONFIG["max_engines"]
N_STEPS = EXPERIMENT_CONFIG["n_steps"]
PLAN_INTERVAL = EXPERIMENT_CONFIG["plan_interval"]
GOAL_STIFFNESS = EXPERIMENT_CONFIG["goal_stiffness"]
NEIGHBOUR_STIFFNESS = EXPERIMENT_CONFIG["neighbour_stiffness"]
TAU_BASE = EXPERIMENT_CONFIG["tau_base"]
USAGE_COEF = EXPERIMENT_CONFIG["usage_coef"]
OUTCOME_COEF = EXPERIMENT_CONFIG["outcome_coef"]
WINDOW = EXPERIMENT_CONFIG["window"]
E_C = EXPERIMENT_CONFIG["E_c"]
E_S = EXPERIMENT_CONFIG["E_s"]
SEED = EXPERIMENT_CONFIG["seed"]

PLOT_PATH = os.path.join(_HERE, "artifacts", "maze_demo.png")

# Session-8 toggle: swap each cluster engine for a DynamicalEngine so
# PhaseTransitionEvent.fdr_slope is populated automatically on basin entry.
# Set to False to run the Session-5 baseline InstrumentedEngine path.
USE_DYNAMICAL_ENGINE = True


# ── dynamical-engine swap (Session 8) ────────────────────────────────────────

def _upgrade_cluster_engines_to_dynamical(cluster, maze) -> None:
    """Replace each MetastableEngine / InstrumentedEngine in cluster.engines
    with a DynamicalEngine carrying a DynamicalGate + StreamingObservables
    pair. Async release keeps measure_fdr off the stepping critical path;
    the stepping loop runs at full speed, the worker returns asynchronously,
    and subsequent PhaseTransitionEvents carry the cached fdr_slope.

    Physical setup:
      - τ-gate observable: total substrate energy (substrate-agnostic).
      - V_obs for measure_fdr: same.
      - Bath reference for τ_env: Langevin trajectory on a weak harmonic
        potential centred at the maze centre. Proxy for free-bath
        diffusion on this substrate.
    """
    center = maze.cell_to_position((maze.width // 2, maze.height // 2), DIM)
    U_bath = lambda v: 0.05 * np.sum((v - center) ** 2)
    bath = run_langevin(U_bath, center, 500, rng=np.random.default_rng(7))

    V_obs = cluster.sub.energy  # bound method; closes over the live substrate

    upgraded = []
    for old in cluster.engines:
        gate = DynamicalGate(window=300, tau_floor=0.05, recompute_interval=100)
        obs = StreamingObservables(V_A_fn=V_obs, window=300, bath_trajectory=bath)
        new_eng = DynamicalEngine(
            substrate=old.sub,
            bus=old.bus,
            gate=gate,
            observables=obs,
            V_obs=V_obs,
            h_mag=0.05,
            async_release=True,
            E_star=old.E_star,
            dt=old.dt,
            barrier_strength=old.barrier_strength,
            cluster_id=old.cluster_id,
        )
        new_eng.v = old.v.copy()
        new_eng.attention_scarcity = old.attention_scarcity
        upgraded.append(new_eng)

    cluster.engines = upgraded


# ── wiring ───────────────────────────────────────────────────────────────────

def build_world() -> Tuple[MazeWorld, Network, EventBus, PersistenceCluster,
                           Effector, Metareasoner, Z3SymbolicSocket,
                           SymbolicForebrain]:
    """Construct all components in the order specified by v2 §TASK-5 Wiring."""
    check_kernel_version()

    maze = MazeWorld(MAZE_W, MAZE_H, seed=SEED)
    print(maze.render_ascii())
    print()
    print(f"start={maze.start}  goal={maze.goal}  "
          f"A* length={len(maze.astar())}  openings={len(maze._openings)}")

    bus = EventBus()
    network = Network(bus=bus)
    effector = Effector().attach(bus)
    mr = Metareasoner(window=WINDOW).attach(bus)
    socket = Z3SymbolicSocket(dim=DIM)

    cluster = PersistenceCluster(
        dim=DIM, E_star=E_STAR_INIT, max_engines=MAX_ENGINES, bus=bus,
        E_c=E_C, E_s=E_S,
        tau_base=TAU_BASE,
        usage_coefficient=USAGE_COEF,
        outcome_coefficient=OUTCOME_COEF,
    )

    # Rewrite cluster_id and every engine's cluster_id to "main" per
    # SESSION-5b-TASK-PROMPT handoff note (PersistenceCluster auto-generates
    # `auto_XXXXXX` via AutoCluster.__init__; PersistenceCluster._on_phase_transition
    # filters by cluster_id; Effector/Metareasoner register under "main").
    cluster.cluster_id = "main"
    for eng in cluster.engines:
        eng.cluster_id = "main"

    if USE_DYNAMICAL_ENGINE:
        _upgrade_cluster_engines_to_dynamical(cluster, maze)

    network.clusters["main"] = cluster

    effector.register_cluster("main", lambda_avg=NEIGHBOUR_STIFFNESS)
    mr.register_cluster("main", e_star=E_STAR_INIT)

    # Place engine at start cell (v2 §TASK-5 Wiring).
    start_pos = maze.cell_to_position(maze.start, DIM)
    for eng in cluster.engines:
        eng.v = start_pos.copy()
        eng.attention_scarcity = 0.05

    forebrain = SymbolicForebrain(
        network, mr, socket,
        plan_library=_build_maze_rules(
            maze,
            goal_stiffness=GOAL_STIFFNESS,
            neighbour_stiffness=NEIGHBOUR_STIFFNESS,
        ),
    )

    return maze, network, bus, cluster, effector, mr, socket, forebrain


# ── loop ─────────────────────────────────────────────────────────────────────

def run_loop(maze, cluster, effector, mr, forebrain) -> Dict[str, Any]:
    signal_trace: List[Dict[str, float]] = []
    n_constraints_trace: List[int] = []
    budget_trace: List[float] = []
    cum_cost_trace: List[float] = []
    agent_cell_trace: List[Tuple[int, int]] = []
    action_log: List[Tuple[int, str, str]] = []
    plan_step_count = 0

    for step in range(N_STEPS):
        cluster.step()
        cluster.sub.decay_step()
        mr.tick()

        signal_trace.append(dict(mr.snapshot("main")))
        n_constraints_trace.append(len(cluster._handles))
        budget_trace.append(float(cluster.local_budget))
        cum_cost_trace.append(
            float(sum(e.total_cost for e in effector.effector_events("main")))
        )
        agent_cell_trace.append(maze.position_to_cell(cluster.engines[0].v))

        if step > 0 and step % PLAN_INTERVAL == 0:
            plan_step_count += 1
            actions = forebrain.plan_step()
            for cid, action in actions.items():
                if action.kind != "noop":
                    tag = action.payload.get("label") or action.payload.get(
                        "new_budget"
                    )
                    action_log.append((step, action.kind, str(tag)))

    # Drain any background FDR worker(s) before returning so the cached
    # slope is finalised for downstream inspection.
    for eng in cluster.engines:
        if hasattr(eng, "wait_for_release"):
            eng.wait_for_release()

    return {
        "signal_trace": signal_trace,
        "n_constraints_trace": n_constraints_trace,
        "budget_trace": budget_trace,
        "cum_cost_trace": cum_cost_trace,
        "agent_cell_trace": agent_cell_trace,
        "action_log": action_log,
        "plan_step_count": plan_step_count,
    }


# ── plotting ─────────────────────────────────────────────────────────────────

def make_plot(maze: MazeWorld, cluster, effector, mr, traces: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(PLOT_PATH), exist_ok=True)

    fig, axes = plt.subplots(4, 1, figsize=(11, 16))
    fig.suptitle(
        f"Session 5b — TASK-5 Maze Navigation Closed Loop "
        f"({MAZE_W}×{MAZE_H} maze, {N_STEPS} steps, "
        f"plan_interval={PLAN_INTERVAL})",
        fontsize=13, y=0.995,
    )

    # ── Panel 1: maze + agent trajectory + A* reference ──────────────────────
    ax = axes[0]
    w, h = maze.width, maze.height

    # Cell floors (white on a tan border).
    ax.set_xlim(-0.5, w - 0.5)
    ax.set_ylim(h - 0.5, -0.5)   # invert y so row 0 is top, matching ASCII render
    ax.set_aspect("equal")
    for c in range(w):
        for r in range(h):
            ax.add_patch(Rectangle((c - 0.5, r - 0.5), 1, 1,
                                   facecolor="#FAFAFA", edgecolor="none"))

    # Walls — bold lines between adjacent cells not in _openings.
    wall_segs: List = []
    for c in range(w):
        for r in range(h):
            # Right neighbour
            if c + 1 < w and frozenset({(c, r), (c + 1, r)}) not in maze._openings:
                wall_segs.append([(c + 0.5, r - 0.5), (c + 0.5, r + 0.5)])
            # Bottom neighbour (row+1)
            if r + 1 < h and frozenset({(c, r), (c, r + 1)}) not in maze._openings:
                wall_segs.append([(c - 0.5, r + 0.5), (c + 0.5, r + 0.5)])
    # Outer border.
    wall_segs.extend([
        [(-0.5, -0.5), (w - 0.5, -0.5)],       # top
        [(-0.5, h - 0.5), (w - 0.5, h - 0.5)], # bottom
        [(-0.5, -0.5), (-0.5, h - 0.5)],        # left
        [(w - 0.5, -0.5), (w - 0.5, h - 0.5)],  # right
    ])
    ax.add_collection(LineCollection(wall_segs, colors="#222", linewidths=1.8))

    # A* reference path — thin grey.
    astar = maze.astar()
    if len(astar) > 1:
        axs_x = [c for c, r in astar]
        axs_y = [r for c, r in astar]
        ax.plot(axs_x, axs_y, "-", color="#BBBBBB", linewidth=1.4,
                label=f"A* optimal ({len(astar)} cells)", zorder=2)

    # Agent trajectory — colour-graded blue→orange.
    cell_seq = traces["agent_cell_trace"]
    if len(cell_seq) > 1:
        pts = np.array(cell_seq, dtype=float)
        segs = np.stack([pts[:-1], pts[1:]], axis=1)
        colours = plt.cm.cool(np.linspace(0, 1, len(segs)))
        # Overlay with a second colourmap to span blue→orange.
        colours = plt.get_cmap("plasma")(np.linspace(0.15, 0.85, len(segs)))
        lc = LineCollection(segs, colors=colours, linewidths=1.2, alpha=0.85, zorder=3)
        ax.add_collection(lc)

    # Start / goal markers.
    sc, sr = maze.start
    gc, gr = maze.goal
    ax.plot([sc], [sr], "o", color="#1f77b4", markersize=12, label="start",
            zorder=5)
    ax.plot([gc], [gr], "*", color="#d62728", markersize=16, label="goal",
            zorder=5)
    fc, fr = cell_seq[-1] if cell_seq else maze.start
    ax.plot([fc], [fr], "D", color="#2ca02c", markersize=9, label="final",
            zorder=5)

    ax.set_title("Panel 1 — Maze with agent trajectory (plasma gradient = step order)")
    ax.set_xlabel("col")
    ax.set_ylabel("row")
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)

    # ── Panel 2: five Metareasoner signals ──────────────────────────────────
    ax = axes[1]
    sig = traces["signal_trace"]
    keys = ["under_budget", "distant_start", "exploration_saturation",
            "thermal_pressure", "idle"]
    xs = np.arange(len(sig))
    for k in keys:
        ys = np.array([s.get(k, 0.0) for s in sig])
        ax.plot(xs, ys, linewidth=1.0, label=k)
    ax.set_title("Panel 2 — Metareasoner signals (clipped to [0,1])")
    ax.set_xlabel("step")
    ax.set_ylabel("signal")
    ax.set_ylim(-0.05, 1.05)
    ax.legend(loc="upper right", fontsize=8, ncol=3)
    ax.grid(True, alpha=0.25)

    # ── Panel 3: n_constraints + local_budget (dual axis) ───────────────────
    ax = axes[2]
    n_trace = traces["n_constraints_trace"]
    b_trace = traces["budget_trace"]
    l1, = ax.step(np.arange(len(n_trace)), n_trace, where="post",
                  color="#1f77b4", label="n constraints")
    ax.set_ylabel("len(cluster._handles)", color="#1f77b4")
    ax.tick_params(axis="y", labelcolor="#1f77b4")
    ax.set_xlabel("step")
    ax2 = ax.twinx()
    l2, = ax2.step(np.arange(len(b_trace)), b_trace, where="post",
                   color="#ff7f0e", label="local_budget")
    ax2.set_ylabel("cluster.local_budget", color="#ff7f0e")
    ax2.tick_params(axis="y", labelcolor="#ff7f0e")
    ax.set_title("Panel 3 — constraint count and local budget")
    ax.grid(True, alpha=0.25)
    ax.legend(handles=[l1, l2], loc="upper left", fontsize=8)

    # ── Panel 4: cumulative EffectorEvent total_cost + action markers ───────
    ax = axes[3]
    cc = traces["cum_cost_trace"]
    ax.plot(np.arange(len(cc)), cc, color="#2ca02c", linewidth=1.1,
            label="cumulative EffectorEvent.total_cost")
    colour_map = {"add_proposition": "#2ca02c",
                  "remove_proposition": "#d62728",
                  "rebudget": "#1f77b4"}
    legend_done: set = set()
    for (step, kind, _tag) in traces["action_log"]:
        col = colour_map.get(kind, "#888888")
        lbl = kind if kind not in legend_done else None
        ax.axvline(step, color=col, alpha=0.4, linewidth=0.8, label=lbl)
        legend_done.add(kind)
    ax.set_title("Panel 4 — cumulative total_cost with action-log markers "
                 "(green=add, red=remove, blue=rebudget)")
    ax.set_xlabel("step")
    ax.set_ylabel("cumulative total_cost")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper left", fontsize=8)

    plt.tight_layout(rect=[0, 0, 1, 0.985])
    fig.savefig(PLOT_PATH, dpi=100)
    plt.close(fig)


# ── acceptance + informational report ────────────────────────────────────────

def evaluate(maze: MazeWorld, cluster, effector, traces: Dict[str, Any]) -> Dict[str, Any]:
    n_steps = len(traces["agent_cell_trace"])
    plan_calls = traces["plan_step_count"]
    required_plan_calls = max(0, (N_STEPS // PLAN_INTERVAL) - 1)

    non_noop_actions = traces["action_log"]
    n_cells_visited = len(set(traces["agent_cell_trace"]))
    n_handles_end = len(cluster._handles)

    plot_ok = os.path.exists(PLOT_PATH) and os.path.getsize(PLOT_PATH) > 0

    sub = {
        "TASK-5.1": ("No crash over N_STEPS substrate steps",
                     n_steps == N_STEPS, f"{n_steps}/{N_STEPS} steps completed"),
        "TASK-5.2": (f"plan_step() called >= {required_plan_calls}",
                     plan_calls >= required_plan_calls,
                     f"{plan_calls} plan_step() calls (required >= {required_plan_calls})"),
        "TASK-5.3": ("At least one non-noop action",
                     len(non_noop_actions) >= 1,
                     f"{len(non_noop_actions)} non-noop actions logged"),
        "TASK-5.4": ("Cluster has >= 1 constraint at end of run",
                     n_handles_end >= 1,
                     f"len(cluster._handles) = {n_handles_end}"),
        "TASK-5.5": ("Plot saved at artifacts/maze_demo.png",
                     plot_ok,
                     PLOT_PATH + (" (OK)" if plot_ok else " (MISSING)")),
        "TASK-5.6": ("Agent visited >= 3 distinct cells",
                     n_cells_visited >= 3,
                     f"{n_cells_visited} distinct cells visited"),
    }

    task5_pass = all(v[1] for v in sub.values())

    # ── informational metrics ────────────────────────────────────────────────
    final_cell = traces["agent_cell_trace"][-1] if traces["agent_cell_trace"] else None
    goal_cell = maze.goal
    astar_len = len(maze.astar())
    effector_events = effector.effector_events("main")
    n_commits = len(effector_events)
    action_kinds = Counter(k for (_, k, _) in non_noop_actions)
    final_signals = traces["signal_trace"][-1] if traces["signal_trace"] else {}

    info = {
        "final_cell": final_cell,
        "goal_cell": goal_cell,
        "reached_goal": final_cell == goal_cell,
        "cells_visited": n_cells_visited,
        "astar_length": astar_len,
        "n_effector_events": n_commits,
        "action_histogram": dict(action_kinds),
        "final_signals": {k: round(v, 4) for k, v in final_signals.items()},
        "final_budget": float(cluster.local_budget),
        "final_handles": sorted(cluster._handles.keys()),
    }

    return {
        "sub": sub,
        "task5_pass": task5_pass,
        "info": info,
    }


# ── entry ────────────────────────────────────────────────────────────────────

def main() -> Dict[str, Any]:
    maze, network, bus, cluster, effector, mr, socket, forebrain = build_world()

    print()
    print("=" * 72)
    print(f"Running {N_STEPS}-step substrate loop with plan_interval={PLAN_INTERVAL}")
    print("=" * 72)

    traces = run_loop(maze, cluster, effector, mr, forebrain)

    make_plot(maze, cluster, effector, mr, traces)

    result = evaluate(maze, cluster, effector, traces)

    print()
    print("=" * 72)
    print("TASK-5 acceptance")
    print("=" * 72)
    for key, (desc, ok, evidence) in result["sub"].items():
        verdict = "PASS" if ok else "FAIL"
        print(f"  {key}  {verdict}  — {desc}")
        print(f"           evidence: {evidence}")
    print()
    print(f"TASK-5 overall: {'PASS' if result['task5_pass'] else 'FAIL'}")

    print()
    print("=" * 72)
    print("Informational metrics (v3 §4.4)")
    print("=" * 72)
    info = result["info"]
    for k, v in info.items():
        print(f"  {k}: {v}")

    # ── Session-8 dynamical-engine state ────────────────────────────────────
    dynamical_engines = [
        e for e in cluster.engines if isinstance(e, DynamicalEngine)
    ]
    if dynamical_engines:
        print()
        print("=" * 72)
        print("DynamicalEngine state (Session 8)")
        print("=" * 72)
        for i, e in enumerate(dynamical_engines):
            slope = (
                f"{e.cached_fdr_slope:+.4f}"
                if e.cached_fdr_slope is not None
                else "None"
            )
            tau = (
                f"{e.gate.tau_estimate:.4f}"
                if e.gate.tau_estimate is not None
                else "None"
            )
            print(
                f"  engine[{i}]  release_count={e.release_count}  "
                f"cached_fdr_slope={slope}  "
                f"gate.tau_estimate={tau}  "
                f"gate.is_pinned={e.gate.is_pinned}"
            )

    return result


if __name__ == "__main__":
    main()
