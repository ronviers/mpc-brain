MPC Working Group                                         Session Notes
Request for Comments: 002                                  April 2026
Category: Standards Track
Updates: None
Relates to: RFC-001-MPC-BRAIN


      MPC-PROJECT-STRUCTURE: Kernel, Packs, and Experiments


Abstract

   This document defines MPC-PROJECT-STRUCTURE, a protocol governing
   how implementations of RFC-001-MPC-BRAIN are organised on disk and
   how new capabilities are added over time.  It does not modify any
   physics, interface, or invariant defined in RFC-001.  It specifies
   three layers — kernel, packs, and experiments — and the rules that
   govern movement between them.

   The four-valued state space {c, s, k, r}, the energy invariant of
   RFC-001 §3, and the existing event protocol are unchanged.  This
   is a packaging standard, not a redesign.


Status of This Memo

   This document is a Standards Track RFC.  It promotes the contents
   of MPC-VISION-001 (advisory) to normative status and supersedes
   the implicit "one new file per session" convention used through
   Sessions 1 through 4.

   Comments and objections are invited in the spirit stated in the
   MPC paper: as tests, not obstacles.


Table of Contents

   1.  Introduction
   2.  Terminology
   3.  The Three Layers (Normative)
       3.1  Kernel
       3.2  Packs
       3.3  Experiments
   4.  Plug Points (Normative)
       4.1  SubstrateExtension
       4.2  EventSubscriber
       4.3  Governor
       4.4  What is not a plug point
   5.  Promotion Rules (Normative)
       5.1  Prototype to Pack
       5.2  Pack to Kernel candidate
       5.3  Kernel candidate to Kernel
       5.4  Default pack manifest
       5.5  Demotion
   6.  Directory Layout (Normative)
   7.  Conformance
       7.1  Kernel conformance
       7.2  Pack conformance
       7.3  Experiment conformance
   8.  Migration from RFC-001 baseline
   9.  Relationship to RFC-001
   10. Tooling and external interfaces
   11. Reference implementation notes
   Appendix A.  Pack roadmap (informational)
   Appendix B.  Biological correspondences (informational)


1.  Introduction

   RFC-001-MPC-BRAIN specifies the interfaces and invariants that
   any MPC brain implementation MUST satisfy.  It deliberately does
   not specify implementation, file layout, or process structure.
   That freedom is correct in principle.  In practice, sessions have
   accreted a single-file-per-revision pattern that compounds
   integration work each time a new capability is added.  By
   Session 4 this had produced a shadowed event type acknowledged as
   technical debt; Session 5 as proposed would compound the pattern
   further.

   This document specifies a structure that contains the growth.
   Capabilities are added by writing packs against documented plug
   points.  The kernel does not grow per session.  Sessions become
   experiments that compose existing capabilities.

   The motivating analogy is biological.  The brain solves the same
   problem of unbounded mechanism accretion by separating components
   along stability classes — perineuronal nets are decadal, synaptic
   weights are days, action potentials are milliseconds — and by
   enforcing that interactions between classes occur only through
   defined channels.  This document applies the same discipline to
   the project: separate what changes rarely from what changes often,
   and forbid the latter from modifying the former.


2.  Terminology

   The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL
   NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL"
   in this document are to be interpreted as described in RFC 2119.

   Kernel
      The minimal implementation of RFC-001-MPC-BRAIN required to
      run the RFC-001 hello-world demo with no optional features.
      Versioned.  Closed for modification by experiments.

   Pack
      A self-contained module conforming to one of the plug points
      defined in Section 4 and providing one capability.  Filed
      under mpc_packs/.  Independently testable, config-driven,
      and free of cross-pack dependencies except where declared.

   Plug point
      A documented interface through which a pack interacts with
      the kernel.  RFC-002 defines exactly three (Section 4).

   Experiment
      A composition of a kernel version, a pack manifest, a domain,
      and a workload, producing a report and trace data.
      Filed under experiments/.  Sessions, going forward, are
      experiments.

   Default pack manifest
      A documented list of packs that experiments load unless
      explicitly disabled.  Section 5.4.

   Promotion
      The movement of a capability from one layer to a more stable
      layer (prototype to pack, pack to kernel).  Governed by
      Section 5.

   Demotion
      The reverse movement.  Governed by Section 5.5.  Rare.


3.  The Three Layers (Normative)

3.1  Kernel

   The kernel MUST contain only those components required to satisfy
   RFC-001 §3 (the energy invariant), §4 (the brain protocol), §5
   (the observation protocol abstract), §6 (the event protocol), and
   §8 (the interaction rules).

   The kernel MUST be runnable in isolation against the RFC-001
   hello-world disambiguation demo with no optional features loaded.

   The kernel MUST be versioned.  The version string MUST follow
   semantic versioning (MAJOR.MINOR.PATCH).  Breaking changes to
   any kernel interface MUST increment MAJOR.  Additive changes that
   preserve backward compatibility MUST increment MINOR.  Bug fixes
   that change no interface MUST increment PATCH.

   The kernel MUST NOT depend on any pack.  The kernel MAY emit
   events that no pack subscribes to; the kernel MUST NOT assume any
   particular pack is loaded.

   The kernel SHOULD be small.  As of this RFC's date, the kernel is
   approximately 1200 lines of Python; growth beyond approximately
   2000 lines without a corresponding RFC-002 revision is a signal
   that promotion rules (Section 5.3) have been applied too liberally.

3.2  Packs

   A pack MUST conform to exactly one of the plug points defined in
   Section 4.

   A pack MUST expose:
      (a)  A configuration dataclass.
      (b)  An attach(...) lifecycle method.
      (c)  A detach(...) lifecycle method.
      (d)  At least one read API method (for EventSubscriber and
           Governor packs) or at least one extension method (for
           SubstrateExtension packs).

   A pack MUST NOT modify any kernel file.

   A pack MUST NOT shadow any kernel-defined type.  If a pack
   requires a new event type or data structure, it MUST define that
   type within the pack's own namespace.

   A pack MUST declare its dependencies on other packs in its
   configuration dataclass.  An undeclared cross-pack import is a
   conformance violation.

   A pack SHOULD be small.  Target: 50 to 200 lines of code excluding
   tests.  Packs significantly larger than 200 lines SHOULD be
   reviewed for whether they are doing more than one thing.

   A pack MUST be independently testable.  Its test suite MUST be
   able to attach the pack to a fresh kernel instance, exercise its
   read API or extension methods, and detach cleanly.

3.3  Experiments

   An experiment MUST declare, in a manifest:
      (a)  The kernel version it requires.
      (b)  The set of packs it loads, with their configurations.
      (c)  The domain or workload it runs.

   An experiment MAY contain domain-specific code (e.g., a maze
   generator, a hello-world driver).  An experiment MUST NOT contain
   code that would meet the criteria for a pack (Section 5.1) without
   first filing that code as a pack.

   An experiment SHOULD produce a report following the structure
   established by the SESSION-N-REPORT.md format: Final Results
   table, per-component sections, RFC-001 invariant checklist,
   artefacts list, what is open.

   An experiment's report MAY supersede or replace this RFC's
   guidance only on points labelled SHOULD; MUST-level requirements
   are not negotiable per-experiment.


4.  Plug Points (Normative)

4.1  SubstrateExtension

   A SubstrateExtension pack augments how the energy landscape is
   computed, updated, or maintained.  It subclasses or wraps the
   kernel's Substrate class.

   Required interface:

      class SubstrateExtension:
          def attach(self, cluster: Cluster) -> None: ...
          def detach(self, cluster: Cluster) -> None: ...

   A SubstrateExtension pack MUST preserve the RFC-001 §3 energy
   invariant.  It MAY change how gradients are computed, how
   frustration ε decays, how usage is tracked, or how barriers are
   maintained.  It MUST NOT alter the classification thresholds or
   the {c, s, k, r} state space.

   Examples in current codebase: JAXSubstrate, DecayingSubstrate,
   PersistenceSubstrate.

4.2  EventSubscriber

   An EventSubscriber pack observes events on the bus and either
   records data, computes derived signals, or emits new events
   internal to the pack.

   Required interface:

      class EventSubscriber:
          def attach(self, bus: EventBus) -> Self: ...
          def detach(self, bus: EventBus) -> None: ...
          def snapshot(self, key: Any = None) -> Any: ...

   An EventSubscriber pack MUST NOT write to substrate state
   directly, per RFC-001 §7.  It MAY inform a Governor (Section 4.3)
   which has that authority.

   An EventSubscriber pack MAY emit new event types, provided those
   types are defined within the pack's own namespace and are
   documented in the pack's README.

   Examples in current codebase: Calorimeter, Effector,
   Metareasoner (proposed).

4.3  Governor

   A Governor pack reads observed signals (typically from
   EventSubscribers) and modifies cluster state through the published
   cluster interface.  Governors are the only pack class permitted
   to mutate substrate-bearing components.

   Required interface:

      class Governor:
          def attach(self,
                     network: Network,
                     subscribers: Dict[str, EventSubscriber]) -> None: ...
          def detach(self,
                     network: Network,
                     subscribers: Dict[str, EventSubscriber]) -> None: ...
          def step(self) -> None: ...

   A Governor MUST declare which EventSubscribers it depends on.
   A Governor MUST declare which cluster-level mutations it performs
   (e.g., load, shed_load, local_budget, ops.reset).

   The set of permitted mutations is the public interface of the
   Cluster class as defined in RFC-001 §4.3.  A Governor that
   requires a mutation not in that set is requesting a kernel
   revision, not a pack.

   Examples in current codebase: SymbolicForebrain (proposed); the
   implicit governance currently spread through MPCCluster and
   AutoCluster MAY migrate here over time.

4.4  What is not a plug point

   There is intentionally no plug point for:
      (a)  Modifying the engine integrator directly.
      (b)  Shadowing or redefining a kernel event type.
      (c)  Redefining a Phase or its classification rule.
      (d)  Bypassing the EventBus to communicate between components.

   Capabilities that would require any of these are kernel revisions,
   not packs.  They proceed under Section 5.3 and require a vision-note
   revision.


5.  Promotion Rules (Normative)

5.1  Prototype to Pack

   A capability MAY be promoted from prototype (inline experiment
   code) to pack when ALL of the following hold:

      (a)  The capability has been used end-to-end in at least one
           experiment.
      (b)  Its public surface fits the pack interface defined in
           Section 3.2.
      (c)  Its interaction with the kernel is exclusively through
           one of the three plug points.
      (d)  It has at least one regression test exercising the
           attach -> use -> detach cycle.

   The decision is made by the experimenter; no review is required
   for prototype-to-pack promotion.

5.2  Pack to Kernel candidate

   A pack MAY be promoted to kernel candidate when ALL of the
   following hold:

      (a)  Two independent experiments depend on it.
      (b)  Its interface has been stable across at least one full
           session boundary (no breaking changes to its config
           dataclass or attach signature).
      (c)  Removing it would force every other dependent pack to
           grow to compensate.

   Promotion to kernel candidate is informational; the pack remains
   filed under mpc_packs/ but is flagged in its README as a candidate.

5.3  Kernel candidate to Kernel

   A kernel candidate MAY be promoted to kernel when ALL of the
   following hold:

      (a)  The capability would be required to run the RFC-001
           hello-world demo if the demo were updated to assume it.
      (b)  An RFC-002 revision proposes the promotion and is
           reviewed.
      (c)  The kernel version is incremented (Section 3.1).

   Promotion to kernel is rare and deliberate.  The default answer is
   "stay a pack."

5.4  Default pack manifest

   To avoid the project shipping a kernel-only configuration that is
   unusable in practice, a default pack manifest is maintained
   alongside the kernel.  It lists packs that experiments load unless
   explicitly disabled in their manifest.

   The default manifest is documentation, not code.  An experiment
   that disables a default pack MUST do so explicitly in its
   manifest.

   The default manifest at the date of this RFC is:
      JAXSubstrate
      AutoCluster
      Effector
      Calorimeter

   Adding to or removing from the default manifest requires an
   RFC-002 revision.

5.5  Demotion

   Demotion (kernel to pack, pack to deletion) is permitted but
   requires an RFC-002 revision.  Demoted code is not silently
   removed; it is moved to mpc_packs/deprecated/ for at least one
   revision before deletion, with a note in the README explaining
   why it was demoted and what replaced it (if anything).


6.  Directory Layout (Normative)

   The following directory layout is REQUIRED for any conforming
   implementation of RFC-002.

      mpc_kernel/
         __init__.py
         __version__.py            # kernel semver
         rfc001/
            __init__.py
            phase.py               # Phase enum, classify()
            substrate.py           # Substrate base class
            engine.py              # MetastableEngine
            cluster.py             # MPCCluster
            network.py             # Network
            bus.py                 # EventBus
            events.py              # canonical event types

      mpc_packs/
         __init__.py
         <pack_name>/
            __init__.py
            pack.py                # the pack code
            config.py              # configuration dataclass
            test_pack.py           # regression test
            README.md              # interface, dependencies, status

      experiments/
         __init__.py
         <experiment_name>/
            __init__.py
            run.py                 # experiment driver
            manifest.py            # kernel ver + pack list + config
            report.md              # human-readable result
            artifacts/             # plots, traces
               *.png
               *.json

      docs/
         RFC-001-MPC-BRAIN.md
         RFC-002-MPC-PROJECT-STRUCTURE.md  # this document
         MPC-VISION-001.md                 # historical, advisory
         MPC-ANATOMY-001.svg               # visual reference
         Mechanisms_of_Memory_Persistence.md
         On_the_Physical_Limits_of_Boolean_Algebra...md

   Each pack directory MUST contain at minimum: __init__.py, pack.py,
   config.py, test_pack.py, README.md.

   Each experiment directory MUST contain at minimum: __init__.py,
   run.py, manifest.py, report.md.


7.  Conformance

7.1  Kernel conformance

   A kernel implementation conforms to RFC-002 if and only if:
      (a)  All Section 3.1 MUST clauses hold.
      (b)  It satisfies all RFC-001 invariants.
      (c)  It is filed under mpc_kernel/ per Section 6.
      (d)  It has a __version__ string accessible as
           mpc_kernel.__version__.

7.2  Pack conformance

   A pack implementation conforms to RFC-002 if and only if:
      (a)  All Section 3.2 and Section 4 MUST clauses hold for the
           pack's plug point.
      (b)  It is filed under mpc_packs/<name>/ per Section 6.
      (c)  Its config dataclass declares all dependencies on other
           packs.
      (d)  Its test suite passes against the kernel version
           declared in its config.

7.3  Experiment conformance

   An experiment conforms to RFC-002 if and only if:
      (a)  All Section 3.3 MUST clauses hold.
      (b)  It is filed under experiments/<name>/ per Section 6.
      (c)  Its manifest declares the kernel version and the loaded
           pack manifest.
      (d)  Its run.py executes without modification of any
           mpc_kernel/ or mpc_packs/ file.


8.  Migration from RFC-001 baseline

   The migration is staged.  No step is mandatory before the next
   can begin, but each step compounds the value of the prior one.

   Step 1.  One-time kernel surgery (blocking S5):
      Add the energy field to the canonical PhaseTransitionEvent
      defined in mpc_engine_rfc001.py.  Update MetastableEngine.step
      to populate it.  This eliminates the S4 shadow type and is the
      only kernel modification required by the migration.

   Step 2.  Directory scaffold (one-time, parallel with S5):
      Create mpc_kernel/, mpc_packs/, experiments/ per Section 6.
      Move the kernel components into mpc_kernel/rfc001/.  Existing
      session files retain their old import paths via backward-compat
      shims for one revision; a deprecation notice is added to the
      shim.

   Step 3.  Pack carve-out (per pack, opportunistic):
      For each capability currently embedded in mpc_session2.py,
      mpc_session3.py, mpc_session4.py, file it as a pack under
      mpc_packs/<name>/ with the structure required by Section 6.
      Update affected experiments to import from the pack location.
      Order is not prescribed; carve out packs as they are needed
      by new experiments.

   Step 4.  Session 5 specifically (the first session under RFC-002):
      Rather than a mpc_session5.py monolith, S5 ships as three
      packs (z3_socket, metareasoner, symbolic_forebrain) and one
      experiment (maze).  See SESSION-5-TASK-PROMPT-v3.md.

   Step 5.  Ongoing:
      As biological packs from Appendix A land, they go directly
      into mpc_packs/ and are exercised by new experiments under
      experiments/.  No session adds to the kernel.

   The migration is complete when:
      (a)  No file under mpc_session*.py exists outside of a
           historical/ subdirectory.
      (b)  Every active capability is filed under mpc_kernel/,
           mpc_packs/, or experiments/.
      (c)  An experiment's report consists of methods and results,
           not architectural deltas against prior sessions.


9.  Relationship to RFC-001

   RFC-002 does not modify any normative content of RFC-001.

   RFC-002 specifies how RFC-001-conformant components are organised
   on disk and added over time.  Every kernel under RFC-002 is also
   a conformant implementation of RFC-001.  Every pack under RFC-002
   either uses or extends an interface defined in RFC-001.

   The single point of friction between the two documents is the
   PhaseTransitionEvent canonical form.  Section 8, Step 1 of this
   document modifies the kernel implementation of that event;
   RFC-001's interface specification (§6) is unchanged because §6
   does not enumerate event field counts.


10. Tooling and external interfaces

   This section is non-normative.

   Wrapping packs as Model Context Protocol (MCP) servers via
   fastmcp or equivalent is a question that arises naturally under
   this structure.  The current recommendation is:

   - The MPC inner loop (Substrate <-> Engine <-> Cluster <-> Bus,
     stepping at substrate-step granularity) MUST remain in-process.
     Crossing a process boundary on every step would marshal
     numerical arrays as serialized payloads and erase the JAX
     gradient speedup measured in Session 2.

   - A pack MAY be exposed as an MCP server when it has been used
     by at least one experiment outside the MPC project, OR when it
     has stabilised under the kernel-candidate criteria of
     Section 5.2 and an external use case is proposed.  The MCP
     wrapper is then itself a pack-adjacent artifact under
     mpc_packs/<name>/mcp_server.py, not a replacement for the
     in-process pack.

   - An experiment MAY be exposed as an MCP tool ("run this
     experiment with this manifest") at any time.  This is the
     cleanest external-tool surface and does not introduce
     per-step protocol overhead.

   No conformance requirement turns on the presence or absence of
   MCP wrappers.


11. Reference implementation notes

   This section is non-normative.

   The reference implementation as of this RFC's date is the existing
   codebase at /mnt/project/, comprising mpc_engine_rfc001.py,
   mpc_session2.py, mpc_session3.py, mpc_session4.py, and
   mpc_lattice.py.  The migration plan in Section 8 describes how
   that codebase reaches RFC-002 conformance.

   The first session executed under RFC-002 is Session 5, governed
   by SESSION-5-TASK-PROMPT-v3.md.  Session 5 is also the first
   session that introduces a domain (maze navigation) intended to
   exercise the cognitive-mapping claims of RFC-001.


Appendix A.  Pack roadmap (informational)

   The following packs are proposed under RFC-002, derived from
   Mechanisms_of_Memory_Persistence.md.  Sizes are estimates;
   dependencies are normative once a pack is filed but advisory
   here.  None of these is required for any specific experiment;
   they form a menu, not a queue.

   PNN-Archive                     SubstrateExtension     ~80 LOC
      Snapshots active frustration graph and constraint anchor
      positions.  On removal events, optionally re-instantiates at
      original coordinates.  Implements the persistence-doc
      "structural archive" mechanism.
      Dependencies: none.

   KIBRA-Shield                    SubstrateExtension    ~100 LOC
      Marks high-density-commit regions as protected from decay,
      analogous to liquid-liquid phase-separated KIBRA-PKMzeta
      droplets in the persistence doc.
      Dependencies: DecayingSubstrate.

   PKMzeta-Maintenance             Governor               ~60 LOC
      Constitutive low-level reinforcement for high-usage
      constraints.  Implements the autonomous-kinase analog.
      Dependencies: DecayingSubstrate, Effector.

   SWR-Replay                      Governor              ~150 LOC
      Replays sequences of recent commits during detected idle
      periods.  Implements offline replay during NREM sharp-wave
      ripples.
      Dependencies: Effector, Metareasoner.

   STC-Tagging                     EventSubscriber +     ~120 LOC
                                   Governor
      Synaptic Tagging and Capture: light commits leave tags;
      subsequent salient commits promote tagged constraints from
      transient to persistent.
      Dependencies: Effector.

   ActivitySilent                  SubstrateExtension    ~100 LOC
      Recently committed constraints enter a primed state that
      costs nothing to maintain but biases gradient flow on next
      perturbation.  Working-memory-without-firing analog.
      Dependencies: none.

   EngramReconstruction            Governor              ~200 LOC
      On recall trigger, regenerates a constraint from current
      substrate state plus stored anchors rather than restoring
      verbatim.  Implements the 2025 reconstruction model.
      Dependencies: PNN-Archive, Effector.

   Methylation-Lock                SubstrateExtension     ~50 LOC
      Marks a constraint as removable only through explicit
      demethylation action.  Implements the covalent-lock passive
      boundary.
      Dependencies: none.

   Total: approximately 860 LOC across eight packs to bring the
   persistence-doc biology into the project, with no kernel
   modification.


Appendix B.  Biological correspondences (informational)

   The following table documents the biological-to-MPC mapping
   used as the design intuition behind RFC-002.  It is reference
   material; no conformance requirement depends on it.

      Neuron                          MetastableEngine
      Cortical column / circuit       MPCCluster
      White-matter projection         EventBus
      Extracellular matrix            Substrate
      Sensory transducer              ObservationSocket
      fMRI / EEG / electrode          Calorimeter, Effector,
                                      Metareasoner
      Neuromodulation (DA, ACh, NE)   SymbolicForebrain (Governor)
      Perineuronal net                PNN-Archive (proposed)
      KIBRA-PKMzeta droplet           KIBRA-Shield + PKMzeta-
                                      Maintenance (proposed)
      Sharp-wave ripple replay        SWR-Replay (proposed)
      Synaptic tagging and capture    STC-Tagging (proposed)
      Activity-silent working memory  ActivitySilent (proposed)
      DNA methylation                 Methylation-Lock (proposed)
      Engram reconstruction           EngramReconstruction (proposed)


End of RFC-002-MPC-PROJECT-STRUCTURE.
