# MPC Brain

**A physically-grounded inference architecture built on Metastable Propositional Calculus.**

[![Status](https://img.shields.io/badge/status-active%20development-blue)]()
[![RFC](https://img.shields.io/badge/RFC-001%20%28Session%202%20baseline%29-green)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)]()

---

## What this is

MPC Brain is a brain architecture — not a neural network, not a symbolic reasoner —
built on the thermodynamic inference framework described in the
**Metastable Propositional Calculus** paper (see `Metastable_Propositional_Calculus__MPC__as_a_Thermodynamic_Extension`).

The core idea: propositions are energy wells in a shared configuration space.
A set of lightweight "engines" evolves stochastically through that space.
The phase each engine settles in tells you whether the proposition is
**committed** (c), **suspended** (s), in **conflict** (k), or **reset** (r).
No gradient descent training. No weight matrices. Just thermodynamics.

```
                Observation
                    │
                    ▼
          ┌─────────────────────┐
          │  LLMConstraintEncoder│  (text → fn: R^n → R+)
          └─────────┬───────────┘
                    │  constraint functions
                    ▼
          ┌─────────────────────┐
          │    JAXSubstrate      │  (energy landscape)
          └─────────┬───────────┘
                    │  gradient / Hessian
                    ▼
          ┌─────────────────────┐
          │    AutoCluster       │  (colony of MetastableEngines)
          └─────────┬───────────┘
                    │  PhaseTransitionEvents
                    ▼
          ┌─────────────────────┐
          │      EventBus        │  (publish-subscribe)
          └─────────────────────┘
```

---

## Architecture

The system is governed by **RFC-001-MPC-BRAIN.md**, which specifies the
interfaces every component must satisfy.  The rule is: the physics
(Section 3 of the RFC) is not negotiable; everything else is.

| Component | File | Description |
|-----------|------|-------------|
| `Substrate` | `mpc_engine_rfc001.py` | Energy landscape. Holds constraints, computes gradients. |
| `JAXSubstrate` | `mpc_session2.py` | Substrate with `jax.grad` / `jax.hessian` (156× speedup at dim=64 vs finite difference). |
| `MetastableEngine` | `mpc_engine_rfc001.py` | Single Langevin integrator. Classifies its own phase per §3.1. |
| `MPCCluster` | `mpc_engine_rfc001.py` | Colony of engines sharing a substrate and budget. |
| `AutoCluster` | `mpc_session2.py` | Self-organising cluster. Spawns/culls engines. Sheds load when in k-state. |
| `LLMConstraintEncoder` | `mpc_session2.py` | Converts natural-language propositions to constraint functions via the Anthropic API (fallback: word-hash heuristic). |
| `EventBus` | `mpc_engine_rfc001.py` | Pub-sub event channel. Only connection between brain and measurement. |
| `Calorimeter` | `mpc_engine_rfc001.py` | Read-only measurement. Subscribes to bus. Never touches brain components. |

---

## Phases

Every engine is always in exactly one of four states:

| Phase | Meaning | Energy condition |
|-------|---------|-----------------|
| **c** (committed) | Found a stable minimum; ready to act | E < E_c AND H ≻ 0 |
| **s** (suspended) | Holding a hypothesis under uncertainty | E_c ≤ E < E_s |
| **k** (conflict) | Contradictory constraints; cannot commit | E ≥ E_s OR H ⊁ 0 |
| **r** (reset) | Budget exhausted; information erased | budget exceeded |

A reset costs at least k_BT·ln(2) per bit erased (Landauer bound), emitted as a `LandauerEvent`.

---

## Quickstart

```bash
git clone <repo>
cd mpc-brain
pip install numpy jax matplotlib anthropic
```

Set your Anthropic API key:

```bash
export ANTHROPIC_KEY=sk-ant-...
```

Run Session 2 (all tasks):

```bash
python mpc_session2.py
```

Expected output:

```
Task 1  extrap speedup @ dim=64: 156x  jax_ok=True
Task 2  worst ratio:             0.4868  PASS
Task 3  AutoCluster smoke:        PASS
Task 4  encoder mode:             api          (or 'fallback' without key)
Task 5  hello-world:             PASS
```

---

## Hello World

The canonical demo is `hello_world()` in `mpc_session2.py`.

**Phase A:** load two contradictory propositions simultaneously:
- P1: *"the object is spherical and smooth"* (ball)
- P2: *"the object has sharp corners and flat faces"* (prism)

The cluster enters k-state (conflict), sheds the weaker constraint (P1), and
suspends on P2.

**Phase B:** add the disambiguating proposition:
- P3: *"the object fits in one hand and is used for writing"* (pen ≈ prism-family)

The cluster commits to the P2/P3 neighbourhood.  Distance to P1 centre: 3.67.
Distance to P2 centre: 0.85.  The ball hypothesis is correctly rejected.

---

## JAX Acceleration

`JAXSubstrate` uses `jax.jit(jax.grad(...))` and `jax.jit(jax.hessian(...))`.

Stiffness values are baked into the XLA computation at compile time.  Any call
to `register`, `deregister`, or `update_lambda` increments a version counter
that forces recompilation on the next gradient call.  This ensures stiffness
changes are never silently stale.

Measured on CPU (no GPU):

| Backend | dim | Steps | Time |
|---------|-----|-------|------|
| Finite Difference | 8 | 1000 | 6.9 s (actual) |
| Finite Difference | 64 | 1000 | ~400 s (extrapolated, O(n²)) |
| JAX | 64 | 1000 | 2.6 s (actual) |

**156× extrapolated speedup on CPU.  GPU would add further hardware parallelism.**

---

## LLM Connector

`LLMConstraintEncoder` is the bridge between language and physics.

With `ANTHROPIC_KEY` set, it calls `claude-sonnet-4-6` with a system prompt
that requires a Python function `fn(v)` returning a non-negative scalar.
The response is executed in a restricted namespace (`{np, __builtins__: {}}`)
and sanity-checked before use.

Without an API key, it falls back to a deterministic word-hash quadratic
encoder (suitable for the hello-world demo; not suitable for production).

```python
encoder = LLMConstraintEncoder(dim=32)
fn = encoder.encode("the object is heavier than 1 kg")
# fn: R^32 → R+, cached by proposition string
```

A formal connector interface (`ObservationSocket`) is specified in
**RFC-001 AMEND-004** and will be implemented in Session 3.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_KEY` | For LLM encoding | API key for `claude-sonnet-4-6` |

---

## Project Structure

```
mpc-brain/
├── README.md                          # This file
├── RFC-001-MPC-BRAIN.md              # Protocol specification
├── SESSION-2-REPORT.md               # Session 2 implementation report
├── mpc_engine_rfc001.py              # Session 1: core engine (base classes)
├── mpc_session2.py                   # Session 2: JAXSubstrate, AutoCluster,
│                                     #            LLMConstraintEncoder, hello-world
├── mpc_lattice.py                    # Lattice substrate (exploratory)
├── wsl_dev_profile.json              # Dev environment config
└── Metastable_Propositional_Calculus__MPC__as_a_Thermodynamic_Extension
                                      # Foundational paper
```

---

## Theoretical Basis

The phase classifier is a consequence of non-equilibrium thermodynamics applied
to inference.  It is not a design choice.  The four invariants in RFC-001 §3
are physical:

1. **Phase classification** — by energy and Hessian spectrum only.
2. **Landauer bound** — resets cost k_BT·ln(2) per bit, always emitted.
3. **Budget enforcement** — no step exceeds E\*.
4. **Maintenance cost** — suspended engines exert a restoring force.

The **Thermodynamic Separation Theorem** (RFC-001 §4.3) bounds the number of
simultaneously suspended engines:

```
N_max = √(2·E* / (α · ε_min · d_avg))
```

Session 2 empirically verified this bound holds across N = 5…50 constraints
(worst observed ratio: 0.49, well below the 1.15 tolerance).

---

## Roadmap

| Session | Scope |
|---------|-------|
| 1 | Core engine: Substrate, MetastableEngine, MPCCluster, EventBus, Calorimeter |
| 2 | JAXSubstrate (156× speedup), AutoCluster, LLMConstraintEncoder, hello-world demo |
| 3 | AMEND-001 (temporal frustration decay), AMEND-003 (lateral maintenance field), ObservationSocket (formal LLM connector), multi-cluster network demo |

---

## Contributing

This project is a living document.  Amendments to the RFC are welcome.
The physical invariants in §3 are not amendable.  Everything else is.

Developed collaboratively between a hobbyist researcher and Claude (Anthropic),
April 2026.
