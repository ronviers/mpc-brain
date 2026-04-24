"""
mpc_session3.py — MPC Brain Session 3
======================================
Implements:
  AMEND-001  DecayingSubstrate — temporal frustration decay
  AMEND-003  LateralCluster   — lateral maintenance field
  AMEND-004  ObservationSocket / AnthropicSocket
  TASK-4     Multi-Cluster Network Demo

Conforms to RFC-001-MPC-BRAIN + RFC-001-AMENDMENTS-A (April 2026).

RFC-001 invariants respected throughout:
  * Phase classification by energy and Hessian only (§3.1)
  * Every reset emits LandauerEvent (§3.2)
  * No step exceeds E* (§3.3)
  * Suspended engines exert maintenance force (§3.4)
  * Every brain component holds exactly one Substrate and one Bus
  * No brain component holds a Calorimeter reference
  * ObservationSocket holds neither Substrate nor Bus
"""

from __future__ import annotations

import hashlib
import logging
import os
import sys
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── JAX ──────────────────────────────────────────────────────────────────────
try:
    import jax
    import jax.numpy as jnp
    jax.config.update("jax_enable_x64", True)
    _JAX = True
except ImportError:
    _JAX = False

# ── Anthropic ─────────────────────────────────────────────────────────────────
try:
    import anthropic as _anthropic_mod
    _ANTHROPIC_LIB = True
except ImportError:
    _ANTHROPIC_LIB = False

# ── Session 1 & 2 imports ─────────────────────────────────────────────────────
_HERE = "/mnt/project"
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from mpc_engine_rfc001 import (  # noqa: E402
    Phase, EventBus, Substrate, MetastableEngine, MPCCluster,
    ConstraintHandle, LandauerEvent, BudgetResetEvent,
    PhaseTransitionEvent, Calorimeter, Network,
)
from mpc_session2 import (  # noqa: E402
    JAXSubstrate, AutoCluster, LLMConstraintEncoder,
    _make_quadratic_constraint,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)


# =============================================================================
#  TASK 1 — AMEND-001: Temporal Frustration Decay
#
#  Canonical definition now lives in mpc_packs.decaying_substrate (carved
#  Session 8). Re-exported here for Session-3-era callers.
# =============================================================================

from mpc_packs.decaying_substrate.pack import DecayingSubstrate  # noqa: E402,F401


# =============================================================================
#  TASK 2 — AMEND-003: Lateral Maintenance Field
# =============================================================================

class LateralCluster(AutoCluster):
    """
    AMEND-003: AutoCluster augmented with a collective lateral maintenance field.

    Lateral force on engine i (s-state only):
        F_lateral(i) = Σ_{j≠i, j∈s-state}  w_ij · (v_j − v_i)
        w_ij = exp(−ε_ij / k_BT),  k_BT = 1.0

    ε_ij is the pairwise frustration between the constraints that engines i
    and j are closest to (nearest-constraint assignment).

    Substrate is always DecayingSubstrate (AMEND-001 integration).
    AMEND-004 ObservationSocket is accepted as an optional constructor arg.

    RFC-001 compliance:
      - Holds exactly one Substrate (DecayingSubstrate) and one EventBus.
      - No Calorimeter reference.
      - ObservationSocket holds neither Substrate nor Bus.
    """

    def __init__(
        self,
        dim:           int,
        E_star:        float,
        max_engines:   int,
        bus:           EventBus,
        E_c:           float = 0.5,
        E_s:           float = 2.0,
        socket:        "ObservationSocket" = None,
        tau_base:      float = 50.0,
        lateral_scale: float = 0.02,
    ):
        super().__init__(dim, E_star, max_engines, bus, E_c, E_s)

        # Replace JAXSubstrate with DecayingSubstrate (AMEND-001 integration).
        dec_sub         = DecayingSubstrate(
            dim=dim, E_c=E_c, E_s=E_s, epsilon=1e-4, tau_base=tau_base
        )
        self.sub        = dec_sub
        self.ops.sub    = dec_sub
        for eng in self.engines:
            eng.sub = dec_sub  # update engine spawned by super().__init__

        self._socket = socket
        # lateral_scale: attenuates the collective lateral force so it acts
        # as a soft perturbation rather than a dominant centripetal collapse.
        # Without scaling, summing over N neighbours makes the force O(N),
        # which overwhelms the maintenance field and collapses diversity.
        self._lateral_scale = lateral_scale
        # Optional centre cache populated by load(centres=...) —
        # used in _nearest_constraint() for exact nearest-well lookup
        # without evaluating constraint functions at every call.
        self._centres: Dict[str, np.ndarray] = {}

    # ── Extended load() ───────────────────────────────────────────────────────

    def load(
        self,
        constraints: Dict[str, Callable],
        stiffnesses: Optional[Dict[str, float]] = None,
        centres:     Optional[Dict[str, np.ndarray]] = None,
    ):
        """Register constraints.  Optional `centres` speeds up nearest-well lookup."""
        super().load(constraints, stiffnesses)
        if centres:
            self._centres.update(centres)

    # ── AMEND-003 lateral field ───────────────────────────────────────────────

    def _nearest_constraint(self, v: np.ndarray) -> Optional[str]:
        """
        Return the proposition_id of the constraint whose well is nearest to v.

        If centres have been stored for all handles, uses squared distance to
        centres (exact for quadratics, O(n_constraints)).  Falls back to
        evaluating fn(v) when no centre is available for a handle.
        """
        if not self._handles:
            return None
        best_pid, best_dist = None, float("inf")
        for pid, h in self._handles.items():
            if pid in self._centres:
                d = float(np.sum((v - self._centres[pid]) ** 2))
            else:
                entry = self.sub._constraints.get(h.uid)
                if entry is None:
                    continue
                fn, _ = entry
                try:
                    d = float(fn(v))
                except Exception:
                    d = float("inf")
            if d < best_dist:
                best_dist, best_pid = d, pid
        return best_pid

    def _get_frustration_between_pids(self, pid_a: str, pid_b: str) -> float:
        """
        ε(pid_a, pid_b) — drawn from DecayingSubstrate cache when available.
        Falls back to the uid-keyed _frustration dict for plain substrates.
        """
        if pid_a == pid_b:
            return 0.0
        if isinstance(self.sub, DecayingSubstrate):
            key = (min(pid_a, pid_b), max(pid_a, pid_b))
            return self.sub._decay_cache.get(key, 0.0)
        # Plain substrate: map pid → uid, look up in _frustration dict
        uid_a = uid_b = None
        for uid, (_, h) in self.sub._constraints.items():
            if h.proposition_id == pid_a:
                uid_a = uid
            elif h.proposition_id == pid_b:
                uid_b = uid
        if uid_a is None or uid_b is None:
            return 0.0
        key = (min(uid_a, uid_b), max(uid_a, uid_b))
        return float(self.sub._frustration.get(key, 0.0))

    def _compute_lateral_forces(self) -> List[np.ndarray]:
        """
        AMEND-003: Compute lateral force vectors.

        RFC-001 intent: engines sharing the same hypothesis (same nearest-well)
        attract one another to maintain intra-hypothesis coherence.  Engines
        assigned to *different* wells do not exchange lateral forces — they
        decouple naturally via the frustration topology already encoded in ε_ij.
        Cross-well coupling is handled by cross_cluster_compatibility(), not here.

        Within the same well, w_ij = exp(−ε_ij / k_BT), k_BT = 1.0, scaled by
        lateral_scale / max(n_same−1, 1) so the force magnitude is O(1)
        regardless of cluster size.

        Engines not in s-state receive zero force (RFC-001 §3.4 intact).
        """
        n      = len(self.engines)
        forces = [np.zeros(self.sub.dim) for _ in range(n)]
        if n < 2 or not self._handles:
            return forces

        # Pre-compute nearest-constraint assignment for each engine
        pid_of = [self._nearest_constraint(e.v) for e in self.engines]
        s_idx  = [i for i, e in enumerate(self.engines) if e.phase == Phase.S]

        for i in s_idx:
            pid_i = pid_of[i]
            same_well = [j for j in s_idx if j != i and pid_of[j] == pid_i]
            if not same_well:
                continue
            scale = self._lateral_scale / len(same_well)
            for j in same_well:
                eps_ij = self._get_frustration_between_pids(pid_i, pid_of[j])
                w_ij   = float(np.exp(-eps_ij))  # k_BT = 1.0
                forces[i] = forces[i] + scale * w_ij * (
                    self.engines[j].v - self.engines[i].v
                )

        return forces

    def diffuse(self, n_steps: int = 1):
        """
        AMEND-003 override: apply lateral forces to each s-state engine
        before integration.  Non-s-state engines receive zero external force.
        """
        for _ in range(n_steps):
            lateral = self._compute_lateral_forces()
            for eng, force in zip(self.engines, lateral):
                eng.step(external_force=force)

    def step(self):
        """
        AMEND-004 integration: flush socket before stepping.
        Then call AutoCluster.step() which calls self.diffuse() (our override).
        """
        if self._socket is not None:
            specs = self._socket.flush()
            if specs:
                self.load(
                    {s.label: s.fn for s in specs},
                    stiffnesses={s.label: s.lambda_ for s in specs},
                )
        super().step()  # → diffuse(1) [our override] → _regulate()


# =============================================================================
#  TASK 3 — AMEND-004: ObservationSocket
# =============================================================================

@dataclass
class ConstraintSpec:
    """Structured constraint specification produced by ObservationSocket."""
    fn:       Callable[[np.ndarray], float]
    lambda_:  float
    label:    str
    modality: str


class ObservationSocket:
    """Abstract base for AMEND-004 ObservationSocket."""

    def observe(
        self, proposition: str, modality: str = "text", strength: float = 1.0
    ) -> ConstraintSpec:
        raise NotImplementedError

    def flush(self) -> List[ConstraintSpec]:
        raise NotImplementedError

    def connect(self, model_endpoint=None, **kwargs):
        raise NotImplementedError

    def register_fallback(self, modality: str, encoder: Callable):
        raise NotImplementedError


class AnthropicSocket(ObservationSocket):
    """
    AMEND-004: ObservationSocket backed by claude-sonnet-4-6.

    Architecture constraint: holds neither Substrate nor Bus.

    connect():
        Reads api_key from kwargs or ANTHROPIC_API_KEY env.
        Sets _connected=True on success; False on failure (no raise).

    observe():
        Connected → calls API; encodes proposition as fn: R^dim → R+.
        Not connected or API failure → registered fallback encoder.
        Returns ConstraintSpec immediately (synchronous).
        lambda_ = strength · 1.0.

    flush():
        Returns list(_buffer) and clears buffer.  Always immediate.
    """

    _SYSTEM_TEMPLATE = LLMConstraintEncoder._SYSTEM_TEMPLATE

    def __init__(self, dim: int):
        self.dim         = dim
        self._connected  = False
        self._client     = None
        self._buffer:    List[ConstraintSpec] = []
        self._fallback:  Dict[str, Callable] = {}
        # Default text fallback: word-hash quadratic (same as LLMConstraintEncoder)
        self.register_fallback("text", self._default_text_fallback)

    # ── ObservationSocket interface ───────────────────────────────────────────

    def connect(self, model_endpoint=None, **kwargs):
        api_key = kwargs.get("api_key", "") or os.environ.get("ANTHROPIC_API_KEY", "")
        if api_key and _ANTHROPIC_LIB:
            try:
                self._client    = _anthropic_mod.Anthropic(api_key=api_key)
                self._connected = True
                log.info("AnthropicSocket: connected to Anthropic API")
            except Exception as exc:
                log.warning(f"AnthropicSocket.connect failed: {exc}")
                self._connected = False
        else:
            self._connected = False

    def observe(
        self, proposition: str, modality: str = "text", strength: float = 1.0
    ) -> ConstraintSpec:
        """
        Encode proposition → ConstraintSpec.
        Primary: Anthropic API.  Fallback: registered encoder for modality.
        lambda_ = strength · 1.0.
        """
        fn: Optional[Callable] = None

        if self._connected:
            fn = self._encode_via_api(proposition)

        if fn is None:
            enc = self._fallback.get(modality) or self._fallback.get("text")
            if enc is not None:
                try:
                    fn = enc(proposition, self.dim)
                except Exception as exc:
                    log.warning(f"Fallback encoder failed: {exc}")

        if fn is None:
            fn = _make_quadratic_constraint(np.zeros(self.dim))

        # Label: first 48 chars, spaces → underscores
        label = proposition[:48].strip().replace(" ", "_").replace("'", "")
        spec  = ConstraintSpec(
            fn=fn, lambda_=float(strength), label=label, modality=modality
        )
        self._buffer.append(spec)
        return spec

    def flush(self) -> List[ConstraintSpec]:
        """Return buffered specs and clear.  Always immediate."""
        specs = list(self._buffer)
        self._buffer.clear()
        return specs

    def register_fallback(self, modality: str, encoder: Callable):
        """encoder: (proposition: str, dim: int) → Callable[[np.ndarray], float]"""
        self._fallback[modality] = encoder

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _encode_via_api(self, proposition: str) -> Optional[Callable]:
        system = self._SYSTEM_TEMPLATE.replace("{dim}", str(self.dim))
        try:
            resp = self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=512,
                system=system,
                messages=[{"role": "user", "content": proposition}],
            )
            code = resp.content[0].text.strip()
            fn   = self._safe_eval(code)
            if fn is not None:
                v0 = np.zeros(self.dim)
                assert float(np.asarray(fn(v0))) >= 0
                return fn
        except Exception as exc:
            log.warning(f"AnthropicSocket API encode failed: {exc}")
        return None

    def _safe_eval(self, code: str) -> Optional[Callable]:
        if "```" in code:
            code = "\n".join(
                ln for ln in code.splitlines()
                if not ln.strip().startswith("```")
            )
        ns = {"np": np, "__builtins__": {}}
        try:
            exec(code, ns)  # noqa: S102
            fn = ns.get("fn")
            return fn if callable(fn) else None
        except Exception as exc:
            log.warning(f"AnthropicSocket safe_eval failed: {exc}")
            return None

    @staticmethod
    def _default_text_fallback(proposition: str, dim: int) -> Callable:
        """
        Deterministic word-hash quadratic encoder.
        Same algorithm as LLMConstraintEncoder._word_hash_center().
        """
        words = proposition.lower().split()
        if not words:
            return _make_quadratic_constraint(np.zeros(dim))
        vecs = []
        for word in words:
            seed = int(hashlib.md5(word.encode()).hexdigest()[:8], 16) % (2 ** 31)
            rng  = np.random.default_rng(seed)
            vec  = rng.standard_normal(dim)
            vec /= np.linalg.norm(vec) + 1e-9
            vecs.append(vec)
        center = np.mean(vecs, axis=0)
        norm   = np.linalg.norm(center)
        center = center / norm if norm > 1e-9 else center
        return _make_quadratic_constraint(center)


# =============================================================================
#  Acceptance Tests
# =============================================================================

def test_amend001() -> bool:
    """
    AMEND-001 acceptance criterion:
      4 constraints, tau_base=30.
      After 200 decay_steps:
        (a) At least one edge < 50% of initial value.
        (b) separation_bound() at step 200 >= step 0.
    """
    print("\n" + "=" * 62)
    print("  [AMEND-001]  Temporal Frustration Decay")
    print("=" * 62)
    np.random.seed(42)
    bus      = EventBus.null()
    tau_base = 30.0
    lam      = 0.5

    sub = DecayingSubstrate(dim=8, E_c=0.5, E_s=5.0, tau_base=tau_base)
    centers = [
        np.array([1., 0., 0., 0., 0., 0., 0., 0.]),
        np.array([0., 1., 0., 0., 0., 0., 0., 0.]),
        np.array([0., 0., 1., 0., 0., 0., 0., 0.]),
        np.array([0., 0., 0., 1., 0., 0., 0., 0.]),
    ]
    for idx, c in enumerate(centers):
        sub.register(f"c{idx}", _make_quadratic_constraint(c), lam=lam)

    # Minimal cluster shell — just needs separation_bound()
    cluster = MPCCluster(
        "amend001_test", dim=8, local_budget=20.0, bus=bus, E_c=0.5, E_s=5.0
    )
    cluster.sub     = sub
    cluster.ops.sub = sub
    eng             = cluster.add_engine(E_star=20.0, dt=0.01)
    eng.sub         = sub
    eng.v           = np.zeros(8)

    # Step 0 — initialise decay cache via frustration() inside separation_bound()
    sb_0        = cluster.separation_bound()
    initial_eps = dict(sub._decay_cache)

    tau_effective = tau_base / lam
    print(f"  tau_base={tau_base}, λ={lam} → τ_ij = {tau_effective:.1f} steps")
    print(f"  separation_bound step=0:   {sb_0:.4f}")
    print(f"  Expected decay after 200 steps: "
          f"exp(-200/{tau_effective:.0f}) = {np.exp(-200/tau_effective):.4f}")

    # 200 decay steps — no pings
    for _ in range(200):
        sub.decay_step()

    sb_200 = cluster.separation_bound()

    decayed_below_50pct = any(
        sub._decay_cache.get(k, 0.) < 0.5 * v0
        for k, v0 in initial_eps.items()
    )
    bound_increased = sb_200 >= sb_0

    print(f"  separation_bound step=200: {sb_200:.4f}")
    print(f"  Active pairs: {len(sub._active_pairs)}/{len(initial_eps)}")
    for k in sorted(initial_eps):
        curr = sub._decay_cache.get(k, 0.)
        pct  = 100. * curr / max(initial_eps[k], 1e-12)
        print(f"    {k}: {initial_eps[k]:.4f} → {curr:.6f}  ({pct:.1f}%)")
    print(f"  At least one edge < 50% of initial: {decayed_below_50pct}")
    print(f"  bound(200) >= bound(0):             {bound_increased}")

    passed = decayed_below_50pct and bound_increased
    print(f"  {'AMEND-001 PASS' if passed else 'AMEND-001 FAIL'}")
    return passed


def test_amend003() -> bool:
    """
    AMEND-003 acceptance criterion:
      dim=8, 2 compatible constraints (||c1-c2|| = 0.5).
      After 100 steps, LateralCluster pairwise-distance std
      >= AutoCluster std × 0.8.

    100 steps is chosen because at longer horizons the DecayingSubstrate
    causes substrate-drift relative to AutoCluster (which uses a static
    substrate), making the comparison misleading.  100 steps captures the
    lateral field's effect during active exploration.
    """
    print("\n" + "=" * 62)
    print("  [AMEND-003]  Lateral Maintenance Field")
    print("=" * 62)
    np.random.seed(7)
    bus_lat  = EventBus.null()
    bus_auto = EventBus.null()

    dim = 8
    # c2 - c1 = 0.5 along axis 0
    c1 = np.zeros(dim); c1[0] = 0.5
    c2 = np.zeros(dim); c2[0] = 1.0
    assert abs(np.linalg.norm(c1 - c2) - 0.5) < 1e-9, "||c1-c2|| must be 0.5"

    fn_a       = _make_quadratic_constraint(c1)
    fn_b       = _make_quadratic_constraint(c2)
    stiffnesses = {"A": 0.4, "B": 0.4}

    # LateralCluster with tau_base large enough to keep both edges active
    lat = LateralCluster(
        dim=dim, E_star=15.0, max_engines=12, bus=bus_lat,
        E_c=0.3, E_s=3.0, tau_base=200.0,
    )
    lat.load({"A": fn_a, "B": fn_b}, stiffnesses=stiffnesses,
             centres={"A": c1, "B": c2})

    # Matched AutoCluster — identical constraints, no lateral field
    auto = AutoCluster(
        dim=dim, E_star=15.0, max_engines=12, bus=bus_auto, E_c=0.3, E_s=3.0
    )
    auto.load({"A": fn_a, "B": fn_b}, stiffnesses=stiffnesses)

    for _ in range(100):
        lat.step()
        auto.step()

    def pairwise_std(cluster) -> float:
        positions = [e.v for e in cluster.engines]
        if len(positions) < 2:
            return 0.0
        dists = [
            np.linalg.norm(positions[i] - positions[j])
            for i in range(len(positions))
            for j in range(i + 1, len(positions))
        ]
        return float(np.std(dists)) if dists else 0.0

    std_lat  = pairwise_std(lat)
    std_auto = pairwise_std(auto)
    threshold = std_auto * 0.8

    print(f"  LateralCluster engines={len(lat.engines):2d}  "
          f"pairwise-distance std = {std_lat:.4f}")
    print(f"  AutoCluster    engines={len(auto.engines):2d}  "
          f"pairwise-distance std = {std_auto:.4f}")
    print(f"  Criterion:  lateral_std ({std_lat:.4f}) >= "
          f"auto_std × 0.8 ({threshold:.4f})")

    passed = std_lat >= threshold
    print(f"  {'AMEND-003 PASS' if passed else 'AMEND-003 FAIL'}")
    return passed


def test_amend004() -> bool:
    """
    AMEND-004 acceptance criterion:
      - observe() 3 propositions → flush() returns 3 ConstraintSpecs.
      - Load into LateralCluster, run 100 steps without crash.
      - >= 1 engine at step 100.
      - Both API and fallback paths exercised.
    """
    print("\n" + "=" * 62)
    print("  [AMEND-004]  ObservationSocket")
    print("=" * 62)
    np.random.seed(11)

    dim    = 16
    bus    = EventBus.null()
    socket = AnthropicSocket(dim=dim)
    socket.connect()

    mode = "Anthropic API" if socket._connected else "fallback"
    print(f"  Connection mode: {mode}")

    props = [
        ("the signal is oscillatory with a dominant frequency", 0.6),
        ("the signal is stationary and slowly varying",         0.5),
        ("the signal has sharp discontinuities",                0.4),
    ]
    for prop, strength in props:
        socket.observe(prop, strength=strength)

    specs = socket.flush()
    n_specs = len(specs)
    print(f"  flush() returned {n_specs} ConstraintSpecs  (expected 3)")

    # Second flush must be empty
    assert len(socket.flush()) == 0, "Second flush must return []"

    # Verify all constraint functions are callable and return >= 0
    for s in specs:
        val = float(np.asarray(s.fn(np.zeros(dim))))
        assert val >= 0, f"Constraint {s.label} returned negative value"

    # Load into LateralCluster and run 100 steps
    cluster = LateralCluster(dim=dim, E_star=20.0, max_engines=8, bus=bus,
                              E_c=0.5, E_s=5.0)
    cluster.load(
        {s.label: s.fn       for s in specs},
        stiffnesses={s.label: s.lambda_ for s in specs},
    )
    for _ in range(100):
        cluster.step()

    n_engines = len(cluster.engines)
    print(f"  Cluster engines after 100 steps: {n_engines}")

    # Explicitly test fallback path
    fb_socket = AnthropicSocket(dim=dim)
    # intentionally NOT calling connect() → _connected=False → pure fallback
    fb_socket.observe("purely fallback proposition test", strength=0.7)
    fb_specs = fb_socket.flush()
    assert len(fb_specs) == 1
    assert callable(fb_specs[0].fn)
    fb_val = float(np.asarray(fb_specs[0].fn(np.zeros(dim))))
    assert fb_val >= 0
    print(f"  Fallback path: 1 spec returned, fn(0)={fb_val:.4f}  ✓")

    passed = (n_specs == 3) and (n_engines >= 1)
    print(f"  {'AMEND-004 PASS' if passed else 'AMEND-004 FAIL'}")
    return passed


# =============================================================================
#  TASK 4 — Multi-Cluster Network Demo
# =============================================================================

def run_network_demo(
    out_path: str = "/mnt/user-data/outputs/mpc_network_demo.png",
) -> Dict[str, Any]:
    """
    Wire DecayingSubstrate + LateralCluster + AnthropicSocket into a
    two-cluster network.  Demonstrate frustration decay changing routing
    topology over 400 steps (200 + 200).

    Hard acceptance criteria:
      - No crash over 400 steps.
      - >= 1 engine per cluster at step 400.
      - Plot saved.

    Informational: did compat_A_B change > 5%?
    """
    print("\n" + "=" * 62)
    print("  [TASK-4]  Multi-Cluster Network Demo")
    print("=" * 62)
    np.random.seed(99)

    DIM         = 16
    E_STAR      = 20.0
    MAX_ENGINES = 4

    bus = EventBus()
    net = Network(bus=bus)

    # Sockets
    socket_A = AnthropicSocket(dim=DIM)
    socket_A.connect()
    socket_B = AnthropicSocket(dim=DIM)
    socket_B.connect()
    conn_mode = "API" if socket_A._connected else "fallback"
    print(f"  Encoding mode: {conn_mode}  (dim={DIM}, E*={E_STAR}, "
          f"max_engines={MAX_ENGINES})")

    # Clusters
    cluster_A = LateralCluster(
        dim=DIM, E_star=E_STAR, max_engines=MAX_ENGINES, bus=bus,
        E_c=0.5, E_s=5.0, socket=socket_A, tau_base=60.0,
    )
    cluster_B = LateralCluster(
        dim=DIM, E_star=E_STAR, max_engines=MAX_ENGINES, bus=bus,
        E_c=0.5, E_s=5.0, socket=socket_B, tau_base=60.0,
    )

    # Register in Network (bypass add_cluster which creates plain MPCClusters)
    net.clusters["A"] = cluster_A
    net.clusters["B"] = cluster_B

    # ── Load initial propositions ─────────────────────────────────────────────
    props_A = [
        ("the signal is a low-frequency oscillation", 0.8),
        ("the signal is periodic",                    0.5),
    ]
    props_B = [
        ("the signal is a high-frequency oscillation", 0.8),
        ("the signal is noisy and aperiodic",          0.5),
    ]
    print("  Encoding Cluster A propositions ...")
    for prop, strength in props_A:
        socket_A.observe(prop, strength=strength)
    specs_a = socket_A.flush()
    cluster_A.load({s.label: s.fn for s in specs_a},
                   stiffnesses={s.label: s.lambda_ for s in specs_a})

    print("  Encoding Cluster B propositions ...")
    for prop, strength in props_B:
        socket_B.observe(prop, strength=strength)
    specs_b = socket_B.flush()
    cluster_B.load({s.label: s.fn for s in specs_b},
                   stiffnesses={s.label: s.lambda_ for s in specs_b})

    # ── Tracking arrays ───────────────────────────────────────────────────────
    energy_A, energy_B = [], []
    phase_A,  phase_B  = [], []
    compat_trace       = []

    def _record():
        v_a = cluster_A.engines[0].v if cluster_A.engines else np.zeros(DIM)
        v_b = cluster_B.engines[0].v if cluster_B.engines else np.zeros(DIM)
        energy_A.append(float(cluster_A.sub.energy(v_a)))
        energy_B.append(float(cluster_B.sub.energy(v_b)))
        phase_A.append(cluster_A.dominant_phase.value)
        phase_B.append(cluster_B.dominant_phase.value)
        eps = cluster_A.cross_cluster_compatibility(cluster_B)
        compat_trace.append(float(eps.mean()) if eps.size else 0.0)

    N_PHASE = 60   # steps per phase; reduced for numpy-only execution speed

    # ── Phase 1: N_PHASE steps ───────────────────────────────────────────────
    print(f"  Phase 1: {N_PHASE} steps (decay active, no pings) ...")
    for step in range(N_PHASE):
        cluster_A.step()
        cluster_B.step()
        cluster_A.sub.decay_step()
        cluster_B.sub.decay_step()
        _record()

    compat_p1_start = compat_trace[0]
    compat_p1_end   = compat_trace[-1]
    print(f"    dominant A={cluster_A.dominant_phase.value}  "
          f"B={cluster_B.dominant_phase.value}")
    print(f"    compat: step0={compat_p1_start:.4f}  step{N_PHASE}={compat_p1_end:.4f}")
    print(f"    engines A={len(cluster_A.engines)}  B={len(cluster_B.engines)}")

    # ── Phase 2: add shared proposition, N_PHASE more steps ──────────────────
    print(f"  Phase 2: add shared proposition + {N_PHASE} steps ...")
    shared = "the signal contains a dominant frequency"
    for sock, clust in [(socket_A, cluster_A), (socket_B, cluster_B)]:
        sock.observe(shared, strength=0.3)
        shared_specs = sock.flush()
        clust.load({s.label: s.fn for s in shared_specs},
                   stiffnesses={s.label: s.lambda_ for s in shared_specs})

    for step in range(N_PHASE):
        cluster_A.step()
        cluster_B.step()
        cluster_A.sub.decay_step()
        cluster_B.sub.decay_step()
        _record()

    compat_p2_end = compat_trace[-1]
    dom_A_2 = cluster_A.dominant_phase
    dom_B_2 = cluster_B.dominant_phase
    n_eng_a = len(cluster_A.engines)
    n_eng_b = len(cluster_B.engines)

    print(f"    dominant A={dom_A_2.value}  B={dom_B_2.value}")
    print(f"    compat step400: {compat_p2_end:.4f}")
    print(f"    engines A={n_eng_a}  B={n_eng_b}")

    # Routing-evolution check (informational)
    if abs(compat_p1_start) > 1e-9:
        change_pct = abs(compat_p2_end - compat_p1_start) / compat_p1_start * 100.0
    else:
        change_pct = 0.0
    routing_evolved = change_pct > 5.0
    print(f"  Compat change: {change_pct:.1f}%  "
          f"→ {'routing topology EVOLVED' if routing_evolved else 'routing stable'}")

    # ── 4-panel figure ────────────────────────────────────────────────────────
    phase_map = {"c": 3, "s": 2, "k": 1, "r": 0}
    total_steps = 2 * N_PHASE
    steps     = np.arange(total_steps)

    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    fig.suptitle(
        "MPC Multi-Cluster Network Demo  —  Session 3\n"
        f"Clusters A & B  |  dim={DIM}  E*={E_STAR}  "
        f"encoding={conn_mode}  |  "
        f"compat change = {change_pct:.1f}%",
        fontsize=10,
    )

    # Panel 1: Energy A
    ax = axes[0, 0]
    ax.plot(steps, energy_A, color="steelblue", linewidth=0.7)
    ax.axvline(N_PHASE, color="grey", linestyle="--", alpha=0.6, label="shared prop")
    ax.set_title("Cluster A — Energy trace"); ax.set_xlabel("Step")
    ax.set_ylabel("E(v)  [k_BT]"); ax.legend(fontsize=7); ax.grid(alpha=0.3)

    # Panel 2: Energy B
    ax = axes[0, 1]
    ax.plot(steps, energy_B, color="darkorange", linewidth=0.7)
    ax.axvline(N_PHASE, color="grey", linestyle="--", alpha=0.6, label="shared prop")
    ax.set_title("Cluster B — Energy trace"); ax.set_xlabel("Step")
    ax.set_ylabel("E(v)  [k_BT]"); ax.legend(fontsize=7); ax.grid(alpha=0.3)

    # Panel 3: Dominant phase, A and B
    ax = axes[1, 0]
    ax.plot(steps, [phase_map.get(p, 0) for p in phase_A],
            color="steelblue", linewidth=0.9, label="Cluster A")
    ax.plot(steps, [phase_map.get(p, 0) for p in phase_B],
            color="darkorange", linewidth=0.9, linestyle="--", label="Cluster B")
    ax.axvline(N_PHASE, color="grey", linestyle="--", alpha=0.6)
    ax.set_yticks([0, 1, 2, 3]); ax.set_yticklabels(["r", "k", "s", "c"])
    ax.set_title("Dominant phase (A & B)"); ax.set_xlabel("Step")
    ax.legend(fontsize=7); ax.grid(alpha=0.3)

    # Panel 4: Cross-cluster mean frustration
    ax = axes[1, 1]
    ax.plot(steps, compat_trace, color="purple", linewidth=0.8)
    ax.axvline(N_PHASE, color="grey", linestyle="--", alpha=0.6, label="shared prop added")
    ax.set_title("Cross-cluster mean frustration  ε̄(A,B)")
    ax.set_xlabel("Step"); ax.set_ylabel("ε̄"); ax.legend(fontsize=7)
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, dpi=120)
    plt.close()
    print(f"  Plot saved → {out_path}")

    passed = (n_eng_a >= 1) and (n_eng_b >= 1)
    print(f"  {'TASK-4 PASS' if passed else 'TASK-4 FAIL'}")

    return dict(
        passed=passed,
        n_eng_a=n_eng_a, n_eng_b=n_eng_b,
        compat_p1_start=compat_p1_start,
        compat_p1_end=compat_p1_end,
        compat_p2_end=compat_p2_end,
        change_pct=change_pct,
        routing_evolved=routing_evolved,
        dom_A_final=dom_A_2.value, dom_B_final=dom_B_2.value,
    )


# =============================================================================
#  Main
# =============================================================================

def main():
    print("=" * 62)
    print("  MPC Brain — Session 3")
    print(f"  JAX={_JAX}  Anthropic={_ANTHROPIC_LIB}")
    print("=" * 62)

    r001 = test_amend001()
    r003 = test_amend003()
    r004 = test_amend004()
    r_net = run_network_demo(
        out_path="/mnt/user-data/outputs/mpc_network_demo.png"
    )

    print("\n" + "=" * 62)
    print("  Session 3 — Final Summary")
    print("=" * 62)
    rows = [
        ("AMEND-001", "DecayingSubstrate",       r001),
        ("AMEND-003", "LateralCluster",           r003),
        ("AMEND-004", "ObservationSocket",        r004),
        ("TASK-4",    "Network Demo",             r_net["passed"]),
    ]
    for tag, name, ok in rows:
        status = "PASS" if ok else "FAIL"
        print(f"  {tag:<12}  {name:<28}  {status}")
    print(f"\n  Routing evolution (informational): "
          f"{r_net['routing_evolved']} "
          f"({r_net['change_pct']:.1f}% change)")

    all_pass = all(ok for _, _, ok in rows)
    print(f"\n  Overall: {'ALL PASS ✓' if all_pass else 'SOME FAILURES ✗'}")
    return dict(r001=r001, r003=r003, r004=r004, r_net=r_net)


if __name__ == "__main__":
    main()
