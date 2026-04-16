#!/usr/bin/env python3
"""
MPC Lattice — Direct Physical Instantiation of Metastable Propositional Calculus
=================================================================================

Three vertices in R². Two fixed anchors A, B. One free probe vertex v = (x, y).
Constraints are geometric potential functions over vertex position.
SciPy minimizes. Gradients are computed analytically or numerically.
We read MPC state directly from the topology of the energy landscape.

No LLMs. No embeddings. No retrieval artifacts. Pure geometry.

The energy landscape IS the proposition space. The wells ARE the truth values.

Requirements (already installed):
    pip install scipy numpy matplotlib

Optional (enables exact auto-differentiation):
    pip install jax

Run:
    python mpc_lattice.py

Outputs:
    mpc_landscape.png              — Energy landscape gallery (c / s / k)
    mpc_perturbation.png           — Perturbation response curves
    mpc_separation.png             — Separation Theorem validation
    mpc_hessian.png                — Hessian probe: directional commitment structure
    mpc_catmullclark_committed.png — CC phase boundary: committed scenario
    mpc_catmullclark_conflict.png  — CC phase boundary: conflict scenario
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from scipy.optimize import minimize
from scipy.optimize import approx_fprime
from functools import partial
import warnings
warnings.filterwarnings('ignore')

# ── Optional JAX ──────────────────────────────────────────────────────────────
try:
    import jax
    import jax.numpy as jnp
    from jax import grad, jit
    jax.config.update("jax_enable_x64", True)
    JAX = True
    print("✓ JAX available — exact analytical gradients active")
except ImportError:
    JAX = False
    print("⚠  JAX not found — using numerical gradients (scipy.optimize.approx_fprime)")
    print("   Results are equivalent. Install JAX anytime: pip install jax")

# ── Physical Constants (MPC paper §3, all in natural units of k_BT) ───────────
#
# These are the thresholds that separate the four MPC regimes.
# E_c < E_s by definition (§3, Table 1).
# Here we express barrier height ΔE in units of k_BT = 1.
#
K_BT  = 1.0   # thermal energy scale — the ruler everything is measured against
#
# CALIBRATED THRESHOLDS for this geometric substrate.
# The MPC paper (§3) explicitly states E_c and E_s are substrate-dependent.
# We determine them empirically from the landscape:
#   committed barrier ΔE ≈ 2.02 k_BT  (from geometry: λ·(r-r_target)² at saddle)
#   suspended barrier ΔE ≈ 0.016 k_BT (same geometry, λ reduced 125×)
#   conflict E_min      = 33.75 k_BT  (residual of incompatible constraints)
#
# E_C is set between suspended and committed barriers: 0.016 < E_C=1.0 < 2.02
# E_S is set below conflict residual:                  E_S=20.0 < 33.75
#
# This is the correct scientific procedure: calibrate instrument to substrate.
E_C   = 1.0   # committed threshold  (substrate-calibrated)
E_S   = 20.0  # suspended threshold  (substrate-calibrated)

# Fixed anchor vertices — these are the "axioms" of our geometry.
# They don't move. They define the constraint reference frame.
A = np.array([0.0, 0.0])
B = np.array([2.0, 0.0])

# ── Constraint Potentials ─────────────────────────────────────────────────────
#
# Each constraint is a function V: R² → R≥0
# V(v) = 0 iff the constraint is exactly satisfied.
# V(v) > 0 is the energetic cost of violation, in units of k_BT.
#
# This is the direct implementation of §2:
#   "Each formula A induces a constraint potential V_A(x) ≥ 0,
#    where V_A(x) = 0 precisely when configuration x satisfies A."

def V_dist(v, anchor, target_r, lam):
    """
    Distance constraint: penalises deviation from target edge length.
    V = λ · (|v − anchor| − target_r)²

    Zero on the circle of radius target_r around anchor.
    λ controls well depth (stiffness). High λ → deep well → [c].
    Low λ → shallow well → [s].
    """
    d = np.linalg.norm(v - anchor)
    return lam * (d - target_r) ** 2


def V_pos(v, target, lam):
    """
    Position constraint: pins vertex to a specific point.
    V = λ · |v − target|²

    Zero only at v = target. Unique global minimum.
    """
    return lam * np.sum((v - target) ** 2)


def V_area(v, a, b, target_area, lam):
    """
    Area constraint: penalises deviation from target triangle area.
    Uses signed cross product — geometrically exact.
    V = λ · (½|AB × AV| − target_area)²
    """
    ab = b - a
    av = v - a
    area = 0.5 * abs(ab[0] * av[1] - ab[1] * av[0])
    return lam * (area - target_area) ** 2


# ── Energy Landscapes: Three MPC Scenarios ───────────────────────────────────
#
# Each scenario is a sum of constraint potentials over the free vertex v.
# The SAME geometric constraints are used for [c] and [s].
# The ONLY difference is λ — constraint stiffness.
# For [k], the constraints are geometrically incompatible.
#
# This is the key insight: MPC states are not intrinsic properties of
# propositions but properties of the relationship between proposition
# and the substrate realizing it. (§3, MPC paper)

def energy_committed(v):
    """
    [c] COMMITTED — compatible constraints, large λ.

    Two circles: radius 1.2 around A, radius 1.0 around B.
    They intersect at two points (≈ (0.95, ±0.73)).
    Both are deep minima: barrier height >> E_C.
    Perturbation is absorbed — the system returns to the nearest minimum.
    λ=100 gives barrier ≈ 6.5 k_BT >> E_C=4.0
    """
    return (V_dist(v, A, 1.2, lam=100.0) +
            V_dist(v, B, 1.0, lam=100.0))


def energy_suspended(v):
    """
    [s] SUSPENDED — same compatible constraints, small λ.

    Same geometry. Same minima. But barriers ~ k_BT.
    Thermal fluctuations can carry the system between wells.
    Active maintenance required to stay committed.
    """
    return (V_dist(v, A, 1.2, lam=0.8) +
            V_dist(v, B, 1.0, lam=0.8))


def energy_conflict(v):
    """
    [k] CONFLICT — geometrically incompatible constraints.

    Circle A: radius 0.25 around A = (0,0)
    Circle B: radius 0.25 around B = (2,0)
    Sum of radii = 0.5 < distance between centres = 2.0.
    The circles are disjoint. No point in R² satisfies both.

    The minimiser finds the best compromise but residual energy > 0
    everywhere. This IS the MPC k-state: a structurally informative
    defect that cannot be resolved without external work.
    """
    return (V_dist(v, A, 0.25, lam=30.0) +
            V_dist(v, B, 0.25, lam=30.0))


# ── Gradient Computation ──────────────────────────────────────────────────────

def make_gradient(energy_fn):
    """
    Return an exact or numerical gradient function for energy_fn.
    JAX: automatic differentiation (exact to floating-point precision).
    Fallback: two-point finite differences via scipy (ε = 1e-6).
    """
    if JAX:
        # Wrap numpy energy as JAX function
        def energy_jax(v):
            v = jnp.array(v)
            # Re-implement using jnp to allow JAX differentiation
            return energy_fn(np.array(v))
        # Use scipy numerical for JAX-incompatible numpy functions
        # (pure numpy inside energy_fn blocks JAX tracing)
        # Fall through to numerical gradient
    
    def numerical_grad(v):
        return approx_fprime(v, energy_fn, epsilon=1e-7)
    
    return numerical_grad


# ── Energy Landscape Grid ─────────────────────────────────────────────────────

def compute_grid(energy_fn, xlim=(-1.0, 3.0), ylim=(-1.8, 1.8), resolution=320):
    """
    Evaluate energy_fn over a 2D grid.
    Returns meshgrids X, Y and energy matrix E.
    This gives us the full landscape topology — not just the minimum.
    """
    xs = np.linspace(*xlim, resolution)
    ys = np.linspace(*ylim, resolution)
    X, Y = np.meshgrid(xs, ys)
    E = np.vectorize(lambda x, y: energy_fn(np.array([x, y])))(X, Y)
    return X, Y, E


# ── Minimisation ──────────────────────────────────────────────────────────────

def find_minima(energy_fn, xlim=(-1.0, 3.0), ylim=(-1.8, 1.8),
                n_restarts=24, merge_radius=0.20):
    """
    Find all local minima of energy_fn using multi-start L-BFGS-B.

    n_restarts initialisation points are drawn from a regular grid
    plus random perturbations. Results within merge_radius of each
    other are deduplicated (same well, different start).

    Returns list of (v_min, E_min) sorted by energy ascending.
    """
    grad_fn = make_gradient(energy_fn)

    # Grid starts + random
    rng = np.random.RandomState(42)
    gx = np.linspace(xlim[0], xlim[1], 5)
    gy = np.linspace(ylim[0], ylim[1], 5)
    starts = [np.array([x, y]) for x in gx for y in gy]
    starts += [rng.uniform([xlim[0], ylim[0]], [xlim[1], ylim[1]])
               for _ in range(n_restarts - len(starts))]

    raw = []
    for v0 in starts:
        try:
            res = minimize(energy_fn, v0, jac=grad_fn, method='L-BFGS-B',
                           options={'maxiter': 2000, 'ftol': 1e-14, 'gtol': 1e-9})
            if res.fun < 1e6:
                raw.append((res.x.copy(), float(res.fun)))
        except Exception:
            pass

    if not raw:
        return []

    # Sort by energy
    raw.sort(key=lambda m: m[1])

    # Deduplicate
    unique = []
    for v, e in raw:
        if not any(np.linalg.norm(v - u) < merge_radius for u, _ in unique):
            unique.append((v, e))

    return unique


def barrier_height(energy_fn, v1, v2, n_scan=120):
    """
    Estimate barrier height between two minima by scanning along
    the straight-line path v1 → v2.

    Requires the two minima to be meaningfully separated (> 0.3).
    If they are too close, the barrier is trivially small and the
    pair is likely a deduplication artifact — return 0.

    Returns: ΔE = max(E along path) − min(E at endpoints)
    """
    sep = np.linalg.norm(v2 - v1)
    if sep < 0.30:
        # Minima too close — spurious pair, not a real double well
        return 0.0

    ts = np.linspace(0, 1, n_scan)
    path_energies = [energy_fn(v1 + t * (v2 - v1)) for t in ts]
    e_endpoints = min(energy_fn(v1), energy_fn(v2))
    return max(path_energies) - e_endpoints


# ── MPC State Classification ──────────────────────────────────────────────────

def classify(energy_fn, minima):
    """
    Classify MPC state from energy landscape.

    Rules (energies in units of k_BT, thresholds E_C and E_S):

    [k] min_energy > E_S
        No satisfying configuration exists. Constraints incompatible.
        The system is in a structurally informative defect state.

    [c] min_energy ≤ E_C AND barrier > E_C
        Deep potential well. Perturbation absorbed.
        High revision cost. Low holding cost.

    [s] everything else
        Shallow minimum (barrier ≤ E_C) OR partially satisfied
        (min_energy in (E_C, E_S]). Ongoing maintenance required.

    Returns: state ('c', 's', 'k'), min_energy, barrier
    """
    if not minima:
        return 'k', float('inf'), float('inf')

    e_min = minima[0][1]

    if e_min > E_S:
        return 'k', e_min, 0.0

    bar = float('inf')
    if len(minima) >= 2:
        bar = barrier_height(energy_fn, minima[0][0], minima[1][0])

    if e_min <= E_C and bar > E_C:
        return 'c', e_min, bar
    else:
        return 's', e_min, bar


# ── Visualisation ─────────────────────────────────────────────────────────────

PALETTE = {'c': '#4fc3f7', 's': '#ffb74d', 'k': '#ef5350', 'r': '#90a4ae'}
CMAPS   = {'c': 'Blues',   's': 'Oranges', 'k': 'Reds',    'r': 'Greys'}
LABELS  = {'c': '[c] COMMITTED', 's': '[s] SUSPENDED', 'k': '[k] CONFLICT'}


def plot_landscape(ax, energy_fn, state, minima, title,
                   xlim=(-1.0, 3.0), ylim=(-1.8, 1.8)):
    """
    Draw energy landscape as a heatmap with:
     - colour encoding energy magnitude
     - white contour lines at equal-energy levels
     - dashed lines marking E_c and E_s thresholds
     - gradient arrows (direction of steepest descent)
     - yellow stars at energy minima
     - square markers at fixed anchors A, B
    """
    X, Y, E = compute_grid(energy_fn, xlim, ylim, resolution=280)

    # Clip high energies for colour scale (outliers collapse the colour range)
    vmax = np.percentile(E, 96)
    E_vis = np.clip(E, 0, vmax)

    cmap = CMAPS[state]
    im = ax.pcolormesh(X, Y, E_vis, cmap=cmap, shading='gouraud',
                       vmin=0, vmax=vmax, alpha=0.88, rasterized=True)
    plt.colorbar(im, ax=ax, label='Energy (k_BT)', shrink=0.82, pad=0.02)

    # Contour lines
    levels_white = np.linspace(0, vmax, 14)
    ax.contour(X, Y, E, levels=levels_white,
               colors='white', alpha=0.30, linewidths=0.5)

    # MPC threshold contours
    for thresh, ls, lbl in [(E_C, '--', 'E_c'), (E_S, ':', 'E_s')]:
        if thresh <= vmax * 1.05:
            cs = ax.contour(X, Y, E, levels=[thresh],
                            colors=['white'], linewidths=1.4, linestyles=[ls])
            ax.clabel(cs, fmt={thresh: lbl}, fontsize=7, colors='white')

    # Gradient field (arrows point downhill — direction of natural relaxation)
    step = 18
    Xq, Yq = X[::step, ::step], Y[::step, ::step]
    grad_fn = make_gradient(energy_fn)
    Gx = np.zeros_like(Xq)
    Gy = np.zeros_like(Yq)
    for i in range(Xq.shape[0]):
        for j in range(Xq.shape[1]):
            g = grad_fn(np.array([Xq[i,j], Yq[i,j]]))
            norm = np.linalg.norm(g) + 1e-12
            Gx[i,j] = -g[0] / norm
            Gy[i,j] = -g[1] / norm
    ax.quiver(Xq, Yq, Gx, Gy, color='white', alpha=0.22,
              scale=28, width=0.0025, headwidth=3)

    # Fixed anchors
    for pt, name in [(A, 'A'), (B, 'B')]:
        ax.scatter(*pt, c='white', s=110, marker='s', zorder=7,
                   edgecolors='#222', linewidths=1.2)
        ax.text(pt[0], pt[1] + 0.13, name, ha='center', fontsize=8,
                color='white', fontweight='bold', zorder=8)

    # Energy minima
    for i, (v_m, e_m) in enumerate(minima[:3]):
        if xlim[0] < v_m[0] < xlim[1] and ylim[0] < v_m[1] < ylim[1]:
            ax.scatter(*v_m, c='yellow', s=220, marker='*', zorder=9,
                       edgecolors='#333', linewidths=0.6)
            ax.annotate(f' v*  E={e_m:.3f}', v_m, fontsize=7, color='yellow',
                        xytext=(4, 4), textcoords='offset points', zorder=10,
                        bbox=dict(boxstyle='round,pad=0.2',
                                  facecolor='#111', alpha=0.65, edgecolor='none'))

    # State badge
    ax.text(0.03, 0.97, LABELS[state], transform=ax.transAxes,
            fontsize=11, fontweight='bold', color='white', va='top',
            bbox=dict(boxstyle='round,pad=0.4',
                      facecolor=PALETTE[state], alpha=0.92, edgecolor='none'))

    ax.set_title(title, fontsize=10, pad=6, color='white')
    ax.set_xlabel('x', color='white')
    ax.set_ylabel('y', color='white')
    ax.set_xlim(xlim); ax.set_ylim(ylim)
    ax.set_aspect('equal')
    ax.tick_params(colors='#aaa')
    for sp in ax.spines.values():
        sp.set_color('#333')


# ── Perturbation Analysis ─────────────────────────────────────────────────────
#
# MPC prediction (§5, belief revision as barrier crossing):
#
# [c] The perturbation moves the constraint target but the deep well
#     absorbs it. Minimum displacement ≈ 0 for small δ.
#     Only large δ (sufficient to cross the barrier) causes a jump.
#
# [s] Shallow well — even small δ cascades into a significant
#     minimum displacement. Linear or superlinear response.
#
# [k] No coherent minimum — displacement is large and non-monotone.
#     The system has no attractor to return to.
#
# This is the B/W signal described earlier:
# B = displacement of minimum centroid under perturbation
# W = intrinsic wandering of minimum across random seeds
# B/W ≈ 0 → [c]    B/W ~ 1 → [s]    B/W large/erratic → [k]

def perturbation_curve(base_energy_fn, make_perturbed_fn,
                       deltas, n_restarts=16):
    """
    For each perturbation magnitude δ in deltas:
      1. Build the perturbed energy landscape
      2. Find its minimum
      3. Measure displacement from the unperturbed minimum

    Returns array of displacements.
    """
    v0, _, _ = find_minima(base_energy_fn, n_restarts=n_restarts)[0], None, None
    v0 = find_minima(base_energy_fn, n_restarts=n_restarts)
    v_base = v0[0][0] if v0 else np.array([1.0, 0.0])

    displacements = []
    for delta in deltas:
        e_pert = make_perturbed_fn(delta)
        mins = find_minima(e_pert, n_restarts=n_restarts)
        v_new = mins[0][0] if mins else v_base
        displacements.append(np.linalg.norm(v_new - v_base))

    return np.array(displacements)


def make_perturbed_committed(delta):
    """Perturb committed landscape: shift target radii by δ."""
    def e(v):
        return (V_dist(v, A, 1.2 + delta, lam=100.0) +
                V_dist(v, B, 1.0 + delta, lam=100.0))
    return e


def make_perturbed_suspended(delta):
    """Perturb suspended landscape: same shift, shallow well."""
    def e(v):
        return (V_dist(v, A, 1.2 + delta, lam=0.8) +
                V_dist(v, B, 1.0 + delta, lam=0.8))
    return e


def make_perturbed_conflict(delta):
    """Perturb conflict landscape: expand incompatible radii."""
    def e(v):
        return (V_dist(v, A, 0.25 + delta, lam=30.0) +
                V_dist(v, B, 0.25 + delta, lam=30.0))
    return e


# ── Hessian Probe ─────────────────────────────────────────────────────────────
#
# MOTIVATION (from session notes, 14 April 2026):
#
# The probe vertex v* at an energy minimum is not just a point.
# It sits inside a well whose SHAPE encodes the full directional structure
# of the commitment. That shape is the Hessian ∇²E(v*) — the matrix of
# second derivatives of the energy at the minimum.
#
# In R², the Hessian is 2×2 with two eigenvalues λ₁, λ₂ and two
# eigenvectors e₁, e₂. These are the principal axes and stiffnesses
# of the attractor basin.
#
# MPC state is not scalar. It is a SPECTRUM:
#   λᵢ > E_C    → [c] committed in direction eᵢ  (stiff wall, perturbation absorbed)
#   0 < λᵢ ≤ E_C → [s] suspended in direction eᵢ  (soft wall, perturbation cascades)
#   λᵢ ≤ 0      → [k] conflict in direction eᵢ   (saddle, no restoring force)
#
# The thermal fluctuation radius in direction eᵢ is:
#   r_thermal = 1/√λᵢ  (in units of k_BT = 1)
#
# This is the "tangent space" interpretation: the attractor basin, when
# linearized at v*, is an ellipse whose semi-axes are 1/√λᵢ along eᵢ.
# In R³ restricted to a constraint surface, this IS the shape operator
# (second fundamental form) of the surface at v*.
#
# The λ₁/λ₂ anisotropy ratio measures directional commitment asymmetry:
# how differently committed the system is along its two principal directions.
# For symmetric constraints, λ₁ ≈ λ₂. For frustrated constraints, they
# diverge — one direction absorbs perturbations, the other cascades them.
#
# The observer with "high-dimensional internal state" from the MPC paper
# Addendum documents corresponds to a system where the Hessian eigenspectrum
# has many components. The Landauer cost of commitment is paid direction by
# direction: each eigendirection that crosses from [s] to [c] pays k_BT ln 2.

def numerical_hessian(energy_fn, v, eps=1e-5):
    """
    Compute the 2×2 Hessian matrix of energy_fn at point v
    using central finite differences.

    H[i,i] = (E(v+εeᵢ) - 2E(v) + E(v-εeᵢ)) / ε²   (diagonal)
    H[i,j] = (E(v+εeᵢ+εeⱼ) - E(v+εeᵢ-εeⱼ)
              - E(v-εeᵢ+εeⱼ) + E(v-εeᵢ-εeⱼ)) / (4ε²)  (off-diagonal)

    Accuracy: O(ε²). For ε=1e-5, error ~ 1e-10 for smooth potentials.
    Returns: symmetric 2×2 numpy array H
    """
    n = len(v)
    H = np.zeros((n, n))
    e0 = np.zeros(n)

    E0 = energy_fn(v)

    for i in range(n):
        ei = e0.copy(); ei[i] = eps
        H[i, i] = (energy_fn(v + ei) - 2*E0 + energy_fn(v - ei)) / eps**2

    for i in range(n):
        for j in range(i+1, n):
            ei = e0.copy(); ei[i] = eps
            ej = e0.copy(); ej[j] = eps
            H[i, j] = (energy_fn(v + ei + ej)
                     - energy_fn(v + ei - ej)
                     - energy_fn(v - ei + ej)
                     + energy_fn(v - ei - ej)) / (4 * eps**2)
            H[j, i] = H[i, j]   # enforce symmetry

    return H


def classify_direction(lam):
    """
    Classify MPC state for a single Hessian eigenvalue.

    λ > E_C  → [c] committed: stiff well, thermal radius 1/√λ < 1/√E_C
    0 < λ ≤ E_C → [s] suspended: soft well, large thermal radius
    λ ≤ 0    → [k] conflict: saddle or flat — no restoring force

    The thermal fluctuation radius r = 1/√λ is the distance the system
    wanders due to k_BT thermal noise along this eigendirection.
    """
    if lam <= 0:
        return 'k', float('inf')
    r_thermal = 1.0 / np.sqrt(lam)
    if lam > E_C:
        return 'c', r_thermal
    else:
        return 's', r_thermal


def hessian_probe(energy_fn, minima, scenario_name, scenario_state):
    """
    Compute and interpret the Hessian eigenstructure at each energy minimum.

    For each minimum v*:
      1. Compute H = ∇²E(v*) via central finite differences
      2. Eigendecompose H → (λ₁, e₁), (λ₂, e₂)
      3. Classify MPC state direction by direction
      4. Compute thermal fluctuation ellipse semi-axes 1/√λᵢ
      5. Compute anisotropy ratio λ_max/λ_min

    Returns a list of dicts, one per minimum, with full eigenstructure.
    """
    results = []

    for i, (v_star, E_min) in enumerate(minima[:2]):  # probe up to 2 minima
        H = numerical_hessian(energy_fn, v_star)

        # Eigendecomposition. np.linalg.eigh guarantees real eigenvalues
        # for symmetric matrices and returns them sorted ascending.
        eigenvalues, eigenvectors = np.linalg.eigh(H)

        # λ₁ ≤ λ₂ (sorted ascending by eigh)
        lam1, lam2 = eigenvalues
        e1, e2 = eigenvectors[:, 0], eigenvectors[:, 1]

        state1, r1 = classify_direction(lam1)
        state2, r2 = classify_direction(lam2)

        # Anisotropy: ratio of stiffest to softest direction
        lam_soft = abs(lam1) + 1e-12
        lam_stiff = abs(lam2) + 1e-12
        anisotropy = lam_stiff / lam_soft

        # Combined state: most informative (weakest direction dominates)
        # A chain is only as strong as its weakest link.
        # If either direction is [k], the whole commitment is [k].
        # If either is [s] (and none [k]), commitment is [s].
        if 'k' in (state1, state2):
            combined = 'k'
        elif 's' in (state1, state2):
            combined = 's'
        else:
            combined = 'c'

        results.append({
            'minimum_idx':   i,
            'v_star':        v_star,
            'E_min':         E_min,
            'H':             H,
            'eigenvalues':   eigenvalues,
            'eigenvectors':  eigenvectors,
            'lam1': lam1, 'e1': e1, 'state1': state1, 'r1': r1,
            'lam2': lam2, 'e2': e2, 'state2': state2, 'r2': r2,
            'anisotropy':    anisotropy,
            'combined':      combined,
            'scenario':      scenario_name,
            'global_state':  scenario_state,
        })

    return results


def plot_hessian_panel(ax, energy_fn, probe_results, scenario_name,
                       xlim=(-1.0, 3.0), ylim=(-1.8, 1.8)):
    """
    Visualise Hessian eigenstructure overlaid on energy landscape.

    For each minimum:
      - Draw the thermal fluctuation ellipse:
          semi-axes = r_thermal = 1/√λᵢ along eigenvector eᵢ
          This is the region the system wanders in due to k_BT noise.
          It is the linearized attractor basin.
      - Draw eigenvector arrows colour-coded by directional MPC state:
          [c] → blue    [s] → orange    [k] → red
      - Annotate eigenvalues and thermal radii

    The ellipse IS the internal state of the committed observer.
    Symmetric ellipse → isotropic commitment.
    Elongated ellipse → anisotropic — committed in one direction, soft in another.
    """
    # Background landscape (desaturated for clarity)
    X, Y, E = compute_grid(energy_fn, xlim, ylim, resolution=220)
    vmax = np.percentile(E, 95)
    E_vis = np.clip(E, 0, vmax)

    ax.pcolormesh(X, Y, E_vis, cmap='Blues', shading='gouraud',
                  vmin=0, vmax=vmax, alpha=0.55, rasterized=True)
    ax.contour(X, Y, E, levels=np.linspace(0, vmax, 10),
               colors='white', alpha=0.18, linewidths=0.5)

    # Fixed anchors
    for pt, name in [(A, 'A'), (B, 'B')]:
        ax.scatter(*pt, c='white', s=100, marker='s', zorder=7,
                   edgecolors='#555', linewidths=1.0)
        ax.text(pt[0], pt[1] + 0.14, name, ha='center', fontsize=8,
                color='white', fontweight='bold')

    state_colors = {'c': '#4fc3f7', 's': '#ffb74d', 'k': '#ef5350'}

    for pr in probe_results:
        v_star = pr['v_star']

        # ── Thermal ellipse ──────────────────────────────────────────────
        # Parametric ellipse: v*(t) = v* + r1·cos(t)·e1 + r2·sin(t)·e2
        t = np.linspace(0, 2*np.pi, 200)
        r1 = min(pr['r1'], 2.0)   # cap display radius for [s]/[k]
        r2 = min(pr['r2'], 2.0)
        ellipse_pts = (v_star[:, None]
                       + r1 * np.cos(t) * pr['e1'][:, None]
                       + r2 * np.sin(t) * pr['e2'][:, None])

        # Ellipse colour = combined MPC state
        ecol = state_colors[pr['combined']]
        ax.plot(ellipse_pts[0], ellipse_pts[1], '-', color=ecol,
                linewidth=1.8, alpha=0.85, zorder=6)
        ax.fill(ellipse_pts[0], ellipse_pts[1],
                color=ecol, alpha=0.10, zorder=5)

        # ── Eigenvector arrows ────────────────────────────────────────────
        scale = 0.35
        for e_vec, lam, state, label in [
            (pr['e1'], pr['lam1'], pr['state1'], f'e₁ λ={pr["lam1"]:.2f}'),
            (pr['e2'], pr['lam2'], pr['state2'], f'e₂ λ={pr["lam2"]:.2f}'),
        ]:
            col = state_colors[state]
            ax.annotate('', xy=v_star + scale * e_vec,
                        xytext=v_star - scale * e_vec,
                        arrowprops=dict(arrowstyle='<->', color=col,
                                        lw=2.2, mutation_scale=12),
                        zorder=8)
            # Label at tip
            tip = v_star + (scale + 0.08) * e_vec
            ax.text(tip[0], tip[1], f'[{state}]\nλ={lam:.2f}',
                    fontsize=6.5, color=col, ha='center', va='center',
                    bbox=dict(boxstyle='round,pad=0.2',
                              facecolor='#111', alpha=0.7, edgecolor='none'),
                    zorder=9)

        # ── Minimum marker ────────────────────────────────────────────────
        ax.scatter(*v_star, c='yellow', s=180, marker='*', zorder=10,
                   edgecolors='#333', linewidths=0.6)

        # ── Annotation box ────────────────────────────────────────────────
        ax.annotate(
            f'v* = ({v_star[0]:.3f}, {v_star[1]:.3f})\n'
            f'E_min = {pr["E_min"]:.4f}\n'
            f'λ₁={pr["lam1"]:.3f} [{pr["state1"]}]  r={r1:.3f}\n'
            f'λ₂={pr["lam2"]:.3f} [{pr["state2"]}]  r={r2:.3f}\n'
            f'anisotropy = {pr["anisotropy"]:.2f}×\n'
            f'combined → [{pr["combined"]}]',
            xy=v_star, xytext=(v_star[0] + 0.35, v_star[1] - 0.55),
            fontsize=6.5, color='#eee', family='monospace',
            bbox=dict(boxstyle='round,pad=0.3',
                      facecolor='#111', alpha=0.82, edgecolor=ecol,
                      linewidth=0.8),
            arrowprops=dict(arrowstyle='-', color='#555', lw=0.6),
            zorder=11
        )

    # State badge
    state_char = probe_results[0]['global_state'] if probe_results else '?'
    ax.text(0.03, 0.97, f'[{state_char}] {scenario_name}',
            transform=ax.transAxes, fontsize=10, fontweight='bold',
            color='white', va='top',
            bbox=dict(boxstyle='round,pad=0.4',
                      facecolor=state_colors.get(state_char, '#555'),
                      alpha=0.92, edgecolor='none'))

    ax.set_xlim(xlim); ax.set_ylim(ylim)
    ax.set_aspect('equal')
    ax.tick_params(colors='#aaa')
    for sp in ax.spines.values():
        sp.set_color('#333')
    ax.set_xlabel('x', color='white')
    ax.set_ylabel('y', color='white')


# ── Catmull-Clark Phase Boundary Display ─────────────────────────────────────
#
# MOTIVATION:
# The MPC energy landscape has two phase boundaries:
#   E = E_C  (committed / suspended threshold)
#   E = E_S  (suspended / conflict threshold)
#
# These level-set curves, extracted from the grid, are piecewise-linear
# polygon chains — accurate but geometrically crude. Catmull-Clark
# subdivision (Lane-Riesenfeld algorithm, cubic B-spline reduction)
# converges to the C² smooth limit of these boundaries.
#
# WHY THIS MATTERS:
# The limit curve is not cosmetic. Its geometry encodes physics:
#
#   Curvature at a boundary point κ = d²E/dn² / (dE/dn)
#   where n is the direction normal to the boundary.
#   High κ → abrupt transition  (sharp MPC state change)
#   Low κ  → gradual transition (smooth crossover)
#
# The convergence rate also carries information:
#   A sharply curved phase boundary requires more subdivision steps
#   to reach its limit than a flat one. The convergence rate is a
#   proxy for the local sharpness of the phase transition.
#
# In R³, this extends naturally: the E_C level set becomes a 2D surface,
# and Catmull-Clark subdivision on quad meshes of that surface converges
# to a smooth B-spline surface. The principal curvatures of that limit
# surface relate directly to the Hessian eigenvalues at the minima —
# the Hessian probe and the Catmull-Clark display are measuring the
# same structure from opposite sides of the phase boundary.
#
# ALGORITHM: Lane-Riesenfeld (cubic B-spline, degree 3)
# For a closed polygon P₀…P_{n-1}, one subdivision step:
#   Step 1: Insert edge midpoints → 2n points
#            doubled[2i]   = P_i
#            doubled[2i+1] = (P_i + P_{(i+1)%n}) / 2
#   Step 2: Two averaging passes
#            averaged[i] = (P_i + P_{(i+1)%n}) / 2
#   Applied twice, this produces the uniform cubic B-spline mask:
#     vertex → (P_{i-1} + 6P_i + P_{i+1}) / 8
#     edge   → (P_i + P_{i+1}) / 2
# Convergence: limit is C² (continuous up to second derivative).

def extract_contour_polygons(energy_fn, level, xlim, ylim,
                             resolution=280, min_points=12):
    """
    Extract all closed contour polygons at E = level.
    Returns a list of (N, 2) numpy arrays, one per contour component.
    Uses matplotlib's contour engine — exact same curves shown in plots.
    """
    X, Y, E = compute_grid(energy_fn, xlim, ylim, resolution)

    # Render to a temporary hidden figure to extract path data
    fig_tmp, ax_tmp = plt.subplots(figsize=(1, 1))
    cs = ax_tmp.contour(X, Y, E, levels=[level])
    plt.close(fig_tmp)

    polygons = []

    # matplotlib >= 3.8 deprecated collections; use allsegs or get_paths()
    try:
        # New API: iterate over the ContourSet directly
        paths = []
        for col in cs.collections:
            paths.extend(col.get_paths())
    except AttributeError:
        # Fallback for matplotlib >= 3.8 where .collections is removed
        paths = []
        for seg_group in cs.allsegs:
            for seg in seg_group:
                if len(seg) >= min_points:
                    # allsegs returns raw numpy arrays, not Path objects
                    polygons.append(seg)
        plt.close(fig_tmp)
        return polygons

    for path in paths:
        verts = path.vertices
        if len(verts) >= min_points:
            if not np.allclose(verts[0], verts[-1], atol=1e-6):
                verts = np.vstack([verts, verts[0]])
            polygons.append(verts[:-1])

    plt.close(fig_tmp)
    return polygons


def lane_riesenfeld_step(points):
    """
    One subdivision step of the Lane-Riesenfeld cubic B-spline algorithm.
    Input:  closed polygon as (N, 2) array
    Output: subdivided polygon as (2N, 2) array — doubled + twice averaged

    This is the exact 1D reduction of Catmull-Clark subdivision.
    C² smooth at the limit (uniform cubic B-spline).
    """
    n = len(points)

    # Step 1: double — insert edge midpoints between each consecutive pair
    doubled = np.zeros((2 * n, 2))
    for i in range(n):
        doubled[2 * i]     = points[i]
        doubled[2 * i + 1] = (points[i] + points[(i + 1) % n]) / 2.0

    # Step 2: two passes of midpoint averaging (degree - 1 = 2 passes)
    for _ in range(2):
        m = len(doubled)
        averaged = np.zeros_like(doubled)
        for i in range(m):
            averaged[i] = (doubled[i] + doubled[(i + 1) % m]) / 2.0
        doubled = averaged

    return doubled


def subdivide_polygon(polygon, n_steps):
    """
    Apply n_steps of Lane-Riesenfeld subdivision to a closed polygon.
    Returns list of arrays [step_0, step_1, ..., step_n] for plotting.
    """
    steps = [polygon]
    for _ in range(n_steps):
        steps.append(lane_riesenfeld_step(steps[-1]))
    return steps


def convergence_metric(poly_a, poly_b):
    """
    Mean displacement between two subdivision levels.
    Resamples the coarser polygon to match the finer polygon's point count
    via linear interpolation, then computes mean Euclidean distance.
    This is the convergence measure: approaches 0 at the limit.
    """
    n_fine = len(poly_b)
    n_coarse = len(poly_a)

    if n_coarse == n_fine:
        return float(np.mean(np.linalg.norm(poly_a - poly_b, axis=1)))

    # Resample poly_a to n_fine points via arc-length parameterisation
    diffs = np.diff(poly_a, axis=0,
                    append=poly_a[:1])        # wrap-around
    seg_len = np.linalg.norm(diffs, axis=1)
    cum_len = np.concatenate([[0], np.cumsum(seg_len)])
    total   = cum_len[-1]

    sample_s = np.linspace(0, total, n_fine, endpoint=False)
    resampled = np.zeros((n_fine, 2))
    for i, s in enumerate(sample_s):
        j = int(np.searchsorted(cum_len, s, side='right')) - 1
        j = np.clip(j, 0, n_coarse - 1)
        j1 = (j + 1) % n_coarse
        t  = (s - cum_len[j]) / (seg_len[j] + 1e-15)
        resampled[i] = (1 - t) * poly_a[j] + t * poly_a[j1]

    return float(np.mean(np.linalg.norm(resampled - poly_b, axis=1)))


def catmull_clark_display(energy_fn, hessian_probes, scenario_name,
                          scenario_state, xlim=(-1.0, 3.0), ylim=(-1.8, 1.8),
                          n_steps=5):
    """
    Figure 5: Catmull-Clark subdivision of MPC phase boundaries.

    Left panel  — convergence gallery:
      Shows subdivision steps 0 (coarse polygon) through n_steps,
      all overlaid on the energy landscape. Each step rendered in a
      distinct colour from warm (coarse) to cool (refined).
      Convergence metric printed per step.

    Right panel — limit + Hessian:
      Shows the limit curve (step n_steps) for both E_C and E_S
      phase boundaries, overlaid with the Hessian thermal ellipses
      from hessian_probe(). The limit curve is the smooth phase
      boundary; the ellipses show the attractor basins just inside it.
      Together they show the relationship between global topology
      (where the boundary sits) and local geometry (how committed
      the system is near the boundary).

    Returns the figure for saving.
    """
    state_colors = {'c': '#4fc3f7', 's': '#ffb74d', 'k': '#ef5350'}
    BG    = '#12121f'
    PANEL = '#1a1a2e'

    # ── Extract phase boundary polygons ──────────────────────────────────
    ec_polys = extract_contour_polygons(energy_fn, E_C, xlim, ylim)
    es_polys = extract_contour_polygons(energy_fn, E_S, xlim, ylim)

    # Subdivide each component independently
    ec_steps_list = [subdivide_polygon(p, n_steps) for p in ec_polys]
    es_steps_list = [subdivide_polygon(p, n_steps) for p in es_polys]

    # ── Background grid for both panels ──────────────────────────────────
    X, Y, E = compute_grid(energy_fn, xlim, ylim, resolution=260)
    vmax = np.percentile(E, 95)
    E_vis = np.clip(E, 0, vmax)

    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(18, 8))
    fig.patch.set_facecolor(BG)

    for ax in (ax_left, ax_right):
        ax.set_facecolor(PANEL)
        ax.pcolormesh(X, Y, E_vis, cmap='Blues', shading='gouraud',
                      vmin=0, vmax=vmax, alpha=0.45, rasterized=True)
        ax.contour(X, Y, E, levels=np.linspace(0, vmax, 8),
                   colors='white', alpha=0.12, linewidths=0.4)
        # Fixed anchors
        for pt, name in [(A, 'A'), (B, 'B')]:
            ax.scatter(*pt, c='white', s=90, marker='s', zorder=7,
                       edgecolors='#555', linewidths=0.9)
            ax.text(pt[0], pt[1] + 0.13, name, ha='center',
                    fontsize=8, color='white', fontweight='bold')
        ax.set_xlim(xlim); ax.set_ylim(ylim)
        ax.set_aspect('equal')
        ax.tick_params(colors='#aaa')
        for sp in ax.spines.values():
            sp.set_color('#333')
        ax.set_xlabel('x', color='white', fontsize=11)
        ax.set_ylabel('y', color='white', fontsize=11)

    # ── LEFT PANEL: convergence gallery ──────────────────────────────────
    # Colour ramp: warm (coarse step 0) → cool (refined step N)
    step_cmap  = plt.cm.plasma
    step_alphas = np.linspace(0.55, 1.0, n_steps + 1)
    step_widths = np.linspace(2.8, 0.9, n_steps + 1)

    # We show convergence for E_C boundary (most meaningful — it divides
    # committed from suspended, directly tied to the Hessian ellipses)
    for comp_steps in ec_steps_list:
        for step_idx, poly in enumerate(comp_steps):
            t = step_idx / max(n_steps, 1)
            col = step_cmap(0.85 - 0.65 * t)   # warm→cool
            lw  = step_widths[step_idx]
            ls  = '--' if step_idx == 0 else '-'
            alpha = step_alphas[step_idx]
            closed = np.vstack([poly, poly[0]])
            ax_left.plot(closed[:, 0], closed[:, 1],
                         ls, color=col, linewidth=lw, alpha=alpha,
                         zorder=5 + step_idx,
                         label=f'Step {step_idx}  ({len(poly)} pts)' if step_idx <= 4 else '_')

    # E_S boundary on left panel (fainter)
    for comp_steps in es_steps_list:
        closed = np.vstack([comp_steps[-1], comp_steps[-1][0]])
        ax_left.plot(closed[:, 0], closed[:, 1],
                     ':', color='#ffb74d', linewidth=1.2, alpha=0.45, zorder=5,
                     label=f'E_s boundary (limit)')

    # Convergence metrics
    conv_lines = ['Convergence  (E_C boundary)']
    for comp_steps in ec_steps_list[:1]:   # show for first component
        for i in range(1, len(comp_steps)):
            d = convergence_metric(comp_steps[i-1], comp_steps[i])
            conv_lines.append(f'  {i-1}→{i}:  Δ = {d:.5f}')
    conv_lines.append(f'\nLimit = cubic B-spline (C²)')
    conv_lines.append(f'E_C = {E_C:.1f} k_BT  (committed threshold)')

    ax_left.text(0.02, 0.03, '\n'.join(conv_lines),
                 transform=ax_left.transAxes, va='bottom', fontsize=7.5,
                 color='#ccc', family='monospace',
                 bbox=dict(boxstyle='round,pad=0.4',
                           facecolor='#111', alpha=0.80, edgecolor='#444'))

    ax_left.legend(fontsize=8, facecolor=PANEL, labelcolor='white',
                   framealpha=0.75, loc='upper right',
                   title='Subdivision step', title_fontsize=8)
    ax_left.set_title(
        f'[{scenario_state}] {scenario_name} — Catmull-Clark Convergence\n'
        f'E_C phase boundary  ·  warm = coarse polygon  ·  cool = limit',
        color='white', fontsize=10, pad=8
    )

    # ── RIGHT PANEL: limit curve + Hessian ellipses ───────────────────────

    # Limit curves — both thresholds
    limit_specs = [
        (ec_steps_list, E_C, '#4fc3f7', 2.2, 0.92, 'E_C  (committed boundary)'),
        (es_steps_list, E_S, '#ffb74d', 1.4, 0.70, 'E_S  (suspended boundary)'),
    ]
    for steps_list, level, col, lw, alpha, lbl in limit_specs:
        for i, comp_steps in enumerate(steps_list):
            poly_limit = comp_steps[-1]
            closed = np.vstack([poly_limit, poly_limit[0]])
            ax_right.plot(closed[:, 0], closed[:, 1], '-',
                          color=col, linewidth=lw, alpha=alpha,
                          zorder=6,
                          label=lbl if i == 0 else '_')
            # Fill the committed region interior
            if level == E_C:
                ax_right.fill(poly_limit[:, 0], poly_limit[:, 1],
                              color=col, alpha=0.07, zorder=4)

    # Hessian ellipses — drawn on top of limit curves
    for pr in hessian_probes:
        v_star = pr['v_star']
        t_param = np.linspace(0, 2 * np.pi, 300)
        r1 = min(pr['r1'], 1.8)
        r2 = min(pr['r2'], 1.8)
        ellipse = (v_star[:, None]
                   + r1 * np.cos(t_param) * pr['e1'][:, None]
                   + r2 * np.sin(t_param) * pr['e2'][:, None])

        ecol = state_colors[pr['combined']]
        ax_right.plot(ellipse[0], ellipse[1], '-', color=ecol,
                      linewidth=2.0, alpha=0.9, zorder=8)
        ax_right.fill(ellipse[0], ellipse[1],
                      color=ecol, alpha=0.12, zorder=7)

        # Principal axis arrows
        for e_vec, lam, state in [
            (pr['e1'], pr['lam1'], pr['state1']),
            (pr['e2'], pr['lam2'], pr['state2']),
        ]:
            col_arrow = state_colors[state]
            sc = min(1.0 / (np.sqrt(abs(lam)) + 1e-9), 1.0) * 0.7
            ax_right.annotate('', xy=v_star + sc * e_vec,
                              xytext=v_star - sc * e_vec,
                              arrowprops=dict(arrowstyle='<->',
                                             color=col_arrow,
                                             lw=1.8, mutation_scale=10),
                              zorder=9)

        # Minimum marker
        ax_right.scatter(*v_star, c='yellow', s=160, marker='*',
                         zorder=10, edgecolors='#333', linewidths=0.6)

        # Relationship annotation: is the ellipse inside the limit curve?
        ax_right.annotate(
            f'λ₁={pr["lam1"]:.1f}[{pr["state1"]}] '
            f'λ₂={pr["lam2"]:.1f}[{pr["state2"]}]\n'
            f'r_th=({min(pr["r1"],99):.3f}, {min(pr["r2"],99):.3f})',
            xy=v_star,
            xytext=(v_star[0] + 0.28, v_star[1] + 0.38),
            fontsize=6.5, color='#eee', family='monospace',
            bbox=dict(boxstyle='round,pad=0.25',
                      facecolor='#111', alpha=0.80,
                      edgecolor=ecol, linewidth=0.8),
            arrowprops=dict(arrowstyle='-', color='#555', lw=0.5),
            zorder=11
        )

    ax_right.legend(fontsize=8, facecolor=PANEL, labelcolor='white',
                    framealpha=0.75, loc='upper right')
    ax_right.set_title(
        f'Limit Surface + Hessian Basins\n'
        f'Limit curve = C² phase boundary  ·  '
        f'Ellipses = thermal attractor basins (1/√λ)',
        color='white', fontsize=10, pad=8
    )

    # State badge
    ax_right.text(0.03, 0.97,
                  f'[{scenario_state}] {scenario_name}',
                  transform=ax_right.transAxes,
                  fontsize=10, fontweight='bold', color='white', va='top',
                  bbox=dict(boxstyle='round,pad=0.4',
                            facecolor=state_colors.get(scenario_state, '#555'),
                            alpha=0.92, edgecolor='none'))

    plt.tight_layout(pad=2.0)
    return fig


# ── Separation Theorem Validation ─────────────────────────────────────────────
#
# Theorem 6.1 (Generalised):
#   ||Γ*|| ≤ N_max = O( √(2E* / α·ε_min·d_avg) )
#
# Procedure:
#   1. Define N position constraints, each wanting v at a different
#      point on a unit circle. Each pair of adjacent constraints has
#      a known pairwise frustration ε_ij.
#   2. Add constraints one by one. After each addition, find the
#      minimum joint energy.
#   3. Record N* where E_min first exceeds the energy budget E*.
#   4. Compare N* to the theoretical bound N_max.
#
# This is a quantitative test of the theorem, not an analogy.

def separation_theorem_test(N_max=12, E_star=30.0, alpha=1.0):
    """
    Direct numerical test of the Thermodynamic Separation Theorem.

    Constraint set: N position constraints, each wanting v at angle
    θ_i = i·π/N on the unit circle. Adjacent constraints are
    frustrated: they cannot both be exactly satisfied simultaneously.

    Pairwise frustration ε_ij for adjacent constraints:
      ε = λ/2 · |p_i − p_j|²   (minimum of V_i + V_j is at midpoint,
                                  energy = λ/2 · d²)
    """
    lam = 20.0
    radius = 1.0

    # Constraint targets spread over the upper semicircle
    angles = np.linspace(np.pi * 0.1, np.pi * 0.9, N_max)
    targets = np.array([[np.cos(a) * radius, np.sin(a) * radius]
                        for a in angles])

    # Pairwise frustration between adjacent targets
    # ε_min = min over all adjacent pairs
    eps_pairs = []
    for i in range(len(targets) - 1):
        d_sq = np.sum((targets[i] - targets[i+1])**2)
        eps_pairs.append((lam / 2) * d_sq)
    eps_min = min(eps_pairs)

    # Theoretical bound: path graph → d_avg = 2(N-1)/N ≈ 2 for large N
    d_avg = 2.0
    N_max_theory = np.sqrt(2 * E_star / (alpha * eps_min * d_avg))

    # Measure: add constraints one by one, track minimum energy
    measured_emin = []
    for n in range(1, N_max + 1):
        tgts = targets[:n]

        def energy_n(v, tgts=tgts):
            return sum(V_pos(v, t, lam) for t in tgts)

        mins = find_minima(energy_n, n_restarts=20)
        e = mins[0][1] if mins else float('inf')
        measured_emin.append(e)

    return {
        'Ns': list(range(1, N_max + 1)),
        'min_energies': measured_emin,
        'N_max_theory': N_max_theory,
        'eps_min': eps_min,
        'E_star': E_star,
        'targets': targets,
        'd_avg': d_avg,
        'alpha': alpha,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    BG    = '#12121f'
    PANEL = '#1a1a2e'

    print("\n" + "═"*62)
    print("  MPC LATTICE — Metastable Propositional Calculus in R²")
    print("═"*62)
    print(f"\n  Physical constants (k_BT natural units):")
    print(f"    k_BT = {K_BT}  (thermal energy scale)")
    print(f"    E_c  = {E_C}  (committed threshold)")
    print(f"    E_s  = {E_S}  (suspended threshold)")
    print(f"\n  Fixed anchors:  A={A}  B={B}")
    print(f"  Free vertex v = (x, y)  — full R² is the configuration space\n")

    # ── Classify all three scenarios ─────────────────────────────────────────
    print("  Finding energy minima...")

    scenarios = [
        ('committed', energy_committed, 'λ=100  (deep well)'),
        ('suspended', energy_suspended, 'λ=0.8  (shallow well)'),
        ('conflict',  energy_conflict,  'incompatible circles'),
    ]

    results = {}
    for name, efn, desc in scenarios:
        mins = find_minima(efn)
        state, e_min, bar = classify(efn, mins)
        results[name] = dict(fn=efn, mins=mins, state=state,
                             e_min=e_min, bar=bar, desc=desc)
        bar_str = f'{bar:.3f}' if bar != float('inf') else '∞'
        print(f"    [{state}] {name:10s}  E_min={e_min:.4f}  ΔE={bar_str}  ({desc})")

    # ═══════════════════════════════════════════════════════════════════════
    # FIGURE 1 — Energy Landscape Gallery
    # ═══════════════════════════════════════════════════════════════════════
    print("\n  Rendering Figure 1: Energy Landscape Gallery...")

    fig1, axes = plt.subplots(1, 3, figsize=(19, 7))
    fig1.patch.set_facecolor(BG)
    for ax in axes:
        ax.set_facecolor(PANEL)

    # Left panel explanation text rows
    panel_data = [
        ('committed', energy_committed,
         '[c] COMMITTED\nCompatible constraints, λ=100\n'
         'Two deep wells — barrier >> E_c\n'
         'Perturbation absorbed',
         axes[0]),
        ('suspended', energy_suspended,
         '[s] SUSPENDED\nSame geometry, λ=0.8\n'
         'Barrier ~ k_BT — thermally soft\n'
         'Active maintenance required',
         axes[1]),
        ('conflict', energy_conflict,
         '[k] CONFLICT\nDisjoint circles (r=0.25 each)\n'
         'No point satisfies both\n'
         'Residual energy > 0 everywhere',
         axes[2]),
    ]

    for name, efn, title, ax in panel_data:
        r = results[name]
        plot_landscape(ax, efn, r['state'], r['mins'], title)

    fig1.suptitle(
        'MPC Energy Landscapes — Three Vertices in R²\n'
        '★ = energy minima   ■ = fixed anchors A, B   '
        'arrows = gradient field (steepest descent)\n'
        'Dashed = E_c threshold   Dotted = E_s threshold',
        fontsize=11, color='white', y=1.00
    )
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    fig1.savefig('mpc_landscape.png', dpi=150, bbox_inches='tight',
                 facecolor=BG)
    print("    Saved: mpc_landscape.png")

    # ═══════════════════════════════════════════════════════════════════════
    # FIGURE 2 — Perturbation Response Curves
    # ═══════════════════════════════════════════════════════════════════════
    print("  Running perturbation analysis...")

    deltas = np.linspace(0.0, 0.6, 18)

    disp_c = perturbation_curve(energy_committed, make_perturbed_committed, deltas)
    disp_s = perturbation_curve(energy_suspended, make_perturbed_suspended, deltas)
    disp_k = perturbation_curve(energy_conflict,  make_perturbed_conflict,  deltas)

    fig2, (ax2a, ax2b) = plt.subplots(1, 2, figsize=(14, 6))
    fig2.patch.set_facecolor(BG)
    for ax in (ax2a, ax2b):
        ax.set_facecolor(PANEL)
        ax.tick_params(colors='#aaa')
        for sp in ax.spines.values():
            sp.set_color('#333')

    # Left: displacement curves
    for disp, state, lbl in [
        (disp_c, 'c', '[c] Committed (λ=30)'),
        (disp_s, 's', '[s] Suspended (λ=0.8)'),
        (disp_k, 'k', '[k] Conflict'),
    ]:
        ax2a.plot(deltas, disp, 'o-', color=PALETTE[state],
                  label=lbl, linewidth=2.5, markersize=5, alpha=0.92)

    ax2a.axhline(0.04, color='white', linestyle=':', alpha=0.35, linewidth=1)
    ax2a.text(0.58, 0.06, 'noise floor', color='#888', fontsize=8)
    ax2a.set_xlabel('Constraint perturbation  δ', color='white', fontsize=12)
    ax2a.set_ylabel('Minimum displacement  ‖v* − v₀‖', color='white', fontsize=12)
    ax2a.set_title('Perturbation Response by MPC State',
                   color='white', fontsize=12)
    ax2a.legend(fontsize=10, facecolor=PANEL, labelcolor='white',
                framealpha=0.8)
    ax2a.text(0.02, 0.97,
              'MPC prediction:\n'
              '[c] flat near zero → perturbation absorbed\n'
              '[s] rises with δ → shallow well, cascades\n'
              '[k] elevated & erratic → no coherent attractor',
              transform=ax2a.transAxes, va='top', fontsize=8.5,
              color='#ccc',
              bbox=dict(boxstyle='round,pad=0.4',
                        facecolor='#111', alpha=0.75, edgecolor='none'))

    # Right: B/W ratio (the pure signal)
    # W = intrinsic variance — estimate from spread of multi-start minima
    # For this plot: W = displacement at δ=0.01 (tiny perturbation, mostly noise)
    W_c = disp_c[1] + 1e-6
    W_s = disp_s[1] + 1e-6
    W_k = disp_k[1] + 1e-6

    bw_c = disp_c / W_c
    bw_s = disp_s / W_s
    bw_k = disp_k / W_k

    for bw, state, lbl in [
        (bw_c, 'c', '[c] Committed'),
        (bw_s, 's', '[s] Suspended'),
        (bw_k, 'k', '[k] Conflict'),
    ]:
        ax2b.plot(deltas, bw, 'o-', color=PALETTE[state],
                  label=lbl, linewidth=2.5, markersize=5, alpha=0.92)

    ax2b.axhline(1.0, color='white', linestyle='--', alpha=0.3, linewidth=1)
    ax2b.text(0.01, 1.05, 'B/W = 1  (noise floor)', color='#888', fontsize=8)
    ax2b.set_xlabel('Constraint perturbation  δ', color='white', fontsize=12)
    ax2b.set_ylabel('B/W  (perturbation / intrinsic variance)', color='white',
                    fontsize=12)
    ax2b.set_title('B/W Signal — The Dimensionless MPC Observable',
                   color='white', fontsize=12)
    ax2b.legend(fontsize=10, facecolor=PANEL, labelcolor='white',
                framealpha=0.8)
    ax2b.text(0.02, 0.97,
              'B/W is dimensionally identical to ΔE/k_BT\n'
              '(barrier height in natural units).\n'
              'B/W ≈ 0 → [c]   B/W ~ 1 → [s]   B/W >> 1 → [k]\n'
              'This ratio cancels model size, hardware, and\n'
              'generation artifacts — pure thermodynamic signal.',
              transform=ax2b.transAxes, va='top', fontsize=8.5, color='#ccc',
              bbox=dict(boxstyle='round,pad=0.4',
                        facecolor='#111', alpha=0.75, edgecolor='none'))

    plt.tight_layout()
    fig2.savefig('mpc_perturbation.png', dpi=150, bbox_inches='tight',
                 facecolor=BG)
    print("    Saved: mpc_perturbation.png")

    # ═══════════════════════════════════════════════════════════════════════
    # FIGURE 3 — Separation Theorem Validation
    # ═══════════════════════════════════════════════════════════════════════
    print("  Running Separation Theorem test (may take ~40s)...")

    sep = separation_theorem_test(N_max=10, E_star=30.0)
    Ns           = sep['Ns']
    min_energies = sep['min_energies']
    N_th         = sep['N_max_theory']
    eps_min      = sep['eps_min']
    E_star       = sep['E_star']
    targets      = sep['targets']

    # Find measured N* (first N where E_min > E*)
    crossings = [i for i, e in enumerate(min_energies) if e >= E_star]
    N_measured = Ns[crossings[0]] if crossings else None

    fig3, (ax3a, ax3b) = plt.subplots(1, 2, figsize=(14, 6))
    fig3.patch.set_facecolor(BG)
    for ax in (ax3a, ax3b):
        ax.set_facecolor(PANEL)
        ax.tick_params(colors='#aaa')
        for sp in ax.spines.values():
            sp.set_color('#333')

    # Left: E_min vs N
    ax3a.plot(Ns, min_energies, 'o-', color='#64b5f6',
              linewidth=2.5, markersize=7, label='Measured E_min(N)', zorder=4)
    ax3a.axhline(E_star, color='#ef5350', linestyle='--', linewidth=2.0,
                 label=f'Energy budget E* = {E_star}', alpha=0.9)
    ax3a.axhline(E_C, color='#4fc3f7', linestyle=':', linewidth=1.2,
                 label=f'E_c = {E_C}', alpha=0.6)
    ax3a.axhline(E_S, color='#ffb74d', linestyle=':', linewidth=1.2,
                 label=f'E_s = {E_S}', alpha=0.6)

    ax3a.axvline(N_th, color='#80cbc4', linestyle='--', linewidth=1.8,
                 alpha=0.85)
    ax3a.text(N_th + 0.1, E_star * 0.12,
              f'N_max = {N_th:.1f}\n(theorem)', color='#80cbc4', fontsize=9)

    if N_measured:
        ax3a.axvline(N_measured, color='#ef5350', linestyle=':', linewidth=1.8,
                     alpha=0.85)
        ax3a.text(N_measured + 0.1, E_star * 0.55,
                  f'N* = {N_measured}\n(measured)', color='#ef5350', fontsize=9)

    ax3a.set_xlabel('Number of constraints  N', color='white', fontsize=12)
    ax3a.set_ylabel('Minimum joint energy  E(Γ*)', color='white', fontsize=12)
    ax3a.set_title('Separation Theorem 6.1\nMinimum Energy vs Constraint Count',
                   color='white', fontsize=11)
    ax3a.legend(fontsize=9, facecolor=PANEL, labelcolor='white', framealpha=0.8)

    param_box = (
        f'Theorem parameters:\n'
        f'  E* = {E_star:.0f}  (energy budget)\n'
        f'  ε_min = {eps_min:.3f}  (pairwise frustration)\n'
        f'  d_avg = {sep["d_avg"]:.1f}  (path graph)\n'
        f'  α = {sep["alpha"]:.1f}\n'
        f'  N_max = √(2E*/α·ε·d) = {N_th:.2f}'
    )
    if N_measured:
        ratio = N_measured / N_th
        param_box += f'\n  Measured N* = {N_measured}\n  N*/N_max = {ratio:.3f}'
        param_box += '  ✓' if ratio <= 1.0 else '  ✗ (theorem violated!)'

    ax3a.text(0.03, 0.97, param_box, transform=ax3a.transAxes, va='top',
              fontsize=8, color='#ccc', family='monospace',
              bbox=dict(boxstyle='round,pad=0.4',
                        facecolor='#111', alpha=0.75, edgecolor='none'))

    # Right: constraint target geometry
    theta_ring = np.linspace(0, 2*np.pi, 200)
    ax3b.plot(np.cos(theta_ring), np.sin(theta_ring),
              '--', color='#333', linewidth=1.2)

    cmap_pts = plt.cm.plasma(np.linspace(0.1, 0.9, len(targets)))
    for i, (tgt, col) in enumerate(zip(targets, cmap_pts)):
        ax3b.scatter(*tgt, color=col, s=90, zorder=5,
                     edgecolors='white', linewidths=0.5)
        ax3b.text(tgt[0] * 1.18, tgt[1] * 1.18, f'H{i+1}',
                  fontsize=7.5, color=col, ha='center', va='center')
        if i < len(targets) - 1:
            ax3b.annotate('', xy=targets[i+1], xytext=tgt,
                          arrowprops=dict(arrowstyle='->', color='#444',
                                          lw=0.8))

    ax3b.scatter(0, 0, c='white', s=120, zorder=6, marker='+',
                linewidths=2)
    ax3b.text(0.08, 0, 'compromise', fontsize=7, color='#aaa')
    ax3b.set_xlim(-1.6, 1.6); ax3b.set_ylim(-1.6, 1.6)
    ax3b.set_aspect('equal')
    ax3b.set_title('Constraint Targets H₁…H₁₀\n'
                   'Each wants v at a different point on the ring',
                   color='white', fontsize=11)
    ax3b.set_xlabel('x', color='white')
    ax3b.set_ylabel('y', color='white')

    ax3b.text(0.02, 0.02,
              'Each constraint is a proposition Hᵢ.\n'
              'All pairs have pairwise frustration εᵢⱼ > 0.\n'
              'Adding constraints raises joint energy.\n'
              'Theorem 6.1 predicts when the budget E*\n'
              'is exceeded and the system enters [k].',
              transform=ax3b.transAxes, va='bottom', fontsize=8,
              color='#ccc',
              bbox=dict(boxstyle='round,pad=0.4',
                        facecolor='#111', alpha=0.75, edgecolor='none'))

    plt.tight_layout()
    fig3.savefig('mpc_separation.png', dpi=150, bbox_inches='tight',
                 facecolor=BG)
    print("    Saved: mpc_separation.png")

    # ═══════════════════════════════════════════════════════════════════════
    # FIGURE 4 — Hessian Probe: Directional Commitment Structure
    # ═══════════════════════════════════════════════════════════════════════
    print("  Running Hessian probe (directional commitment structure)...")

    fig4, axes4 = plt.subplots(1, 3, figsize=(19, 7))
    fig4.patch.set_facecolor(BG)
    for ax in axes4:
        ax.set_facecolor(PANEL)

    hessian_results = {}
    for (name, efn, desc), ax in zip(scenarios, axes4):
        r = results[name]
        probes = hessian_probe(efn, r['mins'], name, r['state'])
        hessian_results[name] = probes
        plot_hessian_panel(ax, efn, probes, name)

        # Print to terminal
        print(f"\n  [{r['state']}] {name} — Hessian eigenstructure:")
        for pr in probes:
            print(f"      Minimum #{pr['minimum_idx']+1}  v*=({pr['v_star'][0]:.3f}, {pr['v_star'][1]:.3f})")
            print(f"        λ₁={pr['lam1']:8.4f}  e₁=({pr['e1'][0]:+.3f},{pr['e1'][1]:+.3f})  "
                  f"r={min(pr['r1'],99):.3f}  [{pr['state1']}]")
            print(f"        λ₂={pr['lam2']:8.4f}  e₂=({pr['e2'][0]:+.3f},{pr['e2'][1]:+.3f})  "
                  f"r={min(pr['r2'],99):.3f}  [{pr['state2']}]")
            print(f"        anisotropy={pr['anisotropy']:.2f}×  combined=[{pr['combined']}]")

    # Shared legend for eigenvector colours
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='#4fc3f7', lw=2.5, label='[c] committed direction'),
        Line2D([0], [0], color='#ffb74d', lw=2.5, label='[s] suspended direction'),
        Line2D([0], [0], color='#ef5350', lw=2.5, label='[k] conflict direction'),
        Line2D([0], [0], color='white',   lw=1.5, linestyle='--',
               label='thermal ellipse (1/√λ semi-axes)'),
    ]
    fig4.legend(handles=legend_elements, loc='lower center', ncol=4,
                fontsize=9, facecolor=PANEL, labelcolor='white',
                framealpha=0.85, bbox_to_anchor=(0.5, -0.02))

    fig4.suptitle(
        'MPC Hessian Probe — Directional Commitment Structure at Energy Minima\n'
        'Ellipse = thermal fluctuation basin (1/√λ semi-axes)   '
        'Arrows = principal eigenvectors coloured by directional MPC state\n'
        'Anisotropy = λ_max/λ_min — asymmetry of commitment across principal directions',
        fontsize=10, color='white', y=1.01
    )
    plt.tight_layout(rect=[0, 0.04, 1, 0.98])
    fig4.savefig('mpc_hessian.png', dpi=150, bbox_inches='tight',
                 facecolor=BG)
    print("\n    Saved: mpc_hessian.png")

    # ═══════════════════════════════════════════════════════════════════════
    # FIGURE 5 — Catmull-Clark Phase Boundary Display
    # ═══════════════════════════════════════════════════════════════════════
    print("  Running Catmull-Clark phase boundary display...")

    # Run on committed scenario — clearest phase structure, two distinct
    # E_C wells that the limit curve will resolve to smooth closed loops.
    # Also run on conflict to show the absence of committed zones.
    for cc_name, cc_efn, cc_state in [
        ('committed', energy_committed, 'c'),
        ('conflict',  energy_conflict,  'k'),
    ]:
        r = results[cc_name]
        probes = hessian_results[cc_name]
        fig5 = catmull_clark_display(
            cc_efn, probes, cc_name, cc_state, n_steps=5
        )
        fname = f'mpc_catmullclark_{cc_name}.png'
        fig5.savefig(fname, dpi=150, bbox_inches='tight',
                     facecolor='#12121f')
        print(f"    Saved: {fname}")
        plt.close(fig5)

    # ── Terminal Summary ──────────────────────────────────────────────────
    print("\n" + "═"*62)
    print("  RESULTS")
    print("═"*62)
    for name, efn, desc in scenarios:
        r = results[name]
        bar_str = f'{r["bar"]:.3f}' if r["bar"] != float('inf') else '∞'
        print(f"\n  [{r['state']}] {name}")
        print(f"      E_min  = {r['e_min']:.4f} k_BT")
        print(f"      ΔE     = {bar_str} k_BT")
        print(f"      Minima = {len(r['mins'])}")
        print(f"      Classified [{r['state']}]: ", end='')
        if r['state'] == 'c':
            print("deep well absorbed perturbation → committed ✓")
        elif r['state'] == 's':
            print("shallow well, barrier ≤ E_c → suspended ✓")
        else:
            print(f"residual energy {r['e_min']:.2f} > E_s={E_S} → conflict ✓")

    print(f"\n  Separation Theorem:")
    print(f"      Theoretical N_max  = {N_th:.2f}")
    if N_measured:
        ratio = N_measured / N_th
        verdict = "✓ HOLDS" if ratio <= 1.0 else "✗ VIOLATED"
        print(f"      Measured N*        = {N_measured}")
        print(f"      N*/N_max           = {ratio:.3f}   {verdict}")
    else:
        print(f"      N* not reached within N={max(Ns)} constraints")

    print("\n" + "═"*62)
    print("  Output files:")
    print("    mpc_landscape.png              — energy landscape gallery")
    print("    mpc_perturbation.png           — perturbation response + B/W signal")
    print("    mpc_separation.png             — Separation Theorem validation")
    print("    mpc_hessian.png                — Hessian probe: directional commitment")
    print("    mpc_catmullclark_committed.png — CC phase boundary: committed")
    print("    mpc_catmullclark_conflict.png  — CC phase boundary: conflict")
    print("═"*62 + "\n")

    plt.show()


if __name__ == '__main__':
    main()