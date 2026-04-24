"""physics_primitives pack — standalone sanity tests.

Ports the three self-checks from the original module's __main__ block into
asserted tests. Runs in well under a second; verifies that the integrator,
correlation-time, survival-margin, and FDR primitives all behave on the
harmonic well (known analytically). Does not reproduce the full four-scenario
Session A table — that lives in mpc_lattice.py (~75 s).

Invocation:

    python -m mpc_packs.physics_primitives.test_pack
"""

import numpy as np

from mpc_kernel.rfc001.phase import Phase

from mpc_packs.physics_primitives import (
    D_EFF,
    K_BT,
    classify_phase_dynamical,
    correlation_time,
    measure_fdr,
    run_langevin,
    survival_margin,
)


def test_harmonic_well_tau():
    """Overdamped Langevin in U = (1/2)|v|^2 gives V=|v|^2 an OU-squared
    autocorrelation decaying at rate 2k=2, so tau_V = 1/(2k) = 0.5."""
    v0 = np.zeros(2)
    U = lambda v: 0.5 * np.sum(v ** 2)
    V = lambda v: np.sum(v ** 2)
    traj = run_langevin(U, v0, 6000, rng=np.random.default_rng(42))
    tau = correlation_time(V, traj)
    assert 0.3 < tau < 0.7, f"tau_V out of sanity band [0.3, 0.7]: {tau:.4f}"
    return tau


def test_survival_margin_sign():
    """Stiffer well (k=2) -> shorter tau -> gamma_A > 0 vs weaker bath (k=0.25).
    Markovian sign per SESSION_A_STATE.md caveat."""
    v0 = np.zeros(2)
    V = lambda v: np.sum(v ** 2)
    U_strong = lambda v: 2.00 * np.sum(v ** 2)
    U_weak = lambda v: 0.25 * np.sum(v ** 2)
    ts = run_langevin(U_strong, v0, 6000, rng=np.random.default_rng(10))
    tw = run_langevin(U_weak, v0, 6000, rng=np.random.default_rng(11))
    gamma, tA, tE = survival_margin(V, ts, tw)
    assert tA < tE, f"strong-well tau should be shorter: tA={tA:.4f}, tE={tE:.4f}"
    assert gamma > 0, f"Markovian sign: expected gamma > 0, got {gamma:+.4f}"
    return gamma, tA, tE


def test_fdr_harmonic_slope():
    """FDT on a harmonic well: slope of chi vs [C(0)-C]/K_BT should be 1/D_EFF."""
    v0 = np.zeros(2)
    h = 0.3
    U_base = lambda v: 0.5 * np.sum(v ** 2)
    U_pert = lambda v: 0.5 * np.sum((v - np.array([h, 0.0])) ** 2)
    V_x = lambda v: v[0]
    _, C, chi = measure_fdr(
        U_base, U_pert, V_x, v0, h,
        n_burnin=1000, n_resp=1500, n_reps=24, seed=7,
    )
    x_end = (C[0] - C[-100:].mean()) / K_BT
    y_end = chi[-100:].mean()
    slope = y_end / (x_end + 1e-12)
    expected = 1.0 / D_EFF
    assert 0.5 * expected < slope < 1.5 * expected, (
        f"FDR slope out of band: measured {slope:.3f}, expected ~{expected:.3f}"
    )
    return slope, expected


def test_classifier_session_a_table():
    """Reproduce the four-row classification from SESSION_A_STATE.md using
    the measured values (tau_A, tau_env, gamma_A, gamma_ij, fdr_slope) as
    fixed inputs. This exercises the classifier, not the integrator."""
    cases = [
        # (tau_A, tau_env, gamma_A, gamma_ij, fdr_slope, expected)
        ("committed", 0.008, 1.387, +118.5, -21.1, +0.96, Phase.C),
        ("suspended", 0.426, 1.387, +1.67,  -1.20, +1.35, Phase.S),
        ("conflict",  0.003, 1.387, +296.1, -27.5, -0.09, Phase.K),
        ("reset",     1.387, 1.387, +0.00,  +0.02, -1.47, Phase.R),
    ]
    for name, tA, tE, gA, gij, slope, expected in cases:
        got = classify_phase_dynamical(tA, tE, gA, gij, slope)
        assert got == expected, f"{name}: expected {expected}, got {got}"
    return cases


if __name__ == "__main__":
    print("physics_primitives pack — sanity tests")
    print("=" * 62)

    tau = test_harmonic_well_tau()
    print(f"[1] harmonic-well tau_V     = {tau:.4f}   (expected ~0.5)   OK")

    gamma, tA, tE = test_survival_margin_sign()
    print(
        f"[2] survival margin          "
        f"tA={tA:.4f}  tE={tE:.4f}  gamma={gamma:+.4f}   OK"
    )

    slope, expected = test_fdr_harmonic_slope()
    print(f"[3] FDR slope (harmonic)    = {slope:.3f}   (expected ~{expected:.3f})   OK")

    cases = test_classifier_session_a_table()
    print(f"[4] classifier Session-A    4 rows classified, all match   OK")

    print("\nAll primitive sanity tests pass.")
