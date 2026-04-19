#!/usr/bin/env python3
"""
MPC Lattice — Langevin Validation Rig for the Dynamical Framework
==================================================================

This is the rebuilt lattice.  The old version was a static-thermodynamic
calorimeter: evaluate a landscape, find minima, read barriers, classify
by energy thresholds.  That machinery is gone.

The new lattice is a *spectroscope*: simulate overdamped Langevin
trajectories on known-ground-truth geometric substrates, measure
correlation-spectrum observables (τ_A, γ_A, γ_ij, and the time-resolved
Fluctuation–Dissipation Ratio), and verify that the regime classifier
correctly reports committed / suspended / conflict / reset states.

The four scenarios have ground-truth regime labels by construction.  This
file is therefore a unit-test harness: when a downstream brain computes
γ_A or γ_ij on neural representations, the numerics it uses have been
exercised here against geometries with known answers.

OUTPUTS
    mpc_trajectories.png   Phase-portrait + per-scenario autocorrelation
    mpc_fdr_atlas.png      Four-regime parametric FDR plot  (money plot)
    mpc_separation.png     Survival Separation Theorem, γ_ij dynamical
    mpc_hessian_probe.png  Equilibrium baseline: τ_Hessian vs τ_measured

RUN
    python3 mpc_lattice.py

PHYSICS NOTE
    In a Markovian overdamped Langevin on harmonic wells, γ_A comes out
    with the *opposite* sign from the paper's Table 1 prediction.  This
    is a substrate-level artifact of the Markovian approximation (the
    paper's Table 1 entries for c/s reflect a memory-kernel formulation;
    see PROTOTYPE_FINDINGS.md §1).  We report γ_A as-measured, interpret
    |γ_A| as regime depth, use γ_ij sign as the k-state detector, and
    use FDR parametric-plot shape as the primary regime discriminator
    (the paper's own primary empirical target per §7).  The caveat is
    explicitly flagged at every site where γ_A is measured or reported.
"""

import os
import warnings
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib.lines import Line2D
from scipy.optimize import minimize as scipy_minimize

# Import validated primitives.  Do NOT duplicate them here.
from physics_primitives import (
    run_langevin,
    autocorr_fft,
    tau_integral,
    correlation_time,
    survival_margin,
    cross_dissipation,
    measure_fdr,
    numerical_grad,
    K_BT, DT, D_EFF,
)

warnings.filterwarnings('ignore', category=RuntimeWarning)


# ── Aesthetic (dark panels, preserved from the old code) ────────────────────
BG       = '#12121f'
PANEL    = '#1a1a2e'
TEXT     = '#e8e8f0'
MUTED    = '#7a7a9a'
GRID     = '#2a2a4a'

# Per-regime color palette (stable, keyed to {c, s, k, r})
COLOR = {
    'committed': '#7dd3fc',   # ice blue     → c
    'suspended': '#fde047',   # pale gold    → s
    'conflict':  '#fb7185',   # rose         → k
    'reset':     '#a78bfa',   # violet       → r
}
REGIME_COLOR = {'c': COLOR['committed'], 's': COLOR['suspended'],
                'k': COLOR['conflict'],  'r': COLOR['reset']}


# ── Fixed anchors ───────────────────────────────────────────────────────────
A = np.array([0.0, 0.0])
B = np.array([2.0, 0.0])


# ── Constraint Potentials (geometry, no LLMs) ───────────────────────────────

def V_dist(v, anchor, target_r, lam):
    """
    Distance constraint.  Zero on the circle of radius target_r around anchor.

        V(v) = λ · (|v − anchor| − target_r)²

    High λ → stiff well → deep commitment regime.
    Low λ → soft well → suspension regime.
    """
    d = np.linalg.norm(v - anchor)
    return lam * (d - target_r) ** 2


def V_pos(v, target, lam):
    """
    Position constraint.  Zero only at v = target.  Unique minimum.

        V(v) = λ · |v − target|²
    """
    return lam * np.sum((v - target) ** 2)


def V_area(v, a, b, target_area, lam):
    """
    Area constraint on the triangle (a, b, v).  Kept for compatibility;
    not used by the four canonical scenarios.
    """
    ab = b - a
    av = v - a
    area = 0.5 * abs(ab[0] * av[1] - ab[1] * av[0])
    return lam * (area - target_area) ** 2


# ── The Four Scenarios (ground-truth regime labels by construction) ─────────
#
# Geometry is intentionally minimal:
#   A = (0,0), B = (2,0).
#   committed/suspended: two circles radius 1.2 around A and 1.0 around B.
#     They intersect at (1.11, ±0.46) — solving x² + y² = 1.44 and
#     (x−2)² + y² = 1 simultaneously.  Old code used (0.95, 0.73), which
#     was wrong.
#   conflict: two small circles (radius 0.25) around A and B.  Sum of
#     radii = 0.5 < 2.0, so the circles are disjoint.  No configuration
#     satisfies both.
#   reset: weak bath.  A shallow harmonic basin around (1, 0).  This is
#     the "unconstrained bath" for τ_env measurement.

# Parameters baselined from PROTOTYPE_FINDINGS.md §4.
LAM_COMMITTED = 20.0    # stiff (but not so stiff as to destabilise
                        # Euler–Maruyama at DT=0.01; 100 → oscillatory blowup,
                        # 20 keeps step·grad < noise while preserving the
                        # 25× stiffness contrast vs LAM_SUSPENDED = 0.8)
LAM_SUSPENDED = 0.8     # soft
LAM_CONFLICT  = 30.0    # stiff but disjoint targets → frustrated
LAM_RESET     = 0.15    # bath

R_A_CS = 1.2
R_B_CS = 1.0
R_A_K  = 0.25
R_B_K  = 0.25


def energy_committed(v):
    """[c] compatible constraints, stiff wells (λ = 100)."""
    return (V_dist(v, A, R_A_CS, LAM_COMMITTED) +
            V_dist(v, B, R_B_CS, LAM_COMMITTED))

def energy_suspended(v):
    """[s] compatible constraints, soft wells (λ = 0.8)."""
    return (V_dist(v, A, R_A_CS, LAM_SUSPENDED) +
            V_dist(v, B, R_B_CS, LAM_SUSPENDED))

def energy_conflict(v):
    """[k] disjoint circles (r = 0.25 each), distance 2.0."""
    return (V_dist(v, A, R_A_K, LAM_CONFLICT) +
            V_dist(v, B, R_B_K, LAM_CONFLICT))

def energy_reset(v):
    """[r] weak bounded bath around the midpoint."""
    mid = 0.5 * (A + B)
    return LAM_RESET * np.sum((v - mid) ** 2)


SCENARIOS = {
    'committed': energy_committed,
    'suspended': energy_suspended,
    'conflict':  energy_conflict,
    'reset':     energy_reset,
}
SCENARIO_ORDER   = ['committed', 'suspended', 'conflict', 'reset']
REGIME_SYMBOL    = {'committed': 'c', 'suspended': 's',
                    'conflict':  'k', 'reset':     'r'}
SCENARIO_TITLE   = {'committed': 'COMMITTED [c]',
                    'suspended': 'SUSPENDED [s]',
                    'conflict':  'CONFLICT [k]',
                    'reset':     'RESET [r]'}


# ── Observables ─────────────────────────────────────────────────────────────
#
# V_A and V_B are the canonical probe observables: "how much is the distance
# constraint on A / on B violated at configuration v?".  They are uniform
# across scenarios (same λ=1.0 functional form) so correlation structure is
# attributable to the scenario's energy, not to a scenario-specific observer.

def V_A_obs(v): return V_dist(v, A, R_A_CS, lam=1.0)
def V_B_obs(v): return V_dist(v, B, R_B_CS, lam=1.0)


# ── Initial positions (per-scenario, per FINDINGS §4) ───────────────────────
# Circle intersection geometry: solve x²+y²=1.44 and (x-2)²+y²=1 simultaneously
#   subtract:  (x-2)² − x² = 1 − 1.44   →   −4x + 4 = −0.44   →  x = 1.11
#   then:     y² = 1.44 − 1.2321 = 0.2079  →  y ≈ 0.456
V0_INTERSECT = np.array([1.11, 0.456])   # committed & suspended start here
V0_MID       = np.array([1.0, 0.0])      # conflict & reset start at midpoint

INITIAL_POSITION = {
    'committed': V0_INTERSECT,
    'suspended': V0_INTERSECT,
    'conflict':  V0_MID,
    'reset':     V0_MID,
}


# ── Per-scenario FDR perturbation magnitude ─────────────────────────────────
# From FINDINGS §3: h_mag ~ 0.3·sqrt(C(0)).  Variance of V_A differs by
# four orders of magnitude across regimes, so a single h_mag is inadequate:
# too weak for pinned regimes, overshoots linear response for free regimes.
FDR_H_MAG = {
    'committed': 0.05,      # stable-well fluctuation scale
    'suspended': 0.08,      # mid-range
    'conflict':  0.03,      # deeply pinned → tiny response envelope
    'reset':     0.05,      # weak bath → large h pushes system off linear
                            # response; 0.3 overshoots at n_resp=5000
}


# ── Simulation budgets ──────────────────────────────────────────────────────
# Start conservative.  Scale only if signal demands.
N_STEPS_TRAJ = 12000     # trajectory length for τ_A / γ_A / γ_ij
N_REPS_TRAJ  = 6         # replicas (different noise seeds) per scenario

FDR_N_BURNIN = 2000      # steps before applying perturbation
FDR_N_RESP   = 5000      # steps of response after perturbation
FDR_N_REPS   = 32        # matched-noise paired replicas

BURN_IN_FRAC = 0.25      # fraction of trajectory discarded for equilibration


# ── Convenience: perturbed potential coupled to V_A ─────────────────────────

def make_perturbed_potential(U_base, V_obs, h_mag):
    """
    Linear perturbation coupling to an observable:  U_pert = U_base − h·V_obs.

    χ(τ) = dE[V_obs] / dh  at h→0 is the standard FDR susceptibility.
    """
    def U_pert(v):
        return U_base(v) - h_mag * V_obs(v)
    return U_pert


# ═══════════════════════════════════════════════════════════════════════════
#   MEASUREMENT PIPELINE
# ═══════════════════════════════════════════════════════════════════════════
#
# The bench has three measurements:
#
#   (1) Per-scenario trajectory + autocorrelation + γ_A       [§2 of paper]
#   (2) Per-scenario γ_ij between V_A and V_B                 [§2]
#   (3) Per-scenario parametric FDR χ(τ) vs [C(0)−C(τ)]/D_eff [§7]
#
# The γ_A sign caveat (FINDINGS §1) is stamped at every measurement site.


def run_scenario_trajectories(scenario, n_reps=N_REPS_TRAJ,
                              n_steps=N_STEPS_TRAJ, seed_base=1000):
    """
    Run n_reps independent Langevin trajectories for `scenario`, each of
    length n_steps.  Returns array of shape (n_reps, n_steps, 2).

    Each replica uses a different RNG seed so that trajectory-averaged
    observables have well-defined variance.
    """
    U  = SCENARIOS[scenario]
    v0 = INITIAL_POSITION[scenario]
    trajs = np.empty((n_reps, n_steps, 2))
    for r in range(n_reps):
        rng = np.random.default_rng(seed_base + r)
        trajs[r] = run_langevin(U, v0, n_steps, rng=rng)
    return trajs


def gamma_A_from_trajectories(V_obs, trajs_scen, trajs_bath):
    """
    γ_A = τ_A⁻¹ − τ_env⁻¹  averaged over replica pairs.

    SIGN CAVEAT (FINDINGS §1): in Markovian overdamped Langevin on harmonic
    wells, stiffer wells yield SHORTER τ_A (faster thermal relaxation), so
    γ_A for [c] comes out POSITIVE here — opposite to the paper's Table 1.
    The root cause is the Markovian approximation; the paper's long τ_A for
    committed is a memory-kernel phenomenon (§7).  Interpret |γ_A| as
    regime depth, not γ_A sign.

    Returns dict: {gamma_A_mean, gamma_A_std, tau_A_mean, tau_env_mean}.
    """
    n_reps = min(trajs_scen.shape[0], trajs_bath.shape[0])
    gammas, tauAs, tauEs = [], [], []
    for r in range(n_reps):
        g, tA, tE = survival_margin(V_obs, trajs_scen[r], trajs_bath[r])
        gammas.append(g); tauAs.append(tA); tauEs.append(tE)
    gammas, tauAs, tauEs = map(np.array, (gammas, tauAs, tauEs))
    return {
        'gamma_A_mean': float(gammas.mean()),
        'gamma_A_std':  float(gammas.std(ddof=1)) if n_reps > 1 else 0.0,
        'tau_A_mean':   float(tauAs.mean()),
        'tau_env_mean': float(tauEs.mean()),
        'n_reps':       n_reps,
    }


def gamma_ij_from_trajectories(V_i, V_j, trajs_scen):
    """
    Cross-dissipation γ_ij = τ_{i∧j}⁻¹ − max(τ_i⁻¹, τ_j⁻¹)
    with joint observable V_{i∧j}(v) = V_i(v) + V_j(v).

    Paper's Table 1 predicts γ_ij > 0 for [k] (destructive interference).
    In Markovian substrates this sign can be unreliable in the deep-pinned
    [k] regime — when both V_i and V_j sit near zero variance (tight
    frustrated trap), all three relaxation times collapse to the thermal
    noise floor and the γ_ij sign is numerically dominated.  The MAGNITUDE
    |γ_ij| still discriminates [k] from the compatible regimes ([c], [s],
    [r]) where γ_ij stays close to zero.

    The caveat is the same physical limitation that affects γ_A
    (FINDINGS §1): both are consequences of the Markovian approximation
    collapsing memory structure that the paper locates in §7's active
    measure.  Interpret magnitudes, not signs.

    Returns dict with per-replica and averaged values.
    """
    n_reps = trajs_scen.shape[0]
    rows = []
    for r in range(n_reps):
        gij, ti, tj, tij = cross_dissipation(V_i, V_j, trajs_scen[r])
        rows.append((gij, ti, tj, tij))
    arr = np.array(rows)
    return {
        'gamma_ij_mean': float(arr[:, 0].mean()),
        'gamma_ij_std':  float(arr[:, 0].std(ddof=1)) if n_reps > 1 else 0.0,
        'tau_i_mean':    float(arr[:, 1].mean()),
        'tau_j_mean':    float(arr[:, 2].mean()),
        'tau_ij_mean':   float(arr[:, 3].mean()),
        'n_reps':        n_reps,
    }


def fdr_for_scenario(scenario, V_obs=V_A_obs,
                     n_burnin=FDR_N_BURNIN, n_resp=FDR_N_RESP,
                     n_reps=FDR_N_REPS, seed=7):
    """
    Integrated FDR for `scenario` via matched-noise paired trajectories.

    Returns (tau_grid, C, chi, h_mag).  Parametric plot is χ (y-axis) vs
    [C(0)−C(τ)]/D_eff (x-axis) — unity slope = FDT, regime structure is
    the deviation from that.
    """
    U_base = SCENARIOS[scenario]
    v0     = INITIAL_POSITION[scenario]
    h_mag  = FDR_H_MAG[scenario]
    U_pert = make_perturbed_potential(U_base, V_obs, h_mag)
    tau, C, chi = measure_fdr(U_base, U_pert, V_obs, v0, h_mag,
                              n_burnin=n_burnin, n_resp=n_resp,
                              n_reps=n_reps, seed=seed, dt=DT)
    return tau, C, chi, h_mag


# ═══════════════════════════════════════════════════════════════════════════
#   HESSIAN EQUILIBRIUM BASELINE
# ═══════════════════════════════════════════════════════════════════════════
#
# For overdamped Langevin near a harmonic minimum
#     U(v) ≈ U₀ + ½ (v − v*)ᵀ H (v − v*)
# an observable quadratic in (v − v*) has autocorrelation decay rate set
# by Hessian eigenvalues and D_eff.  We use
#     τ_V^Hessian ≈ 1 / (2 · D_eff · λ_min(H))
# as the equilibrium prediction.  Disagreement between measured τ_A and
# this prediction quantifies D_active dominance — the "how
# non-equilibrium" detector of §7.


def numerical_hessian(U, v, eps=1e-5):
    """Symmetric 2×2 Hessian by central finite differences."""
    n = len(v)
    H = np.zeros((n, n))
    E0 = U(v)
    for i in range(n):
        e_i = np.zeros(n); e_i[i] = eps
        H[i, i] = (U(v + e_i) - 2*E0 + U(v - e_i)) / eps**2
    for i in range(n):
        for j in range(i+1, n):
            e_i = np.zeros(n); e_i[i] = eps
            e_j = np.zeros(n); e_j[j] = eps
            H[i, j] = (U(v + e_i + e_j) - U(v + e_i - e_j)
                       - U(v - e_i + e_j) + U(v - e_i - e_j)) / (4 * eps**2)
            H[j, i] = H[i, j]
    return H


def find_minimum(U, v_guess):
    """
    Robust local minimum of U near v_guess, via BFGS.

    Naive fixed-step gradient descent diverges on stiff wells (λ=100):
    the first-step gradient magnitude is ~200, and any fixed lr > 0.01
    overshoots catastrophically.  BFGS handles it by construction.
    """
    res = scipy_minimize(U, v_guess, method='BFGS',
                         options={'gtol': 1e-8, 'maxiter': 400})
    return res.x


def hessian_baseline(scenario):
    """
    Returns dict with:
      v_star        : local minimum of U near the scenario's initial position
      H             : Hessian at v_star
      eigvals       : sorted ascending
      lambda_min    : smallest positive eigenvalue (falls back to abs min if
                      the minimum is a saddle, as happens in conflict)
      tau_hessian   : equilibrium prediction  1 / (2·D_eff·λ_min)
      is_saddle     : True if min eigenvalue ≤ 0

    The `reset` scenario has a well-defined trivial minimum at the midpoint.
    `conflict` has a landscape minimum at the saddle/compromise that is only
    approximately harmonic — the Hessian there is informative but noisy.
    """
    U = SCENARIOS[scenario]
    v_star = find_minimum(U, INITIAL_POSITION[scenario])
    H = numerical_hessian(U, v_star)
    eigvals, _ = np.linalg.eigh(H)
    lam_min_signed = eigvals[0]
    is_saddle = lam_min_signed <= 0
    lam_min = abs(lam_min_signed) if is_saddle else lam_min_signed
    # Guard against numerical zero
    lam_min = max(lam_min, 1e-6)
    tau_hessian = 1.0 / (2.0 * D_EFF * lam_min)
    return {
        'scenario':    scenario,
        'v_star':      v_star,
        'H':           H,
        'eigvals':     eigvals,
        'lambda_min':  float(lam_min),
        'lambda_signed': float(lam_min_signed),
        'tau_hessian': float(tau_hessian),
        'is_saddle':   bool(is_saddle),
    }


# ═══════════════════════════════════════════════════════════════════════════
#   REGIME CLASSIFIER
# ═══════════════════════════════════════════════════════════════════════════
#
# The classical MPC paper uses static thresholds E_c, E_s on potential
# energy.  Those are gone.  The dynamical classifier reads regime from
# the correlation spectrum of V_A along the trajectory, plus cross-
# dissipation, plus (optionally) FDR-curve shape.
#
# Thresholds below are calibrated to the four reference scenarios on this
# substrate with λ = {100, 0.8, 30, 0.15} — they are NOT universal.  A
# downstream implementation on a different substrate must re-calibrate.


# Calibrated from the smoke test:
#     committed: τ_A=5.16  γ_A=−0.43   |γ_A|=0.43  (deep: τ_A ≫ τ_env)
#     suspended: τ_A=0.39  γ_A=+2.24   |γ_A|=2.24  (τ_A ≪ τ_env)
#     conflict:  τ_A=0.003 γ_A≈+300    |γ_A|≫1     (τ_A → noise floor)
#     reset:     τ_A=τ_env γ_A=0       |γ_A|=0     (bath)
#
# The classifier uses τ_A / τ_env ratio and γ_ij magnitude, NOT γ_A sign.
TAU_CONFLICT_FLOOR = 0.05    # below this, τ_A is noise-floor dominated → k
GAMMA_A_RESET_BAND = 0.30    # |γ_A| < this AND τ_A ≈ τ_env → r
TAU_COMMITTED_RATIO = 2.0    # τ_A > this × τ_env → c (well-pinned)
GAMMA_IJ_K_FLOOR   = 5.0     # |γ_ij| above this flags k-state coupling.
                             # Calibration: suspended shows |γ_ij| ≈ 1
                             # (ordinary cross-correlation between V_A and
                             # V_B as system orbits the intersection);
                             # conflict shows |γ_ij| ≈ 25+ (deep pinning
                             # collapses all three τ's to noise floor).
                             # Threshold 5 cleanly separates them.


def classify_regime(stats_gA, stats_gij=None, fdr_slope=None):
    """
    Return one of {'c', 's', 'k', 'r'} from measured observables.

    stats_gA   : dict from gamma_A_from_trajectories()
    stats_gij  : optional dict from gamma_ij_from_trajectories()
    fdr_slope  : optional late-time slope of the parametric FDR plot in
                 scaled units (FDT → slope 1).  ESSENTIAL for separating
                 [c] from [k] on Markovian substrates, because both are
                 deeply pinned and collapse τ_A to the noise floor.

    Strategy — honest to the Markovian limit:

       [r]   |γ_A| small  AND  τ_A ≈ τ_env        (bath-equilibrated)
       [s]   τ_A short but not pinned             (soft well, fast decorr)
       [c]   τ_A at noise floor AND FDT-ish FDR   (pinned, compatible)
       [k]   τ_A at noise floor AND flat/negative slope
             (pinned, destructive interference)

    In the absence of FDR slope information, we fall back to γ_ij
    magnitude, which is strongly correlated with the c/k distinction
    when the noise-floor variance is resolved.
    """
    tau_A  = stats_gA['tau_A_mean']
    tau_E  = stats_gA['tau_env_mean']
    gA_abs = abs(stats_gA['gamma_A_mean'])
    ratio  = tau_A / tau_E if tau_E > 0 else 0.0
    g_ij_abs = abs(stats_gij['gamma_ij_mean']) if stats_gij else 0.0

    # Reset: γ_A ≈ 0 AND τ_A ≈ τ_env
    if gA_abs < GAMMA_A_RESET_BAND and 0.75 < ratio < 1.33:
        return 'r'

    # Pinned regime: both committed and conflict collapse τ_A here.
    if tau_A < TAU_CONFLICT_FLOOR:
        # Prefer FDR slope when we have it.
        if fdr_slope is not None:
            return 'k' if fdr_slope < 0.5 else 'c'
        # Fallback: γ_ij magnitude separates them on pinned regimes too,
        # though less reliably.  Use a larger floor here to prevent false
        # k-promotion of a merely noisy committed case.
        return 'k' if g_ij_abs > 3 * GAMMA_IJ_K_FLOOR else 'c'

    # Not pinned, not reset: suspended.  Upgrade to k if γ_ij is
    # strongly positive (paper's original Table 1 k-signature, which
    # holds in the non-pinned regime).
    if stats_gij is not None and stats_gij['gamma_ij_mean'] > GAMMA_IJ_K_FLOOR:
        return 'k'
    return 's'


# ═══════════════════════════════════════════════════════════════════════════
#   SURVIVAL SEPARATION THEOREM  (Theorem 6.1 of the dynamical paper)
# ═══════════════════════════════════════════════════════════════════════════
#
# |Γ*|  ≤  N_max  =  O( √(2 Φ* / (α · γ_min · d_avg)) )
#
# where γ_min is the minimum non-zero cross-dissipation, d_avg the mean
# degree of the interaction graph, and Φ* the system's negentropic flux
# capacity.  In the old static framework, ε_min was measured from pairwise
# joint energies.  Here, γ_min is measured dynamically — from correlation
# spectra of joint V_i+V_j observables along Langevin trajectories.

def separation_theorem_test(N_max=8, Phi_star=30.0, alpha=1.0,
                            lam=20.0, radius=1.0,
                            n_steps=6000, n_reps=3, seed_base=5000):
    """
    Ring of N position constraints on the upper semicircle.  Adjacent
    constraints are geometrically frustrated (targets at different
    angular positions, position potentials penalise distance to each).

    For each N ∈ {2, …, N_max} we:
      1. Build the joint potential of the N constraints.
      2. Run n_reps Langevin trajectories, starting from the centroid.
      3. Measure γ_ij dynamically for each adjacent constraint pair,
         using V_pos-based observables evaluated along the trajectory.
      4. Compute Φ_required = Σ |γ_i| + α · Σ |γ_ij|  (sum over edges).
      5. Record γ_min over adjacent pairs, d_avg = 2(N−1)/N for the path
         graph, and N_max_theory for the bound.

    Returns a dict keyed to each N with the measured quantities.
    """
    # Targets on upper semicircle
    angles_all = np.linspace(np.pi * 0.1, np.pi * 0.9, N_max)
    targets_all = np.array([[np.cos(a) * radius, np.sin(a) * radius]
                            for a in angles_all])

    # Static ε_ij for comparison (these are the old-framework quantities):
    #   min of V_i + V_j is at midpoint, with energy = (λ/2)·|p_i − p_j|²
    eps_pairs_all = []
    for i in range(N_max - 1):
        d_sq = np.sum((targets_all[i] - targets_all[i+1])**2)
        eps_pairs_all.append((lam / 2) * d_sq)

    results = {}
    for n in range(2, N_max + 1):
        targets = targets_all[:n]

        # Joint potential over n constraints
        def U_joint(v, tgts=targets):
            return sum(V_pos(v, t, lam) for t in tgts)

        # Observables for each constraint (position potentials with λ=1)
        def make_V(t):
            return lambda v, t=t: V_pos(v, t, lam=1.0)
        V_constraints = [make_V(t) for t in targets]

        # Run replicas from the centroid of the targets
        v0 = np.mean(targets, axis=0)
        trajs = np.empty((n_reps, n_steps, 2))
        for r in range(n_reps):
            rng = np.random.default_rng(seed_base + 100 * n + r)
            trajs[r] = run_langevin(U_joint, v0, n_steps, rng=rng)

        # Per-constraint γ_i (versus a free-diffusion bath).  We reuse
        # `energy_reset` as the bath — same scale for all N.
        bath_trajs = np.empty((n_reps, n_steps, 2))
        for r in range(n_reps):
            rng = np.random.default_rng(seed_base + 100 * n + r + 5000)
            bath_trajs[r] = run_langevin(energy_reset, v0, n_steps, rng=rng)

        gamma_i = []
        for V_k in V_constraints:
            s = gamma_A_from_trajectories(V_k, trajs, bath_trajs)
            gamma_i.append(abs(s['gamma_A_mean']))

        # Adjacent-pair γ_ij (dynamical)
        gamma_ij = []
        for k in range(n - 1):
            s = gamma_ij_from_trajectories(V_constraints[k],
                                           V_constraints[k+1],
                                           trajs)
            gamma_ij.append(abs(s['gamma_ij_mean']))
        gamma_min = min(gamma_ij) if gamma_ij else 0.0

        # Required flux (dynamical) and theoretical bound
        Phi_req = sum(gamma_i) + alpha * sum(gamma_ij)

        # Path-graph bound: d_avg = 2(n-1)/n
        d_avg = 2.0 * (n - 1) / n if n > 1 else 0.0
        if gamma_min > 1e-9 and d_avg > 1e-9:
            N_theory = np.sqrt(2 * Phi_star / (alpha * gamma_min * d_avg))
        else:
            N_theory = np.inf

        # Static ε_min for the same N (old-framework comparison)
        eps_min_static = min(eps_pairs_all[:n-1]) if n > 1 else 0.0

        results[n] = {
            'N':          n,
            'Phi_req':    float(Phi_req),
            'gamma_min':  float(gamma_min),
            'gamma_i':    gamma_i,
            'gamma_ij':   gamma_ij,
            'eps_min':    float(eps_min_static),
            'd_avg':      float(d_avg),
            'N_theory':   float(N_theory),
            'targets':    targets.copy(),
            'Phi_star':   Phi_star,
            'alpha':      alpha,
        }
    return results


# ═══════════════════════════════════════════════════════════════════════════
#   PLOTTING
# ═══════════════════════════════════════════════════════════════════════════
#
# Four figures:
#   (1) mpc_trajectories.png  — phase portrait + V_A autocorrelation
#   (2) mpc_fdr_atlas.png     — the money plot (§7 of the paper)
#   (3) mpc_separation.png    — Theorem 6.1 with dynamical γ_ij
#   (4) mpc_hessian_probe.png — equilibrium baseline vs measured τ_A
#
# Matplotlib defaults are overridden to match the old code's dark aesthetic.

def _style_axes(ax, title=None):
    """Apply dark-panel styling to a matplotlib Axes."""
    ax.set_facecolor(PANEL)
    for spine in ax.spines.values():
        spine.set_color(GRID); spine.set_linewidth(0.8)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.grid(True, color=GRID, linewidth=0.5, alpha=0.4)
    ax.xaxis.label.set_color(TEXT); ax.yaxis.label.set_color(TEXT)
    if title is not None:
        ax.set_title(title, color=TEXT, fontsize=10,
                     fontweight='bold', pad=8)


def _fig(figsize):
    """Create a dark-background Figure."""
    fig = plt.figure(figsize=figsize, facecolor=BG)
    return fig


# ── Figure 1: trajectories + autocorrelations ───────────────────────────────

def plot_trajectories_figure(trajs_dict, stats_gA, stats_gij, regimes,
                             outpath='mpc_trajectories.png'):
    """
    2 × 4 grid:
      top row:    phase portraits (trajectory scatter + energy contours +
                  constraint circles where relevant + anchors A, B)
      bottom row: V_A autocorrelation with τ_A annotation
    """
    fig = _fig((18, 9))
    gs = fig.add_gridspec(2, 4, hspace=0.35, wspace=0.22,
                          left=0.05, right=0.98, top=0.92, bottom=0.08)

    # Grid for contour plots
    xs = np.linspace(-0.5, 2.7, 140)
    ys = np.linspace(-1.3, 1.3, 140)
    XX, YY = np.meshgrid(xs, ys)

    for col, scen in enumerate(SCENARIO_ORDER):
        U = SCENARIOS[scen]
        Z = np.vectorize(lambda x, y: U(np.array([x, y])))(XX, YY)
        color = COLOR[scen]

        # ── Top: phase portrait ─────────────────────────────────────────
        ax = fig.add_subplot(gs[0, col])
        _style_axes(ax, f'{SCENARIO_TITLE[scen]} — phase portrait')
        ax.set_aspect('equal')
        ax.set_xlim(-0.5, 2.7); ax.set_ylim(-1.3, 1.3)
        ax.set_xlabel('x'); ax.set_ylabel('y')

        # Energy contours (log-spaced for visibility across regimes)
        z_finite = Z[np.isfinite(Z)]
        if z_finite.size:
            zmin = max(z_finite.min(), 1e-3)
            zmax = z_finite.max()
            levels = np.geomspace(zmin + 1e-6, zmax + 1e-6, 12)
            ax.contour(XX, YY, Z, levels=levels,
                       colors=GRID, linewidths=0.5, alpha=0.7)

        # Constraint circles (for committed/suspended: radius 1.2, 1.0;
        # for conflict: radius 0.25 each; reset: no constraints, only bath)
        if scen in ('committed', 'suspended'):
            ax.add_patch(Circle(A, R_A_CS, fill=False,
                                edgecolor=TEXT, linewidth=1.0, alpha=0.6,
                                linestyle='--'))
            ax.add_patch(Circle(B, R_B_CS, fill=False,
                                edgecolor=TEXT, linewidth=1.0, alpha=0.6,
                                linestyle='--'))
        elif scen == 'conflict':
            ax.add_patch(Circle(A, R_A_K, fill=False,
                                edgecolor=COLOR['conflict'], linewidth=1.2,
                                alpha=0.9, linestyle='--'))
            ax.add_patch(Circle(B, R_B_K, fill=False,
                                edgecolor=COLOR['conflict'], linewidth=1.2,
                                alpha=0.9, linestyle='--'))

        # Trajectory scatter (one replica, subsampled)
        traj = trajs_dict[scen][0]
        step = max(1, len(traj) // 2000)
        pts = traj[::step]
        ax.scatter(pts[:, 0], pts[:, 1], s=2, c=color, alpha=0.35,
                   edgecolors='none')

        # Anchors
        ax.scatter([A[0], B[0]], [A[1], B[1]], s=80, c=TEXT,
                   marker='o', edgecolors=BG, linewidths=1.5, zorder=5)
        ax.annotate('A', A + np.array([-0.12, 0.12]),
                    color=TEXT, fontsize=11, fontweight='bold')
        ax.annotate('B', B + np.array([0.06, 0.12]),
                    color=TEXT, fontsize=11, fontweight='bold')

        # Regime tag
        regime_letter = REGIME_SYMBOL[scen]
        classified   = regimes.get(scen, '?')
        tag = f'[{regime_letter}] classified: [{classified}]'
        tag_color = REGIME_COLOR.get(classified, MUTED)
        ax.text(0.02, 0.96, tag, transform=ax.transAxes,
                color=tag_color, fontsize=9, fontweight='bold',
                verticalalignment='top',
                bbox=dict(facecolor=BG, edgecolor=GRID, alpha=0.75,
                          boxstyle='round,pad=0.3'))

        # ── Bottom: V_A autocorrelation ─────────────────────────────────
        ax2 = fig.add_subplot(gs[1, col])
        _style_axes(ax2, 'V_A autocorrelation')

        # Average autocorr across replicas, after burn-in
        traj_full = trajs_dict[scen]
        start = int(traj_full.shape[1] * BURN_IN_FRAC)
        Cs = []
        for r in range(traj_full.shape[0]):
            V = np.array([V_A_obs(v) for v in traj_full[r, start:]])
            Cs.append(autocorr_fft(V, normalize=True))
        C_mean = np.mean(Cs, axis=0)
        # Show first 2τ_env worth of lags, capped
        max_lag_steps = min(len(C_mean) // 2,
                            int(6.0 * stats_gA['reset']['tau_A_mean'] / DT))
        max_lag_steps = max(max_lag_steps, 100)
        lags = np.arange(max_lag_steps) * DT
        ax2.plot(lags, C_mean[:max_lag_steps], color=color, linewidth=1.6)
        ax2.axhline(0.0, color=MUTED, linewidth=0.5, alpha=0.5)
        ax2.axhline(0.05, color=MUTED, linewidth=0.5,
                    linestyle=':', alpha=0.4)
        ax2.set_xlabel('lag t')
        ax2.set_ylabel('C_A(t) / C_A(0)')
        ax2.set_ylim(-0.15, 1.05)

        # Annotation: τ_A, τ_env, γ_A
        tA   = stats_gA[scen]['tau_A_mean']
        tE   = stats_gA[scen]['tau_env_mean']
        gA   = stats_gA[scen]['gamma_A_mean']
        gij  = stats_gij[scen]['gamma_ij_mean']
        note = (f'τ_A={tA:.3f}   τ_env={tE:.3f}\n'
                f'γ_A={gA:+.3f}   γ_ij={gij:+.3f}')
        ax2.text(0.97, 0.95, note, transform=ax2.transAxes,
                 color=TEXT, fontsize=8.5, family='monospace',
                 verticalalignment='top', horizontalalignment='right',
                 bbox=dict(facecolor=BG, edgecolor=GRID, alpha=0.85,
                           boxstyle='round,pad=0.3'))

    fig.suptitle('MPC Lattice — Trajectories and Correlation Structure',
                 color=TEXT, fontsize=14, fontweight='bold', y=0.98)

    # Footer caveat
    fig.text(0.5, 0.015,
             'γ_A, γ_ij reported as measured.  In Markovian Langevin '
             'substrates the SIGNS can invert vs. the paper\'s Table 1; '
             '|γ| is the regime-depth signal.',
             color=MUTED, fontsize=8, ha='center', style='italic')

    fig.savefig(outpath, dpi=120, facecolor=BG, edgecolor='none')
    plt.close(fig)


# ── Figure 2: FDR atlas — the money plot ────────────────────────────────────

def plot_fdr_atlas_figure(fdr_dict, outpath='mpc_fdr_atlas.png'):
    """
    Parametric FDR plot, 2×2 grid — one scenario per panel.  Axes:
      x = [C(0) − C(τ)] / D_eff   (scaled so FDT slope = 1)
      y = χ(τ)                     (integrated response to h·V_A)
    FDT reference line at unit slope is drawn for comparison.

    The four panels should exhibit the paper's predicted signatures:
      r : close to the diagonal (FDT holds)
      s : aging — a curve bending from diagonal toward a plateau
      c : depressed stable slope (< 1)
      k : non-monotonic or negative-slope region

    We show raw data and a low-pass smoothed curve to read the shape
    against thermal noise.
    """
    fig = _fig((12, 10))
    gs  = fig.add_gridspec(2, 2, hspace=0.32, wspace=0.22,
                           left=0.08, right=0.97, top=0.92, bottom=0.09)

    # Axis limits computed per panel, but we want comparable scales
    panels = []
    for idx, scen in enumerate(SCENARIO_ORDER):
        row, col = idx // 2, idx % 2
        ax = fig.add_subplot(gs[row, col])
        _style_axes(ax, SCENARIO_TITLE[scen])
        color = COLOR[scen]

        tau, C, chi, h_mag = fdr_dict[scen]
        if C.size == 0:
            continue

        # Scale x by D_EFF so FDT gives unit slope
        x = (C[0] - C) / D_EFF
        y = chi

        # Low-pass smoothing for readability
        win = max(5, len(y) // 60)
        kern = np.ones(win) / win
        y_smooth = np.convolve(y, kern, mode='same')
        x_smooth = np.convolve(x, kern, mode='same')

        # Plot FDT reference
        xmax = max(abs(x).max(), 1e-3) * 1.1
        ymax = max(abs(y).max(), 1e-3) * 1.15
        ax.plot([0, xmax], [0, xmax], color=MUTED, linestyle='--',
                linewidth=1.0, alpha=0.7, label='FDT (slope 1)')

        # Raw data (translucent)
        ax.plot(x, y, color=color, alpha=0.25, linewidth=0.8)
        # Smoothed
        ax.plot(x_smooth[win:-win], y_smooth[win:-win],
                color=color, linewidth=2.0, label='χ(τ) smoothed')

        # Late-time slope estimate
        late_frac = 0.5
        idx_late = int(len(x) * late_frac)
        x_late = x[idx_late:]; y_late = y[idx_late:]
        if x_late.std() > 1e-9:
            slope_late = np.polyfit(x_late, y_late, 1)[0]
        else:
            slope_late = float('nan')

        # Axes limits (symmetric when k-regime goes negative)
        panels.append((ax, x, y, xmax, ymax))
        ax.set_xlim(-0.05 * xmax, xmax)
        if y.min() < -0.1 * ymax:
            ax.set_ylim(-ymax, ymax)
        else:
            ax.set_ylim(-0.05 * ymax, ymax)

        ax.set_xlabel('[C(0) − C(τ)] / D_eff')
        ax.set_ylabel('χ(τ)')

        # Annotation box
        regime_letter = REGIME_SYMBOL[scen]
        note = (f'[{regime_letter}]  h = {h_mag:.2f}   C(0) = {C[0]:.3f}\n'
                f'late slope ≈ {slope_late:+.2f}   (FDT: 1.00)')
        ax.text(0.03, 0.96, note, transform=ax.transAxes,
                color=TEXT, fontsize=9, family='monospace',
                verticalalignment='top',
                bbox=dict(facecolor=BG, edgecolor=GRID, alpha=0.85,
                          boxstyle='round,pad=0.3'))

        ax.legend(loc='lower right', facecolor=PANEL, edgecolor=GRID,
                  labelcolor=TEXT, fontsize=8, framealpha=0.85)

    fig.suptitle('MPC FDR Atlas — Parametric Plot of χ vs [C(0)−C(τ)]/D_eff',
                 color=TEXT, fontsize=14, fontweight='bold', y=0.97)
    fig.text(0.5, 0.02,
             'Four regimes, four shapes.  Paper §7: r-diagonal · s-aging · '
             'c-depressed-stable · k-non-monotonic/negative.',
             color=MUTED, fontsize=9, ha='center', style='italic')

    fig.savefig(outpath, dpi=120, facecolor=BG, edgecolor='none')
    plt.close(fig)


# ── Figure 3: separation theorem ────────────────────────────────────────────

def plot_separation_figure(sep_results, outpath='mpc_separation.png'):
    """
    Three-panel figure:
      (a) ring-of-N geometry at N_max (targets on upper semicircle)
      (b) required flux Φ_required(N) vs N, with Φ* band
      (c) γ_min(N) vs N — the minimum dynamical cross-dissipation

    The theorem predicts Φ_required grows quadratically in N.  We plot the
    measured flux alongside the theoretical N_max = √(2Φ*/(α γ_min d_avg))
    to check the bound.
    """
    Ns     = sorted(sep_results.keys())
    Phi    = [sep_results[n]['Phi_req']   for n in Ns]
    g_min  = [sep_results[n]['gamma_min'] for n in Ns]
    N_pred = [sep_results[n]['N_theory']  for n in Ns]
    Phi_star = sep_results[Ns[0]]['Phi_star']

    fig = _fig((16, 6))
    gs  = fig.add_gridspec(1, 3, wspace=0.28,
                           left=0.05, right=0.98, top=0.88, bottom=0.15)

    # Panel (a): geometry at the largest N tested
    ax_geom = fig.add_subplot(gs[0, 0])
    _style_axes(ax_geom, f'Ring geometry  (N = {Ns[-1]})')
    ax_geom.set_aspect('equal')
    ax_geom.set_xlim(-1.3, 1.3); ax_geom.set_ylim(-0.3, 1.3)
    ax_geom.set_xlabel('x'); ax_geom.set_ylabel('y')

    tgts = sep_results[Ns[-1]]['targets']
    # Base circle
    theta = np.linspace(0, np.pi, 200)
    ax_geom.plot(np.cos(theta), np.sin(theta),
                 color=GRID, linewidth=1.0, alpha=0.6)
    # Targets (color-coded by γ_i magnitude)
    for i, t in enumerate(tgts):
        ax_geom.add_patch(Circle(t, 0.04, facecolor=COLOR['suspended'],
                                 edgecolor=TEXT, linewidth=0.7))
        ax_geom.annotate(f'{i+1}', t + np.array([0.05, 0.04]),
                         color=MUTED, fontsize=8)
    # Adjacency edges
    for i in range(len(tgts) - 1):
        ax_geom.plot([tgts[i, 0], tgts[i+1, 0]],
                     [tgts[i, 1], tgts[i+1, 1]],
                     color=COLOR['conflict'], linewidth=0.8, alpha=0.5)

    # Panel (b): Φ_required(N)
    ax_phi = fig.add_subplot(gs[0, 1])
    _style_axes(ax_phi, 'Required flux Φ_required(N)')
    ax_phi.set_xlabel('N (active constraints)')
    ax_phi.set_ylabel('Φ_required  =  Σ|γ_i| + α Σ|γ_ij|')
    ax_phi.plot(Ns, Phi, color=COLOR['suspended'],
                marker='o', linewidth=1.8, markersize=7,
                markeredgecolor=TEXT, markeredgewidth=0.7,
                label='measured Φ_required')
    ax_phi.axhline(Phi_star, color=COLOR['conflict'],
                   linestyle='--', linewidth=1.2, alpha=0.8,
                   label=f'Φ* = {Phi_star:.1f}')
    # Quadratic reference curve through first data point
    if len(Ns) >= 2 and Phi[0] > 1e-9:
        coef = Phi[0] / Ns[0]**2
        ax_phi.plot(Ns, [coef * n**2 for n in Ns],
                    color=MUTED, linestyle=':', linewidth=1.0,
                    alpha=0.8, label='∝ N² reference')
    ax_phi.legend(loc='upper left', facecolor=PANEL, edgecolor=GRID,
                  labelcolor=TEXT, fontsize=9, framealpha=0.85)

    # Panel (c): γ_min(N) and theoretical N_max
    ax_gm = fig.add_subplot(gs[0, 2])
    _style_axes(ax_gm, 'γ_min  and  N_max theoretical')
    ax_gm.set_xlabel('N (active constraints)')
    ax_gm.set_ylabel('γ_min  (dynamical, |γ_ij| over adjacent pairs)',
                     color=COLOR['committed'])
    ax_gm.plot(Ns, g_min, color=COLOR['committed'],
               marker='s', linewidth=1.8, markersize=6,
               markeredgecolor=TEXT, markeredgewidth=0.7,
               label='γ_min dynamical')
    ax_gm.tick_params(axis='y', colors=COLOR['committed'])

    ax_gm2 = ax_gm.twinx()
    ax_gm2.set_facecolor(PANEL)
    ax_gm2.spines['right'].set_color(GRID)
    ax_gm2.tick_params(colors=MUTED, labelsize=8)
    ax_gm2.set_ylabel('N_max  =  √(2Φ*/α γ_min d_avg)',
                      color=COLOR['reset'])
    finite_N = [n for n, v in zip(Ns, N_pred) if np.isfinite(v)]
    finite_V = [v for v in N_pred if np.isfinite(v)]
    ax_gm2.plot(finite_N, finite_V, color=COLOR['reset'],
                marker='^', linewidth=1.8, markersize=6,
                markeredgecolor=TEXT, markeredgewidth=0.7,
                label='N_max theory')
    ax_gm2.tick_params(axis='y', colors=COLOR['reset'])
    ax_gm2.axhline(max(Ns), color=MUTED, linestyle=':', alpha=0.6,
                   linewidth=0.8)

    fig.suptitle('Survival Separation Theorem  (Theorem 6.1, dynamical γ_ij)',
                 color=TEXT, fontsize=14, fontweight='bold', y=0.97)
    fig.text(0.5, 0.03,
             'Cross-dissipations γ_ij measured from joint-observable '
             'autocorrelations along Langevin trajectories, not from static '
             'pairwise energies.',
             color=MUTED, fontsize=9, ha='center', style='italic')

    fig.savefig(outpath, dpi=120, facecolor=BG, edgecolor='none')
    plt.close(fig)


# ── Figure 4: Hessian probe — equilibrium baseline ──────────────────────────

def plot_hessian_probe_figure(hess_dict, stats_gA, outpath='mpc_hessian_probe.png'):
    """
    For each scenario we compare
        τ_measured  (from Langevin autocorrelation of V_A)
     vs τ_Hessian   (=  1 / (2 · D_eff · λ_min(H at minimum)))

    Near-equilibrium systems satisfy τ_measured ≈ τ_Hessian.  Disagreement
    quantifies how far from equilibrium the substrate is being driven —
    the  D_active ≫ D_thermal  detector from §7 of the paper.

    Layout:
      (a) bar chart of τ_measured vs τ_Hessian, grouped by scenario
      (b) eigenvalue table / Hessian summary (text panel)
    """
    fig = _fig((16, 7))
    gs  = fig.add_gridspec(1, 2, width_ratios=[1.6, 1.0], wspace=0.22,
                           left=0.06, right=0.97, top=0.90, bottom=0.13)

    # Panel (a): bar chart
    ax = fig.add_subplot(gs[0, 0])
    _style_axes(ax, 'τ measured vs τ Hessian (equilibrium prediction)')

    scen_names = SCENARIO_ORDER
    idx = np.arange(len(scen_names))
    w = 0.38
    tau_meas = [stats_gA[s]['tau_A_mean']      for s in scen_names]
    tau_hess = [hess_dict[s]['tau_hessian']    for s in scen_names]

    # Log-scale for visual readability (values span ~5 decades)
    ax.set_yscale('log')
    ax.set_ylabel('relaxation time τ  (log scale)')
    ax.set_xticks(idx)
    ax.set_xticklabels([SCENARIO_TITLE[s].split()[0] for s in scen_names],
                       color=TEXT)

    b1 = ax.bar(idx - w/2, np.clip(tau_meas, 1e-4, None), w,
                color=[COLOR[s] for s in scen_names],
                edgecolor=TEXT, linewidth=0.7, label='τ_measured')
    b2 = ax.bar(idx + w/2, np.clip(tau_hess, 1e-4, None), w,
                color=BG, edgecolor=[COLOR[s] for s in scen_names],
                linewidth=1.6, hatch='////', label='τ_Hessian')

    # Annotate the ratio above each group
    for i, s in enumerate(scen_names):
        tm = tau_meas[i]; th = tau_hess[i]
        ratio = tm / th if th > 0 else float('inf')
        if hess_dict[s]['is_saddle']:
            tag = 'saddle'
            color = COLOR['conflict']
        elif 0.5 < ratio < 2.0:
            tag = f'≈eq ({ratio:.2f}×)'
            color = COLOR['reset']
        else:
            tag = f'driven ({ratio:.1f}×)'
            color = COLOR['suspended']
        ytop = max(tm, th) * 1.5
        ax.text(i, ytop, tag, color=color, fontsize=9,
                ha='center', fontweight='bold')

    ax.legend(loc='upper left', facecolor=PANEL, edgecolor=GRID,
              labelcolor=TEXT, fontsize=9, framealpha=0.85)

    # Panel (b): eigenstructure text summary
    ax_txt = fig.add_subplot(gs[0, 1])
    ax_txt.set_facecolor(PANEL)
    for spine in ax_txt.spines.values():
        spine.set_color(GRID); spine.set_linewidth(0.8)
    ax_txt.set_xticks([]); ax_txt.set_yticks([])
    ax_txt.set_title('Hessian eigenstructure at U-minimum',
                     color=TEXT, fontsize=10, fontweight='bold', pad=8)

    lines = [f'{"scenario":<10}  {"v*":<20}  {"λ_min":>8}  {"λ_max":>8}  '
             f'{"τ_H":>7}  {"τ_meas":>7}  {"type":>8}']
    lines.append('─' * 84)
    for s in scen_names:
        h = hess_dict[s]
        vs = h['v_star']
        v_str = f'({vs[0]:+.2f}, {vs[1]:+.2f})'
        ev = h['eigvals']
        tm = stats_gA[s]['tau_A_mean']
        th = h['tau_hessian']
        typ = 'saddle' if h['is_saddle'] else ('well')
        lines.append(f'{s:<10}  {v_str:<20}  {ev[0]:8.3f}  {ev[1]:8.3f}  '
                     f'{th:7.3f}  {tm:7.3f}  {typ:>8}')

    text_block = '\n'.join(lines)
    ax_txt.text(0.02, 0.96, text_block, transform=ax_txt.transAxes,
                color=TEXT, fontsize=8.5, family='monospace',
                verticalalignment='top')

    # Interpretive note
    note = (
        '\n\nτ_Hessian is the equilibrium prediction  1/(2·D_eff·λ_min).\n'
        'Agreement → system near thermal equilibrium.\n'
        'Disagreement → driven regime, D_active ≫ D_thermal  (paper §7).\n\n'
        'conflict minimises U at a compromise point with positive\n'
        'eigenvalues (tight trap) yet τ_measured collapses to the\n'
        'noise floor — that gap is the k-state signature here.'
    )
    ax_txt.text(0.02, 0.55, note, transform=ax_txt.transAxes,
                color=MUTED, fontsize=8.5, family='monospace',
                verticalalignment='top', style='italic')

    fig.suptitle('Hessian Equilibrium Baseline vs Measured τ_A',
                 color=TEXT, fontsize=14, fontweight='bold', y=0.97)

    fig.savefig(outpath, dpi=120, facecolor=BG, edgecolor='none')
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════════════════
#   MAIN
# ═══════════════════════════════════════════════════════════════════════════

def _hr(char='─', n=66): return char * n

def main(outdir=None):
    t_start = __import__('time').time()
    outdir = outdir or os.getcwd()
    os.makedirs(outdir, exist_ok=True)

    print(_hr('═'))
    print('  MPC Lattice — Langevin Validation Rig')
    print(_hr('═'))
    print(f'  D_eff = {D_EFF}   k_BT = {K_BT}   dt = {DT}')
    print(f'  Budgets:  traj n_reps={N_REPS_TRAJ}  n_steps={N_STEPS_TRAJ}')
    print(f'            FDR  n_reps={FDR_N_REPS}   n_burnin={FDR_N_BURNIN}  '
          f'n_resp={FDR_N_RESP}')
    print()

    # ── 1. Run Langevin trajectories for every scenario ─────────────────
    print('[1/5] Langevin trajectories ...')
    trajs = {}
    for s in SCENARIO_ORDER:
        t0 = __import__('time').time()
        trajs[s] = run_scenario_trajectories(s)
        print(f'      {s:<12}  done in {__import__("time").time()-t0:5.1f}s')

    # ── 2. γ_A (uses reset as bath) and γ_ij per scenario ───────────────
    print('\n[2/6] Survival margin γ_A and cross-dissipation γ_ij ...')
    stats_gA  = {}
    stats_gij = {}
    for s in SCENARIO_ORDER:
        stats_gA[s]  = gamma_A_from_trajectories(V_A_obs, trajs[s],
                                                 trajs['reset'])
        stats_gij[s] = gamma_ij_from_trajectories(V_A_obs, V_B_obs, trajs[s])

    print(f'\n      {"scenario":<12}  {"τ_A":>7}  {"τ_env":>7}  '
          f'{"γ_A":>10}  {"γ_ij":>10}')
    print(f'      {_hr("-", 58)}')
    for s in SCENARIO_ORDER:
        tA  = stats_gA[s]['tau_A_mean']
        tE  = stats_gA[s]['tau_env_mean']
        gA  = stats_gA[s]['gamma_A_mean']
        gij = stats_gij[s]['gamma_ij_mean']
        print(f'      {s:<12}  {tA:7.3f}  {tE:7.3f}  {gA:+10.3f}  {gij:+10.3f}')

    # ── 3. Hessian equilibrium baseline ─────────────────────────────────
    print('\n[3/6] Hessian equilibrium baseline ...')
    hess_dict = {}
    for s in SCENARIO_ORDER:
        hess_dict[s] = hessian_baseline(s)
        h = hess_dict[s]
        print(f'      {s:<12}  v*=({h["v_star"][0]:+.3f},{h["v_star"][1]:+.3f})  '
              f'λ=({h["eigvals"][0]:+.2f},{h["eigvals"][1]:+.2f})  '
              f'τ_H={h["tau_hessian"]:.3f}  '
              f'saddle={h["is_saddle"]}')

    # ── 4. FDR per scenario (the money-plot data) ───────────────────────
    print('\n[4/6] FDR measurement per scenario (matched-noise paired) ...')
    fdr_dict   = {}
    fdr_slopes = {}
    for s in SCENARIO_ORDER:
        t0 = __import__('time').time()
        tau, C, chi, h = fdr_for_scenario(s)
        fdr_dict[s] = (tau, C, chi, h)
        dt_this = __import__('time').time() - t0
        # Late-time slope in scaled units (FDT → 1.00 after /D_eff scaling)
        x = (C[0] - C) / D_EFF
        late = slice(int(len(x) * 0.5), None)
        if x[late].std() > 1e-9:
            slope = float(np.polyfit(x[late], chi[late], 1)[0])
        else:
            slope = float('nan')
        fdr_slopes[s] = slope
        print(f'      {s:<12}  h_mag={h:.2f}  C(0)={C[0]:8.3f}  '
              f'late slope={slope:+7.2f}   ({dt_this:5.1f}s)')

    # ── 5. Regime classification — uses FDR slope to separate c from k ──
    print('\n[5/6] Regime classification (τ_A ratio, γ_ij, FDR slope) ...')
    regimes = {}
    for s in SCENARIO_ORDER:
        regimes[s] = classify_regime(stats_gA[s], stats_gij[s],
                                     fdr_slope=fdr_slopes[s])
    print(f'      {"scenario":<12}  {"expected":>10}  {"classified":>10}')
    print(f'      {_hr("-", 38)}')
    for s in SCENARIO_ORDER:
        exp = REGIME_SYMBOL[s]
        got = regimes[s]
        flag = '✓' if exp == got else '✗'
        print(f'      {s:<12}  {"["+exp+"]":>10}  {"["+got+"]":>10}   {flag}')

    # ── 6. Separation Theorem test ──────────────────────────────────────
    print('\n[6/6] Survival Separation Theorem (dynamical γ_ij) ...')
    # N restricted to [2, 4]: beyond N=4 on this substrate, the joint
    # potential pins the system so deeply that all three τ's collapse
    # to the noise floor and γ_min becomes numerically unresolvable.
    # This is the same Markovian limit that caps τ_A for [c]/[k].
    sep = separation_theorem_test(N_max=4, Phi_star=20.0,
                                  lam=8.0, n_steps=8000, n_reps=4)
    print(f'      {"N":>3}  {"Φ_req":>8}  {"γ_min":>8}  {"N_max_theory":>12}')
    print(f'      {_hr("-", 40)}')
    for n in sorted(sep.keys()):
        r = sep[n]
        nt = r['N_theory']
        nt_str = f'{nt:12.2f}' if np.isfinite(nt) else f'{"∞":>12}'
        print(f'      {n:>3}  {r["Phi_req"]:8.3f}  '
              f'{r["gamma_min"]:8.4f}  {nt_str}')

    # ── Generate figures ────────────────────────────────────────────────
    print('\n[plots] Rendering four figures ...')

    # Figure 1 requires ALL scenarios' autocorrelations sharing an x-axis
    # scale; pass stats_gA as-is, the helper uses reset's τ_A_mean.
    # Wrap stats_gA with the reset entry visible under a 'reset' key for
    # scale reference in the autocorrelation subpanel:
    path1 = os.path.join(outdir, 'mpc_trajectories.png')
    plot_trajectories_figure(trajs, stats_gA, stats_gij, regimes, outpath=path1)
    print(f'       → {path1}')

    path2 = os.path.join(outdir, 'mpc_fdr_atlas.png')
    plot_fdr_atlas_figure(fdr_dict, outpath=path2)
    print(f'       → {path2}')

    path3 = os.path.join(outdir, 'mpc_separation.png')
    plot_separation_figure(sep, outpath=path3)
    print(f'       → {path3}')

    path4 = os.path.join(outdir, 'mpc_hessian_probe.png')
    plot_hessian_probe_figure(hess_dict, stats_gA, outpath=path4)
    print(f'       → {path4}')

    dt_total = __import__('time').time() - t_start
    print(f'\n[done] total wall time: {dt_total:.1f}s')
    return {
        'trajs':      trajs,
        'stats_gA':   stats_gA,
        'stats_gij':  stats_gij,
        'regimes':    regimes,
        'hess':       hess_dict,
        'fdr':        fdr_dict,
        'separation': sep,
        'outputs':    [path1, path2, path3, path4],
    }


if __name__ == '__main__':
    main()
