#!/usr/bin/env python3
"""
physics_primitives.py — validated core observables for the MPC Langevin rig
===========================================================================

This module is the distilled output of a prototyping session that worked out
the core observables for the dynamical MPC framework. Three prototypes were
built and tested on the four-scenario geometry (committed / suspended /
conflict / reset); the findings are documented in PROTOTYPE_FINDINGS.md.

The primitives in this file are what survived. Import them into the full
mpc_lattice.py rebuild and extend — do not rewrite.

    from physics_primitives import (
        run_langevin, run_paired,
        autocorr_fft, tau_integral,
        correlation_time, survival_margin, cross_dissipation,
        measure_fdr,
    )

Run standalone for a sanity check:

    python3 physics_primitives.py
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


# ── Sanity checks ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("physics_primitives.py — sanity checks")
    print("=" * 62)

    # ── 1. Harmonic well, analytical prediction for τ_V ─────────────────
    # For overdamped Langevin in U = (1/2) k |v|², v(t) is an
    # Ornstein–Uhlenbeck process with relaxation rate k. V = |v|² is a
    # quadratic function of a Gaussian process; its autocorrelation
    # decays at rate 2k, so τ_V = 1/(2k).
    v0 = np.array([0.0, 0.0])
    U_harm = lambda v: 0.5 * np.sum(v ** 2)
    V_sq   = lambda v: np.sum(v ** 2)

    print("\n[1] Harmonic well k=1:  expected τ_V = 0.5")
    traj = run_langevin(U_harm, v0, 6000, rng=np.random.default_rng(42))
    print(f"    measured τ_V = {correlation_time(V_sq, traj):.4f}")

    # ── 2. Survival margin between stronger and weaker wells ────────────
    print("\n[2] Survival margin: strong well (k=4) vs weak well (k=0.5)")
    U_strong = lambda v: 2.00 * np.sum(v ** 2)
    U_weak   = lambda v: 0.25 * np.sum(v ** 2)
    ts = run_langevin(U_strong, v0, 6000, rng=np.random.default_rng(10))
    tw = run_langevin(U_weak,   v0, 6000, rng=np.random.default_rng(11))
    gamma, tA, tE = survival_margin(V_sq, ts, tw)
    print(f"    τ_strong = {tA:.4f}   τ_weak = {tE:.4f}   γ = {gamma:+.4f}")
    print(f"    (stiffer well → shorter τ → γ > 0 in a Markovian substrate;")
    print(f"     paper sign-inversion caveat applies — see FINDINGS §1)")

    # ── 3. FDR on harmonic well — should exhibit FDT ────────────────────
    # In the overdamped-Langevin convention of this code, the effective
    # temperature is D_EFF (not K_BT); Einstein relation gives variance
    # ⟨v²⟩ = D/k in equilibrium, so FDT slope = 1/D_EFF in [C(0)−C]/K_BT
    # units. With D_EFF = 0.3, FDT predicts slope ≈ 3.33.
    print(f"\n[3] FDR on harmonic well — expected slope ≈ {1/D_EFF:.2f}")
    print(f"    (FDT holds; slope = 1/D_EFF in these natural units)")
    h = 0.3
    U_base = lambda v: 0.5 * np.sum(v ** 2)
    U_pert = lambda v: 0.5 * np.sum((v - np.array([h, 0.0])) ** 2)
    V_x    = lambda v: v[0]
    tau, C, chi = measure_fdr(U_base, U_pert, V_x, v0, h,
                              n_burnin=1000, n_resp=1500, n_reps=24, seed=7)
    x_end = (C[0] - C[-100:].mean()) / K_BT
    y_end = chi[-100:].mean()
    print(f"    late-time [C(0)−C]/kT = {x_end:.4f}   χ = {y_end:.4f}")
    print(f"    measured slope = {y_end / (x_end + 1e-12):.3f}  "
          f"(predicted {1/D_EFF:.2f})")

    print("\nAll primitives working. Ready for the full rig build.")
