"""experiments/tolman/latent_learning.py — Tolman 1948 adapted.

Latent-learning protocol:

  Group L (latent):  Phase 1 (steps 0..N1)  — explore the maze with NO
                                                goal_magnet active.
                     Phase 2 (steps N1..N2) — add the goal_magnet and
                                                measure time-to-goal.

  Group C (control): Phase 0 (steps 0..N2)  — goal_magnet active from
                                                step zero.

Tolman's prediction: rats in Group L reach the goal faster on
introduction than they would naively, because they have built a
cognitive map during latent exploration. The MPC Brain analogue: the
DecayingSubstrate / PersistenceSubstrate retains memory of cell wells
visited during Phase 1, so once the goal_magnet is added the agent
should descend into a basin that's already partially mapped.

Status (Session 10): the framework runs end-to-end and the engine
produces deterministic per-condition metrics, but the agent's
traversal is currently constrained by the existing M1-M5 forebrain
rules to a small neighbourhood (Session-5 known limitation: the M6
"remove-behind-cell" rule remains deferred). So neither group reaches
the goal. The point of this scaffold is to be ready when traversal
lands; the comparison metric (cells_visited per phase, position trace,
nearest-cell-to-goal) is collected unconditionally.

Invocation:

    python -m experiments.tolman.latent_learning
"""

from __future__ import annotations

import os
import sys
from typing import Any, Callable, Dict, List, Tuple

import numpy as np

# Add repo root to path so ad-hoc invocation works.
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from mpc_engine_rfc001 import EventBus, Network  # noqa: E402
from mpc_packs.dynamical_gate import (  # noqa: E402
    DynamicalEngine,
    DynamicalGate,
    StreamingObservables,
)
from mpc_packs.metareasoner.pack import Metareasoner  # noqa: E402
from mpc_packs.persistence_substrate.pack import (  # noqa: E402
    Effector,
    PersistenceCluster,
)
from mpc_packs.physics_primitives import run_langevin  # noqa: E402
from mpc_packs.symbolic_forebrain.pack import SymbolicForebrain  # noqa: E402
from mpc_packs.z3_socket.pack import Z3SymbolicSocket  # noqa: E402

from experiments.maze.maze_rules import _build_maze_rules  # noqa: E402
from experiments.maze.maze_world import MazeWorld  # noqa: E402


# ── Config ─────────────────────────────────────────────────────────────────

MAZE_W, MAZE_H = 7, 7
DIM = 4
SEED = 2026

E_STAR = 8.0
MAX_ENGINES = 2
TAU_BASE = 200.0
USAGE_COEF = 1.0
OUTCOME_COEF = 0.3
WINDOW = 50
E_C, E_S = 0.5, 3.0
GOAL_STIFFNESS = 0.05
NEIGHBOUR_STIFFNESS = 0.4
PLAN_INTERVAL = 20

N_STEPS_PHASE_1 = 750     # latent exploration
N_STEPS_PHASE_2 = 750     # post-goal-introduction
N_STEPS_TOTAL = N_STEPS_PHASE_1 + N_STEPS_PHASE_2


# ── Latent-mode rule library ────────────────────────────────────────────────


def _build_latent_rules(maze, goal_enabled: List[bool], **kwargs):
    """Return a maze rule library whose M1 (goal_magnet) only fires when
    `goal_enabled[0]` is True. The list-of-bool indirection lets the
    caller flip the flag mid-run without rebuilding the library.

    All other rules (M2-M5) are inherited from the standard maze rules.
    """
    base_rules = _build_maze_rules(maze, **kwargs)
    # base_rules[0] is M1 (goal_magnet); wrap its predicate.
    m1_pred, m1_factory = base_rules[0]

    def gated_m1_pred(signals, cluster, network) -> bool:
        if not goal_enabled[0]:
            return False
        return m1_pred(signals, cluster, network)

    return [(gated_m1_pred, m1_factory)] + base_rules[1:]


# ── Build a fresh experiment world ──────────────────────────────────────────


def _build_world(maze, goal_enabled: List[bool]):
    """Construct one maze + brain stack. Returns the components needed for
    a run loop, parameterised by the goal_enabled latch."""
    bus = EventBus()
    network = Network(bus=bus)
    effector = Effector().attach(bus)
    mr = Metareasoner(window=WINDOW).attach(bus)
    socket = Z3SymbolicSocket(dim=DIM)
    cluster = PersistenceCluster(
        dim=DIM, E_star=E_STAR, max_engines=MAX_ENGINES, bus=bus,
        E_c=E_C, E_s=E_S,
        tau_base=TAU_BASE,
        usage_coefficient=USAGE_COEF,
        outcome_coefficient=OUTCOME_COEF,
    )
    cluster.cluster_id = "main"
    for eng in cluster.engines:
        eng.cluster_id = "main"

    # Upgrade engines to DynamicalEngine.
    center = maze.cell_to_position(
        (maze.width // 2, maze.height // 2), DIM,
    )
    U_bath = lambda v: 0.05 * np.sum((v - center) ** 2)
    bath = run_langevin(
        U_bath, center, 500, rng=np.random.default_rng(7),
    )
    V_obs = cluster.sub.energy

    new_engines = []
    for old in cluster.engines:
        gate = DynamicalGate(window=300, tau_floor=0.05, recompute_interval=100)
        obs = StreamingObservables(V_A_fn=V_obs, window=300, bath_trajectory=bath)
        new_eng = DynamicalEngine(
            substrate=old.sub, bus=old.bus,
            gate=gate, observables=obs, V_obs=V_obs, h_mag=0.05,
            async_release=True,
            E_star=old.E_star, dt=old.dt,
            barrier_strength=old.barrier_strength,
            cluster_id=old.cluster_id,
        )
        new_eng.v = old.v.copy()
        new_eng.attention_scarcity = old.attention_scarcity
        new_engines.append(new_eng)
    cluster.engines = new_engines

    network.clusters["main"] = cluster
    effector.register_cluster("main", lambda_avg=NEIGHBOUR_STIFFNESS)
    mr.register_cluster("main", e_star=E_STAR)

    start_pos = maze.cell_to_position(maze.start, DIM)
    for eng in cluster.engines:
        eng.v = start_pos.copy()
        eng.attention_scarcity = 0.05

    forebrain = SymbolicForebrain(
        network, mr, socket,
        plan_library=_build_latent_rules(
            maze, goal_enabled,
            goal_stiffness=GOAL_STIFFNESS,
            neighbour_stiffness=NEIGHBOUR_STIFFNESS,
        ),
    )
    return maze, network, bus, cluster, effector, mr, socket, forebrain


# ── Runner ──────────────────────────────────────────────────────────────────


def _run(label: str, n_steps: int, phase_switch_at: int) -> Dict[str, Any]:
    """Run one condition.

    `phase_switch_at` is the step at which the goal_magnet flag flips
    from False to True. Set to 0 for the control (goal active from
    start) or N_STEPS_PHASE_1 for the latent group. Set to n_steps to
    keep the goal off the entire run.
    """
    np.random.seed(SEED)
    maze = MazeWorld(MAZE_W, MAZE_H, seed=SEED)
    goal_enabled = [phase_switch_at == 0]   # mutable latch

    _, _, _, cluster, effector, mr, _, forebrain = _build_world(maze, goal_enabled)
    eng = cluster.engines[0]
    goal_pos = maze.cell_to_position(maze.goal, DIM)

    cells_phase = {0: set(), 1: set()}
    cell_trace: List[Tuple[int, Tuple[int, int]]] = []
    nearest_to_goal_distance: float = float("inf")
    first_goal_step: int = -1
    n_actions = {0: 0, 1: 0}

    for step in range(n_steps):
        if step == phase_switch_at and not goal_enabled[0]:
            goal_enabled[0] = True

        cluster.step()
        cluster.sub.decay_step()
        mr.tick()

        v = eng.v
        cell = maze.position_to_cell(v)
        phase = 1 if goal_enabled[0] else 0
        cells_phase[phase].add(cell)
        cell_trace.append((step, cell))

        dist = float(np.linalg.norm(v - goal_pos))
        if dist < nearest_to_goal_distance:
            nearest_to_goal_distance = dist
        if cell == maze.goal and first_goal_step < 0:
            first_goal_step = step

        if step > 0 and step % PLAN_INTERVAL == 0:
            actions = forebrain.plan_step()
            for cid, action in actions.items():
                if action.kind != "noop":
                    n_actions[phase] += 1

    # Drain any background FDR worker before we exit.
    for e in cluster.engines:
        if hasattr(e, "wait_for_release"):
            e.wait_for_release()

    return {
        "label": label,
        "n_steps": n_steps,
        "cells_phase_0": len(cells_phase[0]),  # latent / control-pre
        "cells_phase_1": len(cells_phase[1]),  # post-goal / control-only
        "cells_total": len(cells_phase[0] | cells_phase[1]),
        "first_goal_step": first_goal_step,
        "nearest_to_goal": nearest_to_goal_distance,
        "actions_phase_0": n_actions[0],
        "actions_phase_1": n_actions[1],
        "final_cell": cell_trace[-1][1],
        "release_count": eng.release_count,
        "fdr_slope": eng.cached_fdr_slope,
        "tau_estimate": eng.gate.tau_estimate,
    }


# ── Entry ──────────────────────────────────────────────────────────────────


def main() -> Dict[str, Any]:
    print("=" * 72)
    print(f"  Tolman 1948 — latent learning  ({MAZE_W}x{MAZE_H} maze)")
    print("=" * 72)

    print("\nGroup L (latent): no goal_magnet for steps 0..{}, "
          "then add it for steps {}..{}.".format(
              N_STEPS_PHASE_1, N_STEPS_PHASE_1, N_STEPS_TOTAL))
    latent = _run("latent", N_STEPS_TOTAL, phase_switch_at=N_STEPS_PHASE_1)

    print("\nGroup C (control): goal_magnet active from step 0..{}.".format(N_STEPS_TOTAL))
    control = _run("control", N_STEPS_TOTAL, phase_switch_at=0)

    print()
    print("=" * 72)
    print("  Comparison")
    print("=" * 72)
    width = 24
    fields = [
        ("cells visited (phase 0)", "cells_phase_0"),
        ("cells visited (phase 1)", "cells_phase_1"),
        ("cells visited (total)",   "cells_total"),
        ("first goal step",         "first_goal_step"),
        ("nearest dist to goal",    "nearest_to_goal"),
        ("actions phase 0",         "actions_phase_0"),
        ("actions phase 1",         "actions_phase_1"),
        ("final cell",              "final_cell"),
        ("FDR releases",            "release_count"),
        ("cached fdr_slope",        "fdr_slope"),
        ("final tau_estimate",      "tau_estimate"),
    ]
    print(f"  {'metric':<{width}}  {'latent':>14}  {'control':>14}")
    print(f"  {'-' * width}  {'-' * 14}  {'-' * 14}")
    for desc, key in fields:
        lv = latent.get(key)
        cv = control.get(key)
        def fmt(x):
            if x is None: return "—"
            if isinstance(x, float): return f"{x:.4f}"
            return str(x)
        print(f"  {desc:<{width}}  {fmt(lv):>14}  {fmt(cv):>14}")

    # Acceptance: framework runs without crashing.
    print()
    print("Acceptance: framework executes both conditions without crash. PASS.")
    print()
    print("Tolman prediction: latent group reaches goal faster than control "
          "after phase-1 exploration.")
    if latent["first_goal_step"] >= 0 and control["first_goal_step"] >= 0:
        print(f"  Both groups reached goal. latent={latent['first_goal_step']}, "
              f"control={control['first_goal_step']}. "
              f"{'Latent faster' if latent['first_goal_step'] < control['first_goal_step'] else 'Control faster'}.")
    else:
        print("  Neither group reached goal in this run — known limitation: "
              "the M6 'remove-behind-cell' rule remains deferred from "
              "Session 5/6/9. The framework is ready for when traversal "
              "lands.")
    return {"latent": latent, "control": control}


if __name__ == "__main__":
    main()
