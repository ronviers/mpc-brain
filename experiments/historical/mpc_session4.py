"""
mpc_session4.py — MPC Brain Session 4
======================================
Implements:
  AMEND-005  Effector                — total-cost accounting per commitment
  AMEND-006  PersistenceSubstrate    — usage + outcome coupled τ
             PersistenceCluster      — traversal + reinforcement wiring
             InstrumentedEngine      — extends PhaseTransitionEvent with energy
  TASK-4     Persistence + Effector Network Demo

Conforms to RFC-001-MPC-BRAIN + RFC-001-AMENDMENTS-A (April 2026).

RFC-001 invariants respected throughout:
  * Phase classification by energy and Hessian only (§3.1)
  * Every reset emits LandauerEvent (§3.2)
  * No step exceeds E* (§3.3)
  * Suspended engines exert maintenance force (§3.4)
  * Every brain component holds exactly one Substrate and one Bus
  * No brain component holds a Calorimeter or Effector reference
  * Effector holds neither Substrate nor Bus (reads via events only)
"""

from __future__ import annotations

import logging
import os
import sys
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Anthropic library availability ───────────────────────────────────────────
try:
    import anthropic as _anthropic_mod  # noqa: F401
    _ANTHROPIC_LIB = True
except ImportError:
    _ANTHROPIC_LIB = False

# ── Session 1/2/3 imports ────────────────────────────────────────────────────
_HERE = "/mnt/project"
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from mpc_engine_rfc001 import (  # noqa: E402
    Phase, EventBus, Substrate,
    MetastableEngine, MPCCluster, Calorimeter,
    ConstraintHandle, LandauerEvent, BudgetResetEvent,
    PhaseTransitionEvent,
)
# The S4 shadow of PhaseTransitionEvent has been retired — the canonical
# kernel type (re-exported by mpc_engine_rfc001) now carries the `energy`
# field that AMEND-005 originally added as a shadow.

from mpc_session2 import (  # noqa: E402
    JAXSubstrate, AutoCluster, LLMConstraintEncoder,
    _make_quadratic_constraint,
)
from mpc_session3 import (  # noqa: E402
    DecayingSubstrate, LateralCluster,
    ConstraintSpec, ObservationSocket, AnthropicSocket,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)


# =============================================================================
#  Step 1 — PhaseTransitionEvent (AMEND-005 — energy field)
# =============================================================================
#
# The S4 spec added an `energy` field to PhaseTransitionEvent so the Effector
# can read E(v_c) at commitment time without touching a Substrate. That
# field now lives on the canonical kernel type (carved in Session 6); this
# module imports it from mpc_engine_rfc001 (which re-exports the kernel
# version). The original S4 shadow class has been retired — Session 4's
# transitional type-split is no longer needed because all three sources
# (kernel, monolith, S4) now yield the same class object.
#
# Subscribers that bind to mpc_engine_rfc001.PhaseTransitionEvent,
# mpc_kernel.rfc001.events.PhaseTransitionEvent, or this module's
# PhaseTransitionEvent all receive events from InstrumentedEngine.


# =============================================================================
#  Step 2 — InstrumentedEngine (AMEND-006 & AMEND-005 support)
#
#  Canonical definition now lives in mpc_packs.persistence_substrate
#  (carved Session 9). Re-exported here for Session-4-era callers.
# =============================================================================

from mpc_packs.persistence_substrate.pack import InstrumentedEngine  # noqa: E402,F401


# =============================================================================
#  Step 3 — EffectorEvent & Effector  (AMEND-005)
#
#  Canonical definitions live in mpc_packs.effector (carved Session 8).
#  Re-exported here so Session-4-era importers (persistence_substrate,
#  maze) resolve the same class objects across import paths.
# =============================================================================

from mpc_packs.effector.pack import Effector, EffectorEvent  # noqa: E402,F401


# =============================================================================
#  Step 4 — test_amend005
# =============================================================================

def test_amend005() -> bool:
    """
    AMEND-005 acceptance test.

    Setup: dim=8, E*=10, one quadratic constraint at c=[2,0,…,0] with λ=0.8.
    Use InstrumentedEngine directly (no cluster).  Run up to 2000 steps or
    until at least one EffectorEvent is emitted.  If none, force a commit by
    placing the engine just outside the c-basin and stepping one more time.

    Acceptance:
      1. at least one EffectorEvent
      2. event.energy_at_c   >= 0
      3. event.landauer_cost >= 0
      4. event.work_estimate >= 0
      5. event.total_cost == sum of the three (within 1e-9)
    """
    print("\n" + "=" * 62)
    print("  [AMEND-005]  Effector — total-cost accounting")
    print("=" * 62)
    np.random.seed(7)

    DIM     = 8
    E_STAR  = 10.0
    LAM     = 0.8

    bus      = EventBus()
    effector = Effector().attach(bus)

    # One quadratic constraint, centre c = [2, 0, 0, ...].
    sub = Substrate(dim=DIM, E_c=0.5, E_s=2.0)
    c   = np.zeros(DIM); c[0] = 2.0
    sub.register("well", _make_quadratic_constraint(c), lam=LAM)

    # λ_avg supplied externally (Effector never reads Substrate).
    effector.register_cluster("test", LAM)

    eng = InstrumentedEngine(
        substrate  = sub,
        bus        = bus,
        E_star     = E_STAR,
        dt         = 0.02,
        cluster_id = "test",
    )
    eng.v = np.zeros(DIM)   # starts in K-basin (E=3.2 > E_s=2.0)

    committed = False
    for _ in range(2000):
        eng.step()
        if effector.effector_events("test"):
            committed = True
            break

    if not committed:
        # Fallback: place v just outside C-basin, then step so the next
        # classify() crosses into C-basin.  The first step starts from a
        # non-C position (S-phase) and the dynamics pull v into C.
        log.warning("test_amend005: no natural commit in 2000 steps — forcing")
        eng.v = c * 0.6            # E = 0.8 * 0.16 * 4 = 0.512 (S-phase)
        # Drive it into the C-basin with a few steps.
        for _ in range(40):
            eng.step()
            if effector.effector_events("test"):
                committed = True
                break

    events = effector.effector_events("test")
    print(f"  emitted EffectorEvents: {len(events)}")

    if not events:
        print("  ✗ no EffectorEvents emitted")
        return False

    ev = events[0]
    print(f"  first event:")
    print(f"    energy_at_c   = {ev.energy_at_c:.6f}")
    print(f"    landauer_cost = {ev.landauer_cost:.6f}")
    print(f"    work_estimate = {ev.work_estimate:.6f}")
    print(f"    total_cost    = {ev.total_cost:.6f}")

    check1 = len(events) >= 1
    check2 = ev.energy_at_c   >= 0
    check3 = ev.landauer_cost >= 0
    check4 = ev.work_estimate >= 0
    sum3   = ev.energy_at_c + ev.landauer_cost + ev.work_estimate
    check5 = abs(ev.total_cost - sum3) < 1e-9

    print(f"  check1 (>=1 event)          : {'PASS' if check1 else 'FAIL'}")
    print(f"  check2 (energy_at_c>=0)     : {'PASS' if check2 else 'FAIL'}")
    print(f"  check3 (landauer_cost>=0)   : {'PASS' if check3 else 'FAIL'}")
    print(f"  check4 (work_estimate>=0)   : {'PASS' if check4 else 'FAIL'}")
    print(f"  check5 (total=sum of parts) : {'PASS' if check5 else 'FAIL'}  "
          f"|Δ|={abs(ev.total_cost - sum3):.2e}")

    ok = all([check1, check2, check3, check4, check5])
    print(f"  AMEND-005: {'PASS' if ok else 'FAIL'}")
    return ok


# =============================================================================
#  Step 5/6  PersistenceSubstrate / PersistenceCluster (AMEND-006)
#
#  Canonical definitions now live in mpc_packs.persistence_substrate
#  (carved Session 9). Re-exported here so Session-4-era callers resolve
#  the same class objects.
# =============================================================================

from mpc_packs.persistence_substrate.pack import (  # noqa: E402,F401
    PersistenceSubstrate,
    PersistenceCluster,
)


# =============================================================================
#  Step 7 — test_amend006
# =============================================================================

def test_amend006() -> bool:
    """AMEND-006 acceptance tests: usage and outcome channels on PersistenceSubstrate."""
    print("\n" + "=" * 62)
    print("  [AMEND-006]  PersistenceSubstrate — usage + outcome")
    print("=" * 62)

    # ── Test A — passive rehearsal (usage) ────────────────────────────────────
    print("\n  Test A: usage (passive rehearsal)")
    np.random.seed(11)
    DIM = 8

    def _build_active_idle():
        """Return two identical-config PersistenceSubstrates seeded with same frustration."""
        def build(usage_coef):
            s = PersistenceSubstrate(
                dim=DIM, E_c=0.5, E_s=2.0, epsilon=1e-4,
                tau_base=500.0,
                usage_coefficient=usage_coef,
                outcome_coefficient=0.0,
            )
            c_A = np.zeros(DIM); c_A[0] = 0.5
            c_B = np.zeros(DIM); c_B[0] = 1.0
            s.register("A", _make_quadratic_constraint(c_A), lam=1.0)
            s.register("B", _make_quadratic_constraint(c_B), lam=1.0)
            # Seed _decay_cache by calling frustration() at v=0.
            s.frustration(np.zeros(DIM))
            return s
        return build(2.0), build(2.0)   # both use usage_coefficient=2.0

    s_active, s_idle = _build_active_idle()

    # s_active sees heavy traversal on (A,B); s_idle sees none.
    for _ in range(100):
        s_active.record_traversal("A", "B")

    for _ in range(200):
        s_active.decay_step()
        s_idle.decay_step()

    eps_active = s_active._decay_cache.get(("A", "B"), 0.0)
    eps_idle   = s_idle._decay_cache.get(("A", "B"),   0.0)
    print(f"    ε_active (100 traversals) = {eps_active:.6f}")
    print(f"    ε_idle   (  0 traversals) = {eps_idle:.6f}")
    test_a = eps_active > eps_idle
    print(f"    Test A: {'PASS' if test_a else 'FAIL'}")

    # ── Test B — active reinforcement (outcome) ──────────────────────────────
    print("\n  Test B: outcome (active reinforcement)")
    s_out = PersistenceSubstrate(
        dim=DIM, E_c=0.5, E_s=2.0, epsilon=1e-4,
        tau_base=500.0,
        usage_coefficient=0.0,
        outcome_coefficient=0.3,
    )
    # Seed state manually (no frustration() call needed for this check).
    s_out._decay_cache[("A", "B")] = 0.3
    s_out._original_eps[("A", "B")] = 1.0
    s_out._active_pairs.add(("A", "B"))   # keep it active so apply_outcome path works

    s_out.apply_outcome("A")
    eps_after = s_out._decay_cache[("A", "B")]
    expected  = min(0.3 + 0.3 * 1.0, 1.0)
    print(f"    ε_ij after apply_outcome = {eps_after:.6f}  (expected {expected:.6f})")
    test_b = abs(eps_after - expected) < 1e-9
    print(f"    Test B: {'PASS' if test_b else 'FAIL'}")

    ok = test_a and test_b
    print(f"\n  AMEND-006 overall: {'PASS' if ok else 'FAIL'}")
    return ok, test_a, test_b


# =============================================================================
#  Step 8 — Network demo (TASK-4)
# =============================================================================

def run_network_demo_s4(
    out_path: str = "/mnt/user-data/outputs/mpc_network_demo_s4.png",
) -> Dict[str, Any]:
    """
    Persistence + Effector Network Demo.

    DIM=16, E*=20, max_engines=4, tau_base=80, N_PHASE=80.
    AnthropicSocket with real API (fallback logged per-proposition on failure).

    Hard acceptance (TASK-4 PASS requires all):
      1. No crash over 2×N_PHASE steps.
      2. len(cluster_A.engines) >= 1 AND len(cluster_B.engines) >= 1 at end.
      3. Plot saved.
    """
    print("\n" + "=" * 62)
    print("  [TASK-4]  Persistence + Effector Network Demo")
    print("=" * 62)
    np.random.seed(2026)

    DIM                 = 16
    E_STAR              = 20.0
    MAX_ENGINES         = 4
    TAU_BASE            = 80.0
    USAGE_COEF          = 1.0
    OUTCOME_COEF        = 0.2
    N_PHASE             = 80

    bus      = EventBus()
    effector = Effector().attach(bus)

    # Sockets (one per cluster, both share the bus implicitly via their clusters).
    socket_A = AnthropicSocket(dim=DIM); socket_A.connect()
    socket_B = AnthropicSocket(dim=DIM); socket_B.connect()
    conn_A = socket_A._connected
    conn_B = socket_B._connected
    conn_mode = "API" if (conn_A and conn_B) else "fallback"
    print(f"  Encoding mode: {conn_mode}  "
          f"(A={'API' if conn_A else 'fallback'}, "
          f"B={'API' if conn_B else 'fallback'})")
    print(f"  dim={DIM}  E*={E_STAR}  max_eng={MAX_ENGINES}  "
          f"τ_base={TAU_BASE}  usage={USAGE_COEF}  outcome={OUTCOME_COEF}")

    # Clusters.
    cluster_A = PersistenceCluster(
        dim=DIM, E_star=E_STAR, max_engines=MAX_ENGINES, bus=bus,
        E_c=0.5, E_s=5.0, socket=socket_A,
        tau_base=TAU_BASE,
        usage_coefficient=USAGE_COEF, outcome_coefficient=OUTCOME_COEF,
    )
    cluster_B = PersistenceCluster(
        dim=DIM, E_star=E_STAR, max_engines=MAX_ENGINES, bus=bus,
        E_c=0.5, E_s=5.0, socket=socket_B,
        tau_base=TAU_BASE,
        usage_coefficient=USAGE_COEF, outcome_coefficient=OUTCOME_COEF,
    )

    # ── Encode initial propositions ──────────────────────────────────────────
    props_A = [
        ("the system is in a low-energy ground state",   0.7),
        ("the system exhibits periodic oscillation",     0.5),
    ]
    props_B = [
        ("the system is in a high-energy excited state", 0.7),
        ("the system exhibits chaotic behaviour",        0.5),
    ]
    shared_prop = ("the system is at a critical transition point", 0.4)

    print("  Encoding Cluster A propositions …")
    for prop, stiff in props_A:
        socket_A.observe(prop, strength=stiff)
    specs_a = socket_A.flush()
    cluster_A.load(
        {s.label: s.fn      for s in specs_a},
        stiffnesses={s.label: s.lambda_ for s in specs_a},
    )
    print("  Encoding Cluster B propositions …")
    for prop, stiff in props_B:
        socket_B.observe(prop, strength=stiff)
    specs_b = socket_B.flush()
    cluster_B.load(
        {s.label: s.fn      for s in specs_b},
        stiffnesses={s.label: s.lambda_ for s in specs_b},
    )

    lam_avg_A = float(np.mean([s.lambda_ for s in specs_a]))
    lam_avg_B = float(np.mean([s.lambda_ for s in specs_b]))
    effector.register_cluster(cluster_A.cluster_id, lam_avg_A)
    effector.register_cluster(cluster_B.cluster_id, lam_avg_B)
    print(f"    λ_avg: A={lam_avg_A:.3f}  B={lam_avg_B:.3f}")

    # ── Tracking arrays ──────────────────────────────────────────────────────
    energy_A, energy_B = [], []
    phase_A,  phase_B  = [], []
    compat_trace       = []
    cum_cost_A_trace   = []
    cum_cost_B_trace   = []

    def _current_cum_cost(cid: str) -> float:
        return float(sum(e.total_cost for e in effector.effector_events(cid)))

    def _record():
        v_a = cluster_A.engines[0].v if cluster_A.engines else np.zeros(DIM)
        v_b = cluster_B.engines[0].v if cluster_B.engines else np.zeros(DIM)
        energy_A.append(float(cluster_A.sub.energy(v_a)))
        energy_B.append(float(cluster_B.sub.energy(v_b)))
        phase_A.append(cluster_A.dominant_phase.value)
        phase_B.append(cluster_B.dominant_phase.value)
        eps = cluster_A.cross_cluster_compatibility(cluster_B)
        compat_trace.append(float(eps.mean()) if eps.size else 0.0)
        cum_cost_A_trace.append(_current_cum_cost(cluster_A.cluster_id))
        cum_cost_B_trace.append(_current_cum_cost(cluster_B.cluster_id))

    # ── Phase 1 ──────────────────────────────────────────────────────────────
    print(f"  Phase 1: {N_PHASE} steps …")
    crashed = False
    try:
        for _ in range(N_PHASE):
            cluster_A.step()
            cluster_B.step()
            cluster_A.sub.decay_step()
            cluster_B.sub.decay_step()
            _record()
    except Exception as exc:
        crashed = True
        log.error(f"Phase 1 crashed: {exc}")

    compat_p1_start = compat_trace[0] if compat_trace else 0.0
    compat_p1_end   = compat_trace[-1] if compat_trace else 0.0
    print(f"    dominant A={cluster_A.dominant_phase.value}  "
          f"B={cluster_B.dominant_phase.value}")
    print(f"    compat step0={compat_p1_start:.4f}  step{N_PHASE}={compat_p1_end:.4f}")
    print(f"    engines A={len(cluster_A.engines)}  B={len(cluster_B.engines)}")

    # ── Phase 2 — add shared proposition ─────────────────────────────────────
    print(f"  Phase 2: add shared proposition + {N_PHASE} steps …")
    for sock, clust in [(socket_A, cluster_A), (socket_B, cluster_B)]:
        sock.observe(shared_prop[0], strength=shared_prop[1])
        sp = sock.flush()
        clust.load(
            {s.label: s.fn      for s in sp},
            stiffnesses={s.label: s.lambda_ for s in sp},
        )

    # Update registered λ_avg to reflect phase-2 complement.
    all_A_specs = specs_a + [ConstraintSpec(
        fn=lambda v: 0.0, lambda_=shared_prop[1],
        label="shared", modality="text")]
    all_B_specs = specs_b + [ConstraintSpec(
        fn=lambda v: 0.0, lambda_=shared_prop[1],
        label="shared", modality="text")]
    effector.register_cluster(
        cluster_A.cluster_id,
        float(np.mean([s.lambda_ for s in all_A_specs])),
    )
    effector.register_cluster(
        cluster_B.cluster_id,
        float(np.mean([s.lambda_ for s in all_B_specs])),
    )

    try:
        for _ in range(N_PHASE):
            cluster_A.step()
            cluster_B.step()
            cluster_A.sub.decay_step()
            cluster_B.sub.decay_step()
            _record()
    except Exception as exc:
        crashed = True
        log.error(f"Phase 2 crashed: {exc}")

    compat_p2_end = compat_trace[-1] if compat_trace else 0.0
    n_eng_a = len(cluster_A.engines)
    n_eng_b = len(cluster_B.engines)
    print(f"    dominant A={cluster_A.dominant_phase.value}  "
          f"B={cluster_B.dominant_phase.value}")
    print(f"    compat step{2*N_PHASE}: {compat_p2_end:.4f}")
    print(f"    engines A={n_eng_a}  B={n_eng_b}")

    # ── Informational metrics (not part of PASS/FAIL) ────────────────────────
    if abs(compat_p1_start) > 1e-9:
        change_pct = abs(compat_p2_end - compat_p1_start) / abs(compat_p1_start) * 100.0
    else:
        change_pct = 0.0
    routing_evolved = change_pct > 5.0
    print(f"  Compat change: {change_pct:.1f}%  "
          f"→ {'routing EVOLVED' if routing_evolved else 'routing stable'}")

    all_eff_events = effector.effector_events()
    if all_eff_events:
        costs = [e.total_cost for e in all_eff_events]
        print(f"  EffectorEvents emitted: {len(all_eff_events)}  "
              f"total_cost min={min(costs):.3f} "
              f"mean={float(np.mean(costs)):.3f} "
              f"max={max(costs):.3f}")
    else:
        print("  EffectorEvents emitted: 0  (no commits during run)")

    trav_total_A = cluster_A.sub._total_traversals
    trav_total_B = cluster_B.sub._total_traversals
    print(f"  Traversal counts: A={trav_total_A}  B={trav_total_B}")

    # ── 5-panel figure ───────────────────────────────────────────────────────
    phase_map   = {"c": 3, "s": 2, "k": 1, "r": 0}
    total_steps = len(energy_A)
    steps       = np.arange(total_steps)

    fig = plt.figure(figsize=(14, 10))
    fig.suptitle(
        "MPC Brain Session 4 — Persistence + Effector Network Demo\n"
        f"dim={DIM}  E*={E_STAR}  τ_base={TAU_BASE}  "
        f"usage={USAGE_COEF}  outcome={OUTCOME_COEF}  "
        f"encoding={conn_mode}  "
        f"commits={len(all_eff_events)}  "
        f"Δε̄={change_pct:.1f}%",
        fontsize=10,
    )
    gs = fig.add_gridspec(3, 2)

    # Panel 1: Energy A
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(steps, energy_A, color="steelblue", linewidth=0.7)
    ax1.axvline(N_PHASE, color="grey", linestyle="--", alpha=0.6, label="shared prop")
    ax1.set_title("Cluster A — Energy trace")
    ax1.set_xlabel("Step"); ax1.set_ylabel("E(v)  [k_BT]")
    ax1.legend(fontsize=7); ax1.grid(alpha=0.3)

    # Panel 2: Energy B
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(steps, energy_B, color="darkorange", linewidth=0.7)
    ax2.axvline(N_PHASE, color="grey", linestyle="--", alpha=0.6, label="shared prop")
    ax2.set_title("Cluster B — Energy trace")
    ax2.set_xlabel("Step"); ax2.set_ylabel("E(v)  [k_BT]")
    ax2.legend(fontsize=7); ax2.grid(alpha=0.3)

    # Panel 3: Dominant phase, A and B
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.plot(steps, [phase_map.get(p, 0) for p in phase_A],
             color="steelblue", linewidth=0.9, label="Cluster A")
    ax3.plot(steps, [phase_map.get(p, 0) for p in phase_B],
             color="darkorange", linewidth=0.9, linestyle="--", label="Cluster B")
    ax3.axvline(N_PHASE, color="grey", linestyle="--", alpha=0.6)
    ax3.set_yticks([0, 1, 2, 3]); ax3.set_yticklabels(["r", "k", "s", "c"])
    ax3.set_title("Dominant phase  (A & B)")
    ax3.set_xlabel("Step"); ax3.legend(fontsize=7); ax3.grid(alpha=0.3)

    # Panel 4: Cross-cluster mean frustration
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.plot(steps, compat_trace, color="purple", linewidth=0.8)
    ax4.axvline(N_PHASE, color="grey", linestyle="--", alpha=0.6, label="shared prop")
    ax4.set_title("Cross-cluster mean frustration  ε̄(A, B)")
    ax4.set_xlabel("Step"); ax4.set_ylabel("ε̄")
    ax4.legend(fontsize=7); ax4.grid(alpha=0.3)

    # Panel 5: Cumulative total_cost per cluster
    ax5 = fig.add_subplot(gs[2, :])
    if max(max(cum_cost_A_trace, default=0.0),
           max(cum_cost_B_trace, default=0.0)) > 0.0:
        ax5.plot(steps, cum_cost_A_trace, color="steelblue",
                 linewidth=0.9, label=f"Cluster A (total={cum_cost_A_trace[-1]:.2f})")
        ax5.plot(steps, cum_cost_B_trace, color="darkorange",
                 linewidth=0.9, label=f"Cluster B (total={cum_cost_B_trace[-1]:.2f})")
    else:
        ax5.plot(steps, np.zeros(total_steps),
                 color="steelblue", label="Cluster A (no commits)")
        ax5.plot(steps, np.zeros(total_steps), color="darkorange",
                 linestyle="--", label="Cluster B (no commits)")
    ax5.axvline(N_PHASE, color="grey", linestyle="--", alpha=0.6, label="shared prop")
    ax5.set_title("Cumulative EffectorEvent total_cost")
    ax5.set_xlabel("Step"); ax5.set_ylabel("Σ total_cost  [k_BT]")
    ax5.legend(fontsize=7); ax5.grid(alpha=0.3)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(out_path, dpi=120)
    plt.close()
    print(f"  Plot saved → {out_path}")

    passed = (not crashed) and (n_eng_a >= 1) and (n_eng_b >= 1)
    print(f"  {'TASK-4 PASS' if passed else 'TASK-4 FAIL'}")

    return dict(
        passed=passed,
        crashed=crashed,
        n_eng_a=n_eng_a, n_eng_b=n_eng_b,
        compat_p1_start=compat_p1_start,
        compat_p1_end=compat_p1_end,
        compat_p2_end=compat_p2_end,
        change_pct=change_pct,
        routing_evolved=routing_evolved,
        n_eff_events=len(all_eff_events),
        cost_stats=(
            dict(min=float(min(e.total_cost for e in all_eff_events)),
                 max=float(max(e.total_cost for e in all_eff_events)),
                 mean=float(np.mean([e.total_cost for e in all_eff_events])))
            if all_eff_events else None
        ),
        trav_total_A=trav_total_A,
        trav_total_B=trav_total_B,
        conn_mode=conn_mode,
    )


# =============================================================================
#  Step 9 — Commit-dynamics supplementary demo (loose-end follow-up)
# =============================================================================

def demo_commit_dynamics(
    out_path: str = "/mnt/user-data/outputs/mpc_network_demo_s4_commits.png",
) -> Dict[str, Any]:
    """
    Supplementary demo (NOT part of the spec PASS criteria) that closes the
    AMEND-005 + AMEND-006 loop end-to-end inside a real PersistenceCluster.

    Why a separate demo?  The spec-compliant TASK-4 configuration produces
    well shapes with energy floors above E_c=0.5 (whether using LLM-encoded
    constraints or the high-stiffness wells in the spec), so commits do not
    naturally fire.  This demo uses two orthogonal quadratic wells with
    matched low stiffness so that |v−c_i|² · λ_avg < E_c at every basin floor,
    and runs long enough for the engine to dwell in a basin past the
    sustained-c-phase threshold.  Everything else — substrate, cluster,
    engine type, effector wiring, traversal accounting, outcome
    reinforcement — is the production AMEND-005 + AMEND-006 stack.

    Demonstrates:
      * EffectorEvents firing with all three cost components populated
      * apply_outcome() actually firing on each commit and pinning ε_ij
        near ε_original instead of letting it decay
    """
    print("\n" + "=" * 62)
    print("  [SUPPLEMENTARY]  Commit-dynamics demo")
    print("  (closes AMEND-005 + AMEND-006 loop end-to-end)")
    print("=" * 62)
    np.random.seed(2026)

    DIM     = 8
    bus     = EventBus()
    eff     = Effector().attach(bus)

    cluster = PersistenceCluster(
        dim=DIM, E_star=8.0, max_engines=2, bus=bus,
        E_c=0.5, E_s=3.0,
        tau_base=200.0,
        usage_coefficient=1.0,
        outcome_coefficient=0.3,
    )

    # Two orthogonal wells, low matched stiffness so cross-pollution < E_c.
    c1 = np.zeros(DIM); c1[0] = 1.0
    c2 = np.zeros(DIM); c2[4] = 1.0
    LAM = 0.2
    cluster.load(
        {"well_1": _make_quadratic_constraint(c1),
         "well_2": _make_quadratic_constraint(c2)},
        stiffnesses={"well_1": LAM, "well_2": LAM},
        centres={"well_1": c1, "well_2": c2},
    )
    eff.register_cluster(cluster.cluster_id, LAM)

    # Lower attention scarcity so engines settle into basins.
    for eng in cluster.engines:
        eng.attention_scarcity = 0.03
    # Seed first engine near well_1 to give it somewhere to commit.
    cluster.engines[0].v = c1.copy() + 0.1 * np.random.randn(DIM)

    # Tracking
    N_STEPS = 500
    energy_trace, phase_trace = [], []
    decay_trace, traversal_trace, cum_cost_trace = [], [], []

    phase_map = {"r": 0, "k": 1, "s": 2, "c": 3}

    for _ in range(N_STEPS):
        cluster.step()
        cluster.sub.decay_step()
        v0 = cluster.engines[0].v
        energy_trace.append(float(cluster.sub.energy(v0)))
        phase_trace.append(phase_map.get(cluster.dominant_phase.value, 0))
        decay_trace.append(
            float(cluster.sub._decay_cache.get(("well_1", "well_2"), 0.0))
        )
        traversal_trace.append(
            int(cluster.sub._traversal.get(("well_1", "well_2"), 0))
        )
        cum_cost_trace.append(
            float(sum(e.total_cost for e in eff.effector_events()))
        )

    events = eff.effector_events()
    n_commits = len(events)
    print(f"  Commits emitted: {n_commits}")
    if events:
        sample = events[:5]
        for i, ev in enumerate(sample):
            print(f"    [{i}]  E(v_c)={ev.energy_at_c:.3f}  "
                  f"L={ev.landauer_cost:.3f}  "
                  f"W={ev.work_estimate:.3f}  "
                  f"total={ev.total_cost:.3f}")
        if len(events) > 5:
            print(f"    … {len(events)-5} more")
    eps_original = cluster.sub._original_eps.get(("well_1", "well_2"), 0.0)
    eps_final    = cluster.sub._decay_cache.get(("well_1", "well_2"), 0.0)
    print(f"  ε_ij (well_1, well_2):  original={eps_original:.4f}  "
          f"final={eps_final:.4f}  retention={eps_final/max(eps_original,1e-9):.1%}")
    print(f"  Traversals (well_1↔well_2): {traversal_trace[-1]}")

    # 4-panel supplementary figure.
    steps = np.arange(N_STEPS)
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    fig.suptitle(
        "S4 Supplementary — Commit dynamics with reinforcement\n"
        f"PersistenceCluster + Effector  |  dim={DIM}  E*=8.0  E_c=0.5  "
        f"τ_base=200  outcome=0.3  |  commits={n_commits}",
        fontsize=10,
    )

    ax = axes[0, 0]
    ax.plot(steps, energy_trace, color="steelblue", linewidth=0.7, label="E(v)")
    ax.axhline(0.5, color="green", linestyle=":", alpha=0.7, label="E_c=0.5")
    ax.set_title("Engine 0 — Energy trace")
    ax.set_xlabel("Step"); ax.set_ylabel("E(v) [k_BT]")
    ax.legend(fontsize=7); ax.grid(alpha=0.3)

    ax = axes[0, 1]
    ax.plot(steps, phase_trace, color="darkorange", linewidth=0.7)
    ax.set_yticks([0, 1, 2, 3]); ax.set_yticklabels(["r", "k", "s", "c"])
    ax.set_title("Cluster — Dominant phase")
    ax.set_xlabel("Step"); ax.grid(alpha=0.3)

    ax = axes[1, 0]
    ax.plot(steps, decay_trace, color="purple", linewidth=0.9, label="ε_ij(t)")
    ax.axhline(eps_original, color="red", linestyle=":", alpha=0.7,
               label=f"ε_original={eps_original:.3f}")
    ax.set_title("Edge ε(well_1,well_2) — reinforcement holds it near saturation")
    ax.set_xlabel("Step"); ax.set_ylabel("ε_ij")
    ax.legend(fontsize=7); ax.grid(alpha=0.3)

    ax = axes[1, 1]
    ax.plot(steps, cum_cost_trace, color="darkgreen", linewidth=0.9,
            label=f"Σ total_cost (final={cum_cost_trace[-1]:.2f})")
    ax.set_title("Cumulative EffectorEvent total_cost")
    ax.set_xlabel("Step"); ax.set_ylabel("Σ total_cost [k_BT]")
    ax.legend(fontsize=7); ax.grid(alpha=0.3)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(out_path, dpi=120)
    plt.close()
    print(f"  Supplementary plot saved → {out_path}")

    return dict(
        n_commits=n_commits,
        eps_original=eps_original,
        eps_final=eps_final,
        retention_pct=100.0 * eps_final / max(eps_original, 1e-9),
        cumulative_cost=float(cum_cost_trace[-1]),
        traversals=traversal_trace[-1],
    )


# =============================================================================
#  Main
# =============================================================================

def main():
    print("=" * 62)
    print("  MPC Brain — Session 4")
    print(f"  Anthropic={_ANTHROPIC_LIB}  "
          f"API_KEY={'set' if os.environ.get('ANTHROPIC_API_KEY') else 'unset'}")
    print("=" * 62)

    r005          = test_amend005()
    r006_all, r006a, r006b = test_amend006()
    r_task4       = run_network_demo_s4(
        out_path="/mnt/user-data/outputs/mpc_network_demo_s4.png",
    )
    r_supp        = demo_commit_dynamics(
        out_path="/mnt/user-data/outputs/mpc_network_demo_s4_commits.png",
    )

    print("\n" + "=" * 62)
    print("  Session 4 — Final Summary")
    print("=" * 62)
    rows = [
        ("AMEND-005",  "Effector",                        r005),
        ("AMEND-006A", "PersistenceSubstrate (usage)",    r006a),
        ("AMEND-006B", "PersistenceSubstrate (outcome)",  r006b),
        ("TASK-4",     "Network Demo",                     r_task4["passed"]),
    ]
    for tag, name, ok in rows:
        print(f"  {tag:<12}  {name:<34}  {'PASS' if ok else 'FAIL'}")

    all_pass = all(ok for _, _, ok in rows)
    print(f"\n  Overall: {'ALL PASS ✓' if all_pass else 'SOME FAILURES ✗'}")
    print(f"\n  Supplementary commit demo: {r_supp['n_commits']} commits, "
          f"ε retention {r_supp['retention_pct']:.0f}%")

    return dict(
        r005=r005, r006a=r006a, r006b=r006b, r_task4=r_task4,
        r_supp=r_supp,
        all_pass=all_pass,
    )


if __name__ == "__main__":
    main()
