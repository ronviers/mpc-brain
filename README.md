# MPC Brain

**A physically-grounded inference architecture built on Metastable Propositional Calculus.**

[![Status](https://img.shields.io/badge/status-active%20development-blue)]()
[![Standards](https://img.shields.io/badge/standards-RFC--001%20·%20RFC--002%20·%20RFC--003%20·%20RFC--004-green)]()
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)]()

---

## What this is

MPC Brain is a brain architecture — not a neural network, not a symbolic reasoner —
built on the thermodynamic inference framework described in
**On the Physical Limits of Boolean Algebra as a Theory of Inference**.

The core idea: propositions are energy wells in a shared configuration space.
A set of lightweight "engines" evolves stochastically through that space. The
phase each engine settles in tells you whether the proposition is **committed**
(c), **suspended** (s), in **conflict** (k), or **reset** (r). No gradient
descent training. No weight matrices. Just thermodynamics.

The project is organised in three layers under RFC-002. The kernel carries the
RFC-001 physics and is closed for modification. Packs are capability modules
that extend the kernel through three documented plug points. Experiments compose
packs against a domain and produce reports. The rule is: the physics is not
negotiable; everything else is.

---

## The three layers

```
┌─────────────────────────────────────────────────────────────────┐
│                         EXPERIMENTS                             │
│               hello_world · maze · (dynamical)                  │
├─────────────────────────────────────────────────────────────────┤
│                            PACKS                                │
│   physics_primitives · dynamical_gate                           │
│   jax_substrate · auto_cluster                                  │
│   decaying_substrate · persistence_substrate                    │
│   effector · observation_socket · llm_encoder                   │
│   lateral_cluster · z3_socket · metareasoner                    │
│   symbolic_forebrain · mobility_detector (shelved)              │
├─────────────────────────────────────────────────────────────────┤
│                           KERNEL                                │
│  Substrate · Engine · Cluster · Network · EventBus · Phase      │
├─────────────────────────────────────────────────────────────────┤
│               PHYSICS · RFC-001 §3 · non-negotiable             │
└─────────────────────────────────────────────────────────────────┘
```

The **kernel** is the minimal implementation of RFC-001-MPC-BRAIN. Versioned,
small, frozen against per-session modification.

**Packs** are self-contained modules conforming to one of three plug points:
`SubstrateExtension` (augments the energy landscape), `EventSubscriber`
(observes bus events), or `Governor` (mutates cluster state in response to
signals). Each pack is ~50–200 lines, has a config dataclass, an attach/detach
lifecycle, and zero cross-pack dependencies except where declared.

**Experiments** select a kernel version, a pack manifest, and a domain. They
run, produce a report, and do not add capabilities to the kernel. Sessions,
going forward, are experiments.

A biological correspondence motivates the shape:
perineuronal nets are decadal, synaptic weights are days, action potentials
are milliseconds. Each timescale has its own substrate and its own interface.
Mixing them is forbidden. The project structure applies the same discipline.

---

## Document map

The project is specified across a small set of companion documents. Read them
in this order if you are new:

| Document | What it is |
|---|---|
| `RFC-001-MPC-BRAIN.md` | The kernel protocol. Specifies substrate, engine, cluster, network, event bus, and the non-amendable energy invariant. |
| `RFC-002-MPC-PROJECT-STRUCTURE.md` | How the project is organised. Defines kernel, packs, experiments, plug points, promotion rules, and directory layout. |
| `RFC-003-MPC-TRACE-FORMAT-001.md` | The wire format for observing an experiment as it runs or after it finishes. |
| `RFC-004-MPC-DYNAMICAL.md` | The dynamical-track extension: regime classification via correlation times and the Fluctuation–Dissipation Ratio, per the Session-A Langevin validation. |
| `MPC-ANATOMY-001.svg` | A poster-sized visual reference. The three layers, the biology mapping, the promotion ladder. Hang it on a wall. |
| `Mechanisms of Memory Persistence.md` | Survey of state-of-the-art neurobiology. Source material for the pack roadmap (RFC-002 Appendix A). |
| `dynamical-track/` | Research artefacts from the dynamical-track prototyping: `mpc_lattice.py` (Langevin validation rig), `SESSION_A_STATE.md`, the four-scenario figures. |

Session reports (`SESSION-N-REPORT.md`) document specific implementation rounds
and stand as historical record. They are not normative.

---

## Directory layout

```
mpc-brain/
├── README.md                          # this file
├── docs/
│   ├── RFC-001-MPC-BRAIN.md
│   ├── RFC-002-MPC-PROJECT-STRUCTURE.md
│   ├── RFC-003-MPC-TRACE-FORMAT-001.md
│   ├── RFC-004-MPC-DYNAMICAL.md
│   ├── MPC-ANATOMY-001.svg
│   ├── Mechanisms of Memory Persistence.md
│   └── dynamical-track/               # Langevin rig + Session-A artefacts
│
├── mpc_kernel/                        # RFC-001 physics, versioned
│   ├── __version__.py                 # 0.4.0
│   └── rfc001/
│       ├── phase.py                   # Phase enum
│       ├── substrate.py               # base Substrate, topological classify()
│       ├── engine.py                  # MetastableEngine
│       ├── cluster.py                 # MPCCluster
│       ├── network.py                 # Network, Calorimeter
│       ├── bus.py                     # EventBus
│       └── events.py                  # PhaseTransitionEvent, LandauerEvent, BudgetResetEvent
│
├── mpc_packs/                         # capability modules
│   ├── physics_primitives/            # Langevin + dynamical classifier
│   ├── dynamical_gate/                # streaming-τ FDR release + DynamicalEngine
│   ├── mobility_detector/             # shelved linear mobile-vs-pinned probe
│   ├── jax_substrate/                 # JAX-accelerated Substrate
│   ├── auto_cluster/                  # self-organising MPCCluster (RFC-001 §4.3)
│   ├── decaying_substrate/            # temporal frustration decay (AMEND-001)
│   ├── persistence_substrate/         # AMEND-006 (PersistenceSubstrate + Cluster)
│   ├── effector/                      # commit-accounting subscriber (AMEND-005)
│   ├── lateral_cluster/               # AMEND-003 lateral maintenance field
│   ├── observation_socket/            # AMEND-004 ObservationSocket family
│   ├── llm_encoder/                   # natural-language → constraint encoder
│   ├── z3_socket/                     # Z3-backed ObservationSocket (concrete)
│   ├── metareasoner/                  # EventSubscriber, per-cluster signals
│   └── symbolic_forebrain/            # Governor
│
├── mpc_engine_rfc001.py               # historical monolith (top-level for legacy imports)
├── mpc_session2.py                    # ↑ sys.modules alias → experiments/historical/
├── mpc_session3.py                    # ↑ same
├── mpc_session4.py                    # ↑ same
│
└── experiments/
    ├── hello_world/                   # kernel-only demo (scaffold)
    ├── maze/                          # maze navigation demo, now runs DynamicalEngine
    └── historical/                    # SESSION-<N>-REPORT.md, legacy scripts
```

Every pack directory contains at minimum `pack.py`, `config.py`,
`test_pack.py`, and `README.md`. Every experiment directory contains at
minimum `manifest.py`, `run.py`, and `report.md`. RFC-002 §6 is normative
on this layout.

---

## Adding a pack

Packs are the operational unit of growth. When you want a new capability —
temporal decay on the frustration graph, a new constraint encoder, a
biological mechanism from `Mechanisms_of_Memory_Persistence.md` — you write
a pack.

The shape is always the same:

1. Pick a plug point. `SubstrateExtension` if the capability changes how the
   energy landscape is computed, updated, or maintained. `EventSubscriber`
   if it observes events without mutating anything. `Governor` if it reads
   signals and issues mutations to a cluster.
2. Create `mpc_packs/<your_pack>/` and write `pack.py`, `config.py`,
   `test_pack.py`, `README.md`.
3. Expose `attach(...)`, `detach(...)`, and at least one read or extension
   method per the plug point's contract.
4. Declare dependencies on other packs in the config dataclass. Never import
   a pack you have not declared.
5. Preserve the RFC-001 §3 invariants. Never shadow a kernel type. Never
   modify a kernel file.

If the capability would require mutating engine internals directly,
redefining a Phase, or shadowing an event type, it is not a pack. It is a
kernel revision and proceeds under RFC-002 §5.3. The default answer to "is
this a kernel revision?" is no.

RFC-002 Appendix A lists eight proposed packs derived from the persistence
doc (PNN-Archive, KIBRA-Shield, PKMzeta-Maintenance, SWR-Replay,
STC-Tagging, ActivitySilent, EngramReconstruction, Methylation-Lock),
with size estimates and dependencies. Each is independent. Pick one, write
it, attach it to an experiment.

---

## Running an experiment

An experiment is a composition, not a script.

```python
# experiments/maze/manifest.py
KERNEL_REQUIRED = "0.4.0"
PACKS = [
    ("decaying_substrate",    {}),
    ("persistence_substrate", {"usage_coef": 1.0, "outcome_coef": 0.3,
                               "tau_base": 200.0}),
    ("z3_socket",             {}),
    ("metareasoner",          {"window": 50, "bucket_tolerance": 0.5}),
    ("symbolic_forebrain",    {"plan_library": "maze_rules"}),
]
EXPERIMENT_CONFIG = {"maze_w": 7, "maze_h": 7, "dim": 4,
                     "n_steps": 1500, "E_c": 0.5, "E_s": 3.0, ...}
```

`experiments/maze/run.py` additionally exposes a `USE_DYNAMICAL_ENGINE`
toggle (default `True`) that replaces each cluster engine with a
`DynamicalEngine` carrying its own `DynamicalGate` +
`StreamingObservables` pair. Async release keeps `measure_fdr` off the
stepping critical path, so a gate firing during the 1500-step run
doesn't stall the loop.

`experiments/<name>/run.py` loads the manifest, attaches the packs to a fresh
kernel, runs the workload, writes trace data and the report. The report
follows the SESSION-N-REPORT template: final results table, per-component
sections, RFC-001 + RFC-002 conformance checklists, artefacts list, what
is open.

Experiments may emit RFC-003 trace frames (JSONL) for live or post-hoc
visualization. A `TraceWriter` pack is planned — until it lands, experiments
that want traces write them inline.

---

## Hello World

The kernel-only demo lives at `experiments/hello_world/`. It loads two
contradictory propositions simultaneously, observes the cluster enter
k-state and shed the weaker, then adds a disambiguating proposition and
observes commitment.

- P1: *"the object is spherical and smooth"* (ball)
- P2: *"the object has sharp corners and flat faces"* (prism)
- P3: *"the object fits in one hand and is used for writing"* (pen ≈ prism-family)

The cluster commits to the P2/P3 neighbourhood. Distance to P1 centre: 3.67.
Distance to P2 centre: 0.85. The ball hypothesis is correctly rejected.

The current `hello_world/` directory is a scaffold — `run.py` has the
narrative in place, but `manifest.py` and `report.md` are stubs pending
the jax_substrate / auto_cluster / effector / calorimeter carve-outs
(SESSION-5 "What's open" item 1). The maze experiment at
`experiments/maze/` is the currently-green reference demo.

---

## Phases

Every engine is always in exactly one of four states:

| Phase | Meaning | Condition |
|---|---|---|
| **c** (committed) | Found a stable minimum; ready to act | E < E_c ∧ H ≻ 0 |
| **s** (suspended) | Holding a hypothesis under uncertainty | E_c ≤ E < E_s |
| **k** (conflict) | Contradictory constraints; cannot commit | E ≥ E_s ∨ H ⊁ 0 |
| **r** (reset) | Budget exhausted; information erased | budget exceeded |

A reset costs at least k_BT·ln(2) per bit erased (Landauer bound), emitted
as a `LandauerEvent`.

---

## Theoretical basis

The phase classifier is a consequence of non-equilibrium thermodynamics
applied to inference. It is not a design choice. The four invariants in
RFC-001 §3 are physical:

1. **Phase classification** — by energy and Hessian spectrum only.
2. **Landauer bound** — resets cost k_BT·ln(2) per bit, always emitted.
3. **Budget enforcement** — no step exceeds E\*.
4. **Maintenance cost** — suspended engines exert a restoring force.

The **Thermodynamic Separation Theorem** (RFC-001 §4.3) bounds the number
of simultaneously suspended engines:

```
N_max = √(2·E* / (α · ε_min · d_avg))
```

This was empirically verified across N = 5…50 constraints (worst observed
ratio: 0.49, below the 1.15 tolerance) in an earlier session. The theorem
matters because it is the formal statement of why a bounded brain cannot
maintain unbounded hypotheses — premature commitment is not a bug, it is
what the second law requires.

The full derivation and its cognitive corollaries (frame problem, working
memory as metastability, Landauer gap) are in the foundational paper.

---

## Performance notes

The JAX-accelerated substrate (`jax_substrate`, not yet carved into a
pack — lives in the historical monolith) uses `jax.jit(jax.grad(...))`
and `jax.jit(jax.hessian(...))`. Stiffness values bake into the XLA
computation at compile time; `register`, `deregister`, and
`update_lambda` each bump a version counter that forces recompilation
on the next call, so stiffness changes are never silently stale.

Measured on CPU (no GPU), pre-carve-out:

| Backend | dim | Steps | Time |
|---|---|---|---|
| Finite Difference | 8 | 1000 | 6.9 s (actual) |
| Finite Difference | 64 | 1000 | ~400 s (extrapolated, O(n²)) |
| JAX | 64 | 1000 | 2.6 s (actual) |

~156× extrapolated speedup on CPU. GPU adds further hardware parallelism.

---

## Environment

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | For the `llm_encoder` pack only | API key for the constraint encoder that converts natural language to constraint functions. |

No other environment configuration is required. All packs are opt-in per
experiment manifest; the default manifest has no external dependencies.

---

## Status

RFC-002 is normative as of April 2026. Kernel at `0.4.0`.

- **Kernel** imports end-to-end. `mpc_kernel/rfc001/events.py` carries
  first-class `@dataclass` definitions for `PhaseTransitionEvent`,
  `LandauerEvent`, and `BudgetResetEvent` (Session 6 carve-out).
  `PhaseTransitionEvent` carries an optional `fdr_slope` field for
  dynamical classification.
- **Kernel event types are unified.** `PhaseTransitionEvent`, `Phase`,
  `LandauerEvent`, `BudgetResetEvent`, `EventBus`, and `Calorimeter`
  resolve to the same class object whether imported from
  `mpc_kernel.rfc001.*`, `mpc_engine_rfc001`, or
  `experiments.historical.mpc_session4`. Session 4's shadow
  `PhaseTransitionEvent` dataclass is retired.
- **Pack carve-out is complete.** Twelve first-class packs (plus
  `mobility_detector` shelved). No transitional shims remain. Every
  meaningful class from the Session-2/3/4 monoliths now has a proper
  pack with declared dependencies, real tests, and a README. The
  historical .py files in `experiments/historical/` shrunk from
  ~3300 LOC to ~1700 LOC and consist almost entirely of re-export
  statements + acceptance-test scaffolding. `InstrumentedEngine` is
  retired to an alias of the kernel `MetastableEngine` (Session 6's
  unification of `PhaseTransitionEvent.energy` made the distinct
  class redundant).
- **Dynamical track.** `mpc_packs/physics_primitives` provides the
  Langevin observables and the four-regime classifier
  `classify_phase_dynamical(...)`. `mpc_packs/dynamical_gate` layers
  on streaming-τ release gating, paired streaming estimators, and
  `DynamicalEngine` — a `MetastableEngine` subclass that emits
  `PhaseTransitionEvent` with `fdr_slope` populated automatically on
  transitions that occurred after a gate release. Async release via
  `async_release=True` keeps `measure_fdr` off the stepping critical
  path (~23× stepping speedup, slope byte-identical). Full Session-A
  rig reproduces via `python docs/dynamical-track/mpc_lattice.py`.
- **Latest green experiment:** `experiments/maze/` runs
  `DynamicalEngine` as a drop-in for `InstrumentedEngine`. All six
  TASK-5 acceptance criteria PASS. After Session 10's M6 rule +
  stiffness tuning, the agent actually traverses the maze: reaches
  cell (4,4) in 1500 steps and within 1 cell of the goal (5,6) in
  3000 steps on the 7×7 maze (A* path length 27). Before M6: 3
  cells, 0 commits, trapped at (1,1).
- **Tolman battery** scaffolded at `experiments/tolman/`
  (`latent_learning.py` runs; detour / shortcut / reversal queued).
- **Real-time browser visualizer** at `H:\mpc-visualizer\` shows
  the engine traversing procedural mazes live with phase-color-coded
  agent, FDR gate state, streaming charts, and scrolling action log.
  `python H:\mpc-visualizer\server.py` then open <http://localhost:18765>.

---

## Roadmap

| Session | Scope | Status |
|---|---|---|
| 1 | Core engine: Substrate, MetastableEngine, MPCCluster, EventBus, Calorimeter | complete |
| 2 | JAXSubstrate, AutoCluster, LLMConstraintEncoder, hello-world demo | complete |
| 3 | Temporal frustration decay, lateral maintenance field, ObservationSocket, multi-cluster demo | complete |
| 4 | Effector (total-cost accounting), PersistenceSubstrate, network demo | complete |
| 5 | First RFC-002-native session. Kernel surgery, three new packs (Z3Socket, Metareasoner, SymbolicForebrain), first maze navigation experiment. | complete |
| 6 | Physics-primitives pack carve-out from `docs/dynamical-track/`; kernel events carved out of the legacy monolith shim; `classify_phase_dynamical` + `PhaseTransitionEvent.fdr_slope` wired end-to-end. | complete |
| 7 | Streaming-τ `dynamical_gate` pack: edge-triggered FDR release, `StreamingObservables` companion, `DynamicalEngine(MetastableEngine)` drop-in that auto-populates `PhaseTransitionEvent.fdr_slope`. One failed design (Maya mobility gate) shelved as `mobility_detector`. | complete |
| 8 | Async release worker. Top-level session-monolith shims + unified event / `Calorimeter` type identity. First-class packs carved: `jax_substrate`, `auto_cluster`, `effector`, `decaying_substrate` (promoted from shim). `DynamicalEngine` in the maze experiment; all six TASK-5 criteria PASS. | complete |
| 9 | Final S2/S3/S4 carve-out closes the shim era: `lateral_cluster`, `observation_socket`, `llm_encoder`, `persistence_substrate` (promoted from shim). `InstrumentedEngine` retired to an alias of `MetastableEngine`. Twelve first-class packs total. | complete |
| 10 | Maze determinism (seeded RNG). Monolith unification closes the last parallel implementations (Substrate, MetastableEngine, MPCCluster, Network all re-exported from kernel; `mpc_engine_rfc001.py` 997→233 LOC). **M6 forebrain rule** unblocks traversal; stiffness tuning gets agent to within 1 cell of goal. Tolman latent-learning scaffold. Thread-safety fix on async FDR release. | complete |
| 11 | Full Tolman battery (detour, shortcut, reversal). Traversal-completion polish — either extend step budget or add an M7 goal-adjacent boost. Visualizer polish (replay, video export, per-event maze highlights). | planned |
| 12 | Parallel mazes. Cross-cluster routing on transfer. First multi-substrate experiment. | planned |
| 9+ | Persistence-doc packs land per RFC-002 Appendix A. | queued |

The cleanest stopping condition: if Session 7's behavioural curves
qualitatively match Tolman's 1940s rat data, the substrate is doing real
cognitive work and there is something publishable. If they don't, there
are specific mechanisms to fix — and under RFC-002, fixing them no longer
means rewriting a thousand-line session file.

---

## Contributing

This project is a living document. Amendments to RFC-001 are welcome; the
physical invariants in §3 are not amendable. Amendments to RFC-002 follow
the promotion rules in §5. Comments and objections are invited in the
spirit stated in the foundational paper: as tests, not obstacles.

Developed collaboratively between a hobbyist researcher and Claude (Anthropic),
April 2026.
