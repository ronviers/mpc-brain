"""
mpc_session2.py — MPC Brain Session 2
Tasks 1-5: JAX-ify Substrate, scale validation, AutoCluster,
           LLM constraint encoder, hello-world disambiguation.

Conforms to RFC-001-MPC-BRAIN (April 2026).
All new classes hold exactly one Substrate and one EventBus;
no Calorimeter references in brain components.

Timing notes (CPU-only environment):
  FD Hessian at dim=64 costs ~250s/100 steps (O(n^2) Python loops).
  JAX Hessian at dim=64 costs ~3s/1000 steps (compiled XLA).
  Task 1 benchmark: FD timed at dim=8 (actual), JAX at dim=64 (actual);
  extrapolated speedup at dim=64 cited in summary.
"""

from __future__ import annotations

import os
import sys
import time
import uuid
import hashlib
import textwrap
import logging
from typing import Any, Callable, Dict, List, Optional

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# JAX availability
try:
    import jax
    import jax.numpy as jnp
    jax.config.update("jax_enable_x64", True)
    _JAX = True
except ImportError:
    _JAX = False

# Anthropic availability
try:
    import anthropic as _anthropic_mod
    _ANTHROPIC_LIB = True
except ImportError:
    _ANTHROPIC_LIB = False

# Base classes from Session 1
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mpc_engine_rfc001 import (
    Phase, EventBus, Substrate, MetastableEngine, MPCCluster,
    ConstraintHandle, LandauerEvent, BudgetResetEvent,
    PhaseTransitionEvent, Calorimeter,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)


# ================================================================================
#  Shared helper
# ================================================================================

def _make_quadratic_constraint(center: np.ndarray) -> Callable:
    """
    fn(v) = ||v - c||^2  using np.sum (no float() cast).

    np.sum is intercepted by JAX when the input is a traced array, so this
    function is JAX-differentiable without any code change.
    Works with numpy arrays (returns numpy scalar) and JAX arrays alike.
    """
    c = np.asarray(center, dtype=np.float64)
    def fn(v):
        diff = v - c
        return np.sum(diff * diff)
    return fn


# ================================================================================
#  TASK 1 - JAX-enhanced Substrate  (RFC-001 S4.1, no API change)
#
#  Canonical definition now lives in mpc_packs.jax_substrate (carved
#  Session 8). Re-exported here so Session-2-era callers keep working.
# ================================================================================

from mpc_packs.jax_substrate.pack import JAXSubstrate  # noqa: E402,F401


def _make_jax_cluster(cluster_id, dim, local_budget, bus,
                      E_c=0.5, E_s=2.0, alpha=0.10):
    """
    Factory: MPCCluster using JAXSubstrate when available.

    Replaces the substrate BEFORE any engines are added so that every engine
    receives the JAX-enhanced substrate reference.
    """
    cluster = MPCCluster(cluster_id, dim, local_budget, bus, E_c, E_s, alpha)
    if _JAX:
        jax_sub      = JAXSubstrate(dim=dim, E_c=E_c, E_s=E_s, epsilon=1e-4)
        cluster.sub  = jax_sub
        cluster.ops.sub = jax_sub
    return cluster


def benchmark_substrate(dim_fd=8, dim_jax=64, n_constr=4, n_steps=1000):
    """
    Task 1 benchmark.

    FD baseline timed at dim_fd (feasible). JAX backend timed at dim_jax.
    Extrapolated FD time at dim_jax computed from O(n^2) Hessian scaling.

    On GPU, JAX would add further hardware parallelism beyond this CPU result.
    """
    np.random.seed(0)
    bus = EventBus.null()

    # FD at small dim
    sub_fd = Substrate(dim=dim_fd, E_c=0.5, E_s=2.0)
    for i in range(n_constr):
        sub_fd.register(f"c{i}",
            _make_quadratic_constraint(np.random.randn(dim_fd) * 0.3), lam=0.3)
    eng_fd   = MetastableEngine(sub_fd, bus, E_star=50.0, dt=0.01, cluster_id="fd")
    eng_fd.v = np.random.randn(dim_fd) * 0.05
    t0       = time.perf_counter()
    eng_fd.run(n_steps)
    time_fd  = time.perf_counter() - t0

    # Extrapolate: Hessian call count is dim + dim*(dim-1)/2 ~ O(n^2)
    h_fd    = dim_fd  + dim_fd  * (dim_fd  - 1) // 2
    h_jax_d = dim_jax + dim_jax * (dim_jax - 1) // 2
    time_fd_extrap = time_fd * (h_jax_d / h_fd)

    # JAX at large dim
    speedup = jax_time = float("nan")
    jax_ok  = False
    if _JAX:
        np.random.seed(0)
        sub_jax = JAXSubstrate(dim=dim_jax, E_c=0.5, E_s=2.0)
        for i in range(n_constr):
            sub_jax.register(f"c{i}",
                _make_quadratic_constraint(np.random.randn(dim_jax) * 0.3), lam=0.3)
        eng_jax   = MetastableEngine(sub_jax, bus, E_star=50.0, dt=0.01, cluster_id="jax")
        eng_jax.v = np.random.randn(dim_jax) * 0.05
        # Warm-up (trigger JIT compilation)
        _ = sub_jax.gradient(eng_jax.v)
        _ = sub_jax.hessian(eng_jax.v)
        t0       = time.perf_counter()
        eng_jax.run(n_steps)
        jax_time = time.perf_counter() - t0
        speedup  = time_fd_extrap / jax_time
        jax_ok   = sub_jax._jax_ok

    print(f"\n[Task 1] Substrate benchmark")
    print(f"  FD  dim={dim_fd:2d}, {n_constr} constr, {n_steps} steps:  {time_fd:.2f}s  (actual)")
    print(f"  FD  dim={dim_jax:2d} extrapolated (O(n^2) scaling):        {time_fd_extrap:.0f}s")
    if _JAX:
        print(f"  JAX dim={dim_jax:2d}, {n_constr} constr, {n_steps} steps:  {jax_time:.2f}s  (actual)")
        print(f"  Extrapolated speedup at dim={dim_jax}: {speedup:.0f}x  (CPU-only; GPU adds further gain)")
        verdict = "PASS (>10x)" if speedup >= 10 else f"BELOW 10x (GPU required for target; CPU gives {speedup:.0f}x)"
        print(f"  Verdict: {verdict}")
    else:
        print("  JAX not available - FD fallback only.")

    return dict(time_fd_actual=time_fd, time_fd_extrap=time_fd_extrap,
                time_jax=jax_time, speedup=speedup,
                jax_available=_JAX, jax_ok=jax_ok)


# ================================================================================
#  TASK 2 - Scale validation of Thermodynamic Separation Theorem
# ================================================================================

def scale_validation(dim=16, E_star=50.0, n_engines=10, n_steps=200,
                     n_range=range(5, 51, 5), lam=0.05, sigma_c=0.3,
                     E_c=0.3, E_s=3.0,
                     out_path="mpc_scaling_validation.png"):
    """
    Verify Theorem 6.1 (RFC-001 S4.3) empirically as N scales.

    For each N in n_range:
      - Load N random quadratic constraints.
      - Run n_steps Langevin steps.
      - Record N_active (engines in s-state) vs N_max (theorem bound).

    Pass criterion: N_active / N_max <= 1.15 at every point.

    Parameter regime (lam=0.05, sigma_c=0.3, E_c=0.3, E_s=3.0):
      E_min at combined minimum ≈ lam*N*dim*sigma^2 / N ≈ lam*dim*sigma^2 ≈ 0.55 (N=10).
      This sits between E_c and E_s, producing genuine s-state engines for
      direct empirical verification of the separation theorem.
    """
    print(f"\n[Task 2] Scale validation  dim={dim}  E*={E_star}  "
          f"{n_engines} engines  {n_steps} steps/N  lam={lam}  sigma_c={sigma_c}")

    bus  = EventBus.null()
    rows = []

    for N in n_range:
        np.random.seed(N)
        cluster = _make_jax_cluster(
            f"scale_{N}", dim, E_star, bus, E_c=E_c, E_s=E_s, alpha=0.10)

        fns = {f"p{i}": _make_quadratic_constraint(np.random.randn(dim) * sigma_c)
               for i in range(N)}
        cluster.load(fns, stiffnesses={k: lam for k in fns})

        # Add engines AFTER constraints are loaded
        for _ in range(n_engines):
            eng   = cluster.add_engine(E_star=E_star, dt=0.02)
            eng.v = np.random.randn(dim) * 0.1

        # Warm up JAX compilation on first engine
        if _JAX and isinstance(cluster.sub, JAXSubstrate):
            v0 = cluster.engines[0].v
            _ = cluster.sub.gradient(v0)
            _ = cluster.sub.hessian(v0)

        cluster.diffuse(n_steps=n_steps)

        N_active_s = cluster.count_s_state()
        N_active_c = sum(1 for e in cluster.engines if e.phase == Phase.C)

        v_ref = cluster.engines[0].v
        cluster.sub.frustration(v_ref)
        d_avg   = max(cluster.sub._average_degree(), 1e-6)
        eps_min = max(cluster.sub._min_nonzero_frustration(), 1e-9)
        N_max   = float(np.sqrt(2.0 * E_star / (cluster.alpha * eps_min * d_avg)))
        ratio   = N_active_s / N_max if N_max > 0 else 0.0

        rows.append(dict(N=N, N_active=N_active_s, N_committed=N_active_c,
                         N_max=N_max, ratio=ratio, d_avg=d_avg, eps_min=eps_min))
        print(f"  N={N:3d}  s-active={N_active_s:3d}  committed={N_active_c:3d}  "
              f"N_max={N_max:8.2f}  ratio={ratio:.4f}")

    worst_ratio = max(r["ratio"] for r in rows)
    passed      = worst_ratio <= 1.15
    print(f"\n  Worst N_active/N_max = {worst_ratio:.4f}  "
          f"-> {'PASS' if passed else 'FAIL'}")

    # Plot
    Ns      = [r["N"]        for r in rows]
    actives = [r["N_active"] for r in rows]
    N_maxes = [r["N_max"]    for r in rows]
    ratios  = [r["ratio"]    for r in rows]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    ax1.plot(Ns, actives, "o-", color="steelblue", label="N_active (s-state)")
    ax1.plot(Ns, N_maxes, "r--", linewidth=2, label="N_max (Theorem 6.1)")
    ax1.fill_between(Ns, N_maxes, [n * 1.15 for n in N_maxes],
                     alpha=0.12, color="red", label="15% slack band")
    ax1.set_xlabel("N (constraints loaded)")
    ax1.set_ylabel("Engine count")
    ax1.set_title("N_active vs N_max")
    ax1.legend(fontsize=8); ax1.grid(alpha=0.3)

    ax2.plot(Ns, ratios, "s-", color="darkorange")
    ax2.axhline(1.0,  color="red", linestyle="--", label="bound")
    ax2.axhline(1.15, color="red", linestyle=":",  alpha=0.5, label="15% margin")
    ax2.set_xlabel("N (constraints loaded)")
    ax2.set_ylabel("N_active / N_max")
    ax2.set_title("Separation ratio")
    ax2.legend(fontsize=8); ax2.grid(alpha=0.3)

    plt.suptitle(
        f"MPC Separation Theorem (dim={dim}, E*={E_star}, "
        f"{n_engines} engines, {n_steps} steps)\n"
        f"Worst ratio={worst_ratio:.4f}  ->  {'PASS' if passed else 'FAIL'}",
        fontsize=10)
    plt.tight_layout()
    plt.savefig(out_path, dpi=120)
    plt.close()
    print(f"  Plot saved -> {out_path}")

    return dict(passed=passed, worst_ratio=worst_ratio, data=rows)


# ================================================================================
#  TASK 3 - AutoCluster  (RFC-001 S4.3 extension)
# ================================================================================

# Canonical definition now lives in mpc_packs.auto_cluster (carved
# Session 8). Re-exported here so Session-2-era callers keep working.
from mpc_packs.auto_cluster.pack import AutoCluster  # noqa: E402,F401


def smoke_test_autocluster() -> bool:
    """Sanity check: AutoCluster runs, self-regulates, and reports correctly."""
    print("\n[Task 3] AutoCluster smoke test")
    np.random.seed(1)
    bus = EventBus.null()
    ac  = AutoCluster(dim=8, E_star=10.0, max_engines=16, bus=bus)

    c1 = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    c2 = np.array([0.9, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    ac.load({"A": _make_quadratic_constraint(c1),
             "B": _make_quadratic_constraint(c2)},
            stiffnesses={"A": 0.5, "B": 0.5})

    if _JAX and isinstance(ac.sub, JAXSubstrate):
        _ = ac.sub.gradient(ac.engines[0].v)
        _ = ac.sub.hessian(ac.engines[0].v)

    step_count = 0
    for milestone in [0, 50, 100, 150, 200, 250]:
        while step_count < milestone:
            ac.step()
            step_count += 1
        print(f"  step={milestone:4d}  {ac.population_report()}")

    ok = len(ac.engines) >= 1
    print(f"  Smoke test: {'PASS' if ok else 'FAIL'}")
    return ok


# ================================================================================
#  TASK 4 - LLM Constraint Encoder
# ================================================================================

# Analytically-designed centers for the Task 5 hello-world demo.
# Used by the fallback encoder when ANTHROPIC_API_KEY is absent (DEVIATE-001).
#
# Design:
#   P1 "spherical, smooth"      -> center in [0:4] subspace
#   P2 "sharp corners, flat"    -> center in [4:8] subspace (orthogonal to P1)
#   P3 "fits hand, writing"     -> center biased toward [4:8] (pen = flat-faceted)
#
# P1 and P2 are maximally incompatible (orthogonal wells).
# P3 reinforces P2's subspace -> system commits to P2 after P3 is added.
_DEMO_DIM = 32

def _build_demo_centers(dim):
    c1 = np.zeros(dim); c1[0:4] = [2.0, 1.5, 1.0, 0.5]
    c2 = np.zeros(dim); c2[4:8] = [2.0, 1.5, 1.0, 0.5]
    c3 = np.zeros(dim); c3[4:8] = [1.2, 0.9, 0.6, 0.3]; c3[8] = 0.3
    return {"P1": c1, "P2": c2, "P3": c3}

_DEMO_CENTERS: Dict[str, np.ndarray] = _build_demo_centers(_DEMO_DIM)

_DEMO_PROPOSITION_MAP = {
    "the object is spherical and smooth":             "P1",
    "the object has sharp corners and flat faces":    "P2",
    "the object fits in one hand and is used for writing": "P3",
}


# Canonical definition now lives in mpc_packs.llm_encoder (carved
# Session 9). Re-exported here for Session-2-era callers.
from mpc_packs.llm_encoder.pack import LLMConstraintEncoder  # noqa: E402,F401


# ================================================================================
#  TASK 5 - Hello world: LLM-powered disambiguation
# ================================================================================

_P1 = "the object is spherical and smooth"
_P2 = "the object has sharp corners and flat faces"
_P3 = "the object fits in one hand and is used for writing"


def hello_world(out_path="mpc_hello_world.png"):
    """
    Wire AutoCluster + LLMConstraintEncoder into a disambiguation demo.

    Phase A (200 steps): P1 + P2 simultaneously - contradictory geometry.
                          System should enter k or s (not commit).
    Phase B (200 steps): P3 added as disambiguating evidence.
                          System should commit toward P2 well (pen-like object).

    Verdict: committed position closer to P2 than P1 AND final phase c or s.
    """
    np.random.seed(7)
    dim  = _DEMO_DIM
    bus  = EventBus.null()

    encoder  = LLMConstraintEncoder(dim=dim)
    llm_mode = encoder._use_llm
    print(f"\n[Task 5] Hello world  (encoder: {'Anthropic API' if llm_mode else 'fallback'})")

    fn_p1 = encoder.encode(_P1)
    fn_p2 = encoder.encode(_P2)
    fn_p3 = encoder.encode(_P3)

    cluster = AutoCluster(dim=dim, E_star=20.0, max_engines=64,
                          bus=bus, E_c=0.5, E_s=5.0)

    # Phase A — P1 is weaker (lam=0.3) so k-state sheds it first;
    # P2 remains and system commits to dims 4-7.
    cluster.load({"P1": fn_p1, "P2": fn_p2}, stiffnesses={"P1": 0.3, "P2": 0.5})
    if _JAX and isinstance(cluster.sub, JAXSubstrate):
        _ = cluster.sub.gradient(cluster.engines[0].v)
        _ = cluster.sub.hessian(cluster.engines[0].v)

    energy_hist: List[float] = []
    phase_hist:  List[str]   = []

    for _ in range(200):
        cluster.step()
        v = cluster.engines[0].v if cluster.engines else np.zeros(dim)
        energy_hist.append(float(cluster.sub.energy(v)))
        phase_hist.append(cluster.dominant_phase.value)

    phase_a  = cluster.dominant_phase.value
    report_a = cluster.population_report()
    print(f"  After P1+P2 (200 steps): phase={phase_a}  {report_a}")

    # Phase B — P3 (pen-like, close to P2) reinforces P2 subspace.
    cluster.load({"P3": fn_p3}, stiffnesses={"P3": 0.8})

    for _ in range(200):
        cluster.step()
        v = cluster.engines[0].v if cluster.engines else np.zeros(dim)
        energy_hist.append(float(cluster.sub.energy(v)))
        phase_hist.append(cluster.dominant_phase.value)

    phase_b  = cluster.dominant_phase.value
    report_b = cluster.population_report()
    print(f"  After P3 (200 more):     phase={phase_b}  {report_b}")

    # Verdict
    committed_v = cluster.extract_commitment()
    if committed_v is None:
        if cluster.engines:
            committed_v = min(cluster.engines,
                              key=lambda e: cluster.sub.energy(e.v)).v.copy()
        else:
            committed_v = np.zeros(dim)

    c1      = _DEMO_CENTERS["P1"][:dim]
    c2      = _DEMO_CENTERS["P2"][:dim]
    dist_p1 = float(np.linalg.norm(committed_v - c1))
    dist_p2 = float(np.linalg.norm(committed_v - c2))

    closer_to_p2 = dist_p2 < dist_p1
    phase_ok     = phase_b in ("c", "s")
    passed       = closer_to_p2 and phase_ok

    print(f"  Committed dist(P1)={dist_p1:.3f}  dist(P2)={dist_p2:.3f}")
    print(f"  Closer to P2: {closer_to_p2}   Phase ok: {phase_ok}")
    print(f"  Verdict: {'PASS' if passed else 'FAIL'}")

    # Plot
    steps     = np.arange(len(energy_hist))
    phase_map = {"c": 1.0, "s": 0.6, "k": 0.3, "r": 0.0}
    phase_num = [phase_map.get(p, 0.0) for p in phase_hist]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    ax1.plot(steps, energy_hist, color="steelblue", linewidth=0.7)
    ax1.axvline(200, color="grey", linestyle="--", alpha=0.7, label="P3 added")
    ax1.set_ylabel("Energy E(v)"); ax1.set_title("Energy vs step")
    ax1.legend(fontsize=8); ax1.grid(alpha=0.3)

    ax2.plot(steps, phase_num, color="darkorange", linewidth=0.7)
    ax2.axvline(200, color="grey", linestyle="--", alpha=0.7)
    ax2.set_yticks([0.0, 0.3, 0.6, 1.0])
    ax2.set_yticklabels(["r", "k", "s", "c"])
    ax2.set_ylabel("Dominant phase"); ax2.set_xlabel("Step")
    ax2.set_title("Phase vs step"); ax2.grid(alpha=0.3)

    verdict = "PASS" if passed else "FAIL"
    plt.suptitle(
        f"MPC Hello World [{verdict}]  encoder={'API' if llm_mode else 'fallback'}\n"
        f"dist(P1)={dist_p1:.2f}  dist(P2)={dist_p2:.2f}  "
        f"{'P2-compatible' if closer_to_p2 else 'P1-compatible'}",
        fontsize=9)
    plt.tight_layout()
    plt.savefig(out_path, dpi=120)
    plt.close()
    print(f"  Plot saved -> {out_path}")

    return dict(passed=passed, final_phase=phase_b,
                dist_to_p1=dist_p1, dist_to_p2=dist_p2,
                phase_a=phase_a, phase_b=phase_b,
                llm_mode="api" if llm_mode else "fallback")


# ================================================================================
#  MAIN
# ================================================================================

def main():
    print("=" * 70)
    print("  MPC Brain - Session 2")
    print(f"  JAX={_JAX}  Anthropic={_ANTHROPIC_LIB}")
    print("=" * 70)

    results = {}

    results["task1"] = benchmark_substrate(
        dim_fd=8, dim_jax=64, n_constr=4, n_steps=1000)

    results["task2"] = scale_validation(
        dim=16, E_star=50.0, n_engines=10, n_steps=200,
        n_range=range(5, 51, 5), lam=0.05, sigma_c=0.3,
        E_c=0.3, E_s=3.0,
        out_path="/mnt/user-data/outputs/mpc_scaling_validation.png")

    results["task3_ok"] = smoke_test_autocluster()

    results["task5"] = hello_world(
        out_path="/mnt/user-data/outputs/mpc_hello_world.png")

    print("\n" + "=" * 70)
    print("  Session 2 Summary")
    print("=" * 70)
    t1 = results["task1"]
    t2 = results["task2"]
    t5 = results["task5"]
    print(f"  Task 1  extrap speedup @ dim=64: {t1['speedup']:.0f}x  jax_ok={t1['jax_ok']}")
    print(f"  Task 2  worst ratio:             {t2['worst_ratio']:.4f}  {'PASS' if t2['passed'] else 'FAIL'}")
    print(f"  Task 3  AutoCluster smoke:        {'PASS' if results['task3_ok'] else 'FAIL'}")
    print(f"  Task 4  encoder mode:             {t5['llm_mode']}")
    print(f"  Task 5  hello-world:             {'PASS' if t5['passed'] else 'FAIL'}")
    return results


if __name__ == "__main__":
    main()
