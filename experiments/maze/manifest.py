"""experiments/maze/manifest.py — RFC-002 §3.3 experiment manifest.

Literal per SESSION-5-TASK-PROMPT-v3.md §4.2 (with the plan_library entry
resolved lazily, since maze_rules consumes a MazeWorld instance that is
constructed at runtime in run.py — see §4.2 paragraph on transitional shims).
"""
from __future__ import annotations

from mpc_kernel import __version__ as KERNEL_VERSION

KERNEL_REQUIRED = "0.4.0"   # the post-Step-0 kernel
DEFAULT_PACKS_DISABLED: list = []  # all defaults loaded

PACKS = [
    ("decaying_substrate",   {}),                                # S3 carve-out (shim)
    ("persistence_substrate", {"usage_coef": 1.0,
                               "outcome_coef": 0.3,
                               "tau_base": 200.0}),              # S4 carve-out (shim)
    ("z3_socket",            {}),                                # S5 new
    ("metareasoner",         {"window": 50,
                              "bucket_tolerance": 0.5}),         # S5 new
    # plan_library resolves to _build_maze_rules(maze) at wiring time in run.py.
    ("symbolic_forebrain",   {"plan_library": "maze_rules"}),    # S5 new
]

EXPERIMENT_CONFIG = {
    "maze_w": 7, "maze_h": 7,
    "dim": 4,
    "e_star_init": 8.0,
    "max_engines": 2,
    "n_steps": 1500,
    "plan_interval": 20,
    "goal_stiffness": 0.3,        # Session 10: swept up from 0.05 for faster traversal
    "neighbour_stiffness": 0.1,   # Session 10: swept down from 0.4; relative goal/neighbour ratio matters
    # Additional config items from v2 §TASK-5 configuration block.
    "tau_base": 200.0,
    "usage_coef": 1.0,
    "outcome_coef": 0.3,
    "window": 50,
    "E_c": 0.5,
    "E_s": 3.0,
    "seed": 2026,
}


def check_kernel_version() -> None:
    """Abort early if the kernel version doesn't match the experiment's
    requirement. RFC-002 §3.3 requires every experiment to declare and
    verify its kernel version before wiring.
    """
    if KERNEL_VERSION != KERNEL_REQUIRED:
        raise RuntimeError(
            f"manifest kernel mismatch: required {KERNEL_REQUIRED!r}, "
            f"got {KERNEL_VERSION!r}"
        )
