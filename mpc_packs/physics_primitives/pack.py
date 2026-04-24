"""physics_primitives — validated core observables for the MPC Langevin rig.

Moved verbatim from docs/dynamical-track/physics_primitives.py (Task A,
SESSION_A_STATE.md). Do not edit without re-running the four-scenario
validation in mpc_lattice.py; the constants and integrator parameters are
load-bearing.

Public primitives:

    run_langevin, run_paired,
    autocorr_fft, tau_integral,
    correlation_time, survival_margin, cross_dissipation,
    measure_fdr,
    numerical_grad,
    K_BT, DT, D_EFF
"""

import numpy as np


# ── Physical constants (natural units, k_BT = 1) ────────────────────────────
K_BT  = 1.0
DT    = 0.01
D_EFF = 0.3


# ── Numerical gradient ──────────────────────────────────────────────────────
def numerical_grad(fn, v, eps=1e-5):
    """Central-difference gradient of a scalar potential."""
    g = np.zeros_like(v)
    for i in range(len(v)):
        vp = v.copy(); vp[i] += eps
        vm = v.copy(); vm[i] -= eps
        g[i] = (fn(vp) - fn(vm)) / (2 * eps)
    return g


# ── Overdamped Langevin ─────────────────────────────────────────────────────
def run_langevin(U, v0, n_steps, dt=DT, D=D_EFF, rng=None):
    """
    Euler–Maruyama integrator for overdamped Langevin dynamics:
        v(t+dt) = v(t) − ∇U(v)·dt + √(2·D·dt)·ξ,   ξ ~ N(0, I)
    Returns trajectory array of shape (n_steps, dim).
    """
    if rng is None:
        rng = np.random.default_rng(0)
    v = np.asarray(v0, dtype=float).copy()
    traj = np.empty((n_steps, len(v)))
    s2 = np.sqrt(2 * D * dt)
    for i in range(n_steps):
        F = -numerical_grad(U, v)
        v = v + F * dt + s2 * rng.standard_normal(len(v))
        traj[i] = v
    return traj


def run_paired(U_unp, U_per, v0, n_burnin, n_resp, n_reps,
               dt=DT, D=D_EFF, seed=0):
    """
    Matched-noise paired Langevin trajectories for FDR measurement.

    For each replica, generates one noise sequence and simulates two
    trajectories (always-unperturbed U_unp vs perturbed = U_unp during
    burn-in then U_per) driven by the SAME noise realization. This is
    the common-random-numbers variance-reduction technique — without it
    the response signal is swamped by ensemble fluctuation.

    Returns (trajs_unp, trajs_per), each shape (n_reps, n_burnin+n_resp, dim).
    """
    n_total = n_burnin + n_resp
    dim = len(v0)
    tu = np.empty((n_reps, n_total, dim))
    tp = np.empty_like(tu)
    s2 = np.sqrt(2 * D * dt)

    for r in range(n_reps):
        rng = np.random.default_rng(seed + r)
        noise = rng.standard_normal((n_total, dim))
        vu = np.asarray(v0, dtype=float).copy()
        vp = vu.copy()
        for i in range(n_total):
            xi = noise[i]
            Fu = -numerical_grad(U_unp, vu)
            vu = vu + Fu * dt + s2 * xi
            tu[r, i] = vu
            U_now = U_unp if i < n_burnin else U_per
            Fp = -numerical_grad(U_now, vp)
            vp = vp + Fp * dt + s2 * xi
            tp[r, i] = vp
    return tu, tp


# ── Autocorrelation ─────────────────────────────────────────────────────────
def autocorr_fft(x, normalize=True):
    """
    Unbiased autocorrelation of a 1D signal via FFT (Wiener–Khinchin).

    If normalize=True, returns C(τ)/C(0). Otherwise returns C(τ) in signal
    units squared. Returns zeros if the signal has negligible variance.
    """
    x = np.asarray(x, dtype=float) - np.mean(x)
    n = len(x)
    if np.var(x) < 1e-14:
        return np.zeros(n)
    X = np.fft.fft(x, 2 * n)
    C = np.fft.ifft(X * np.conj(X)).real[:n]
    C /= (n - np.arange(n))  # unbiased
    return C / C[0] if normalize else C


def tau_integral(C, dt=DT, cutoff=0.05):
    """
    Integral relaxation time τ = ∫₀^T C(t) dt, T = first time C drops below
    `cutoff`. The cutoff is load-bearing — without it, statistical noise in
    the autocorrelation tail dominates the integral for low-variance signals.
    """
    below = np.where(C < cutoff)[0]
    if len(below) == 0:
        return float(np.trapezoid(C, dx=dt))
    end = max(below[0], 3)
    return float(np.trapezoid(C[:end], dx=dt))


# ── Survival margin and cross-dissipation ───────────────────────────────────
def correlation_time(V_obs, traj, dt=DT, burn_frac=0.2):
    """τ_A from autocorrelation of V_obs along `traj`, after burn-in."""
    start = int(traj.shape[0] * burn_frac)
    V = np.array([V_obs(v) for v in traj[start:]])
    C = autocorr_fft(V, normalize=True)
    return tau_integral(C, dt)


def survival_margin(V_obs, traj_constrained, traj_bath, dt=DT):
    """
    γ_A  =  τ_A⁻¹ − τ_env⁻¹

    ----  CAVEAT (Markovian substrate)  ----
    The paper (Table 1) predicts γ_A ≪ 0 for committed and γ_A ≈ 0 for
    reset, via a memory-kernel formulation (§7). In overdamped Markovian
    Langevin on harmonic wells, V_A's autocorrelation reflects FAST
    thermal relaxation in stiff wells — so τ_A comes out SHORT for
    committed, giving γ_A > 0. This is a substrate-level artifact, not an
    observable-choice issue. Interpret |γ_A| as regime depth; use γ_ij
    sign for k-state detection; use FDR shape for qualitative regime
    discrimination. See PROTOTYPE_FINDINGS.md §1.

    Returns (gamma_A, tau_A, tau_env).
    """
    tA  = correlation_time(V_obs, traj_constrained, dt)
    tE  = correlation_time(V_obs, traj_bath, dt)
    return 1.0 / tA - 1.0 / tE, tA, tE


def cross_dissipation(V_i, V_j, traj, dt=DT):
    """
    γ_ij  =  τ_{i∧j}⁻¹ − max(τ_i⁻¹, τ_j⁻¹)

    Joint observable V_i + V_j (sum of violations). Positive γ_ij is the
    k-state destructive-interference signature.

    Returns (gamma_ij, tau_i, tau_j, tau_ij).
    """
    V_joint = lambda v: V_i(v) + V_j(v)
    ti  = correlation_time(V_i, traj, dt)
    tj  = correlation_time(V_j, traj, dt)
    tij = correlation_time(V_joint, traj, dt)
    return 1.0 / tij - max(1.0 / ti, 1.0 / tj), ti, tj, tij


# ── Fluctuation–Dissipation Ratio ───────────────────────────────────────────
def measure_fdr(U_base, U_pert, V_obs, v0, h_mag,
                n_burnin=2000, n_resp=4000, n_reps=32, seed=0, dt=DT):
    """
    Integrated response χ(τ) and spontaneous correlation C(τ) of V_obs,
    measured via matched-noise paired Langevin trajectories.

    U_base : unperturbed potential
    U_pert : perturbed potential (small shift coupling to V_obs; magnitude h_mag)
    V_obs  : observable

    Parametric FDR plot — χ (y) vs [C(0)−C(τ)]/k_BT (x):
      · diagonal slope 1  →  FDT holds (r-regime, equilibrium)
      · depressed stable slope < 1  →  c-regime (deep commitment)
      · curve bending from diagonal over τ  →  s-regime (aging)
      · non-monotonic or negative-slope region  →  k-regime

    Returns (tau_grid, C, chi), all length n_resp.
    """
    tu, tp = run_paired(U_base, U_pert, v0,
                        n_burnin, n_resp, n_reps, dt=dt, seed=seed)
    n_total = n_burnin + n_resp

    Vu = np.empty((n_reps, n_total))
    Vp = np.empty_like(Vu)
    for r in range(n_reps):
        for i in range(n_total):
            Vu[r, i] = V_obs(tu[r, i])
            Vp[r, i] = V_obs(tp[r, i])

    # Susceptibility (response per unit perturbation)
    chi = (Vp[:, n_burnin:].mean(axis=0) - Vu[:, n_burnin:].mean(axis=0)) / h_mag

    # Spontaneous correlation from unperturbed steady-state segment
    Vss = Vu[:, n_burnin:]
    dV  = Vss - Vss.mean()
    C   = np.mean([autocorr_fft(dV[r], normalize=False) for r in range(n_reps)],
                  axis=0)

    return np.arange(n_resp) * dt, C, chi
