MPC Working Group                                         Session Notes
Request for Comments: 002                         April 2026 (Rev. 2)
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

   Revision 2 adds normative sections covering session budget and
   scope (§12), the project knowledge base pane (§13), and the
   session lifecycle (§14, which absorbs the prior standalone
   SOP_Session_Hand-Off document).  These sections formalise working
   practices that emerged across Sessions 1 through 5 and codify the
   budget discipline required to prevent multi-session spirals.

   The four-valued state space {c, s, k, r}, the energy invariant of
   RFC-001 §3, and the existing event protocol are unchanged.  This
   is a packaging and process standard, not a redesign.


Status of This Memo

   This document is a Standards Track RFC.  Revision 1 promoted the
   contents of MPC-VISION-001 (advisory) to normative status and
   superseded the implicit "one new file per session" convention
   used through Sessions 1 through 4.  Revision 2 adds §§12–14 and
   retires the standalone SOP_Session_Hand-Off document by
   absorption into §14.

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
   12. Session Budget and Scope (Normative)
       12.1  Deliverable-bounded sessions
       12.2  Hard budget caps
       12.3  No re-verification
       12.4  Completion signature
       12.5  Session types
       12.6  Premature termination protocol
       12.7  Conversation forking
   13. Project Knowledge Base Files (Normative)
       13.1  MUST include
       13.2  MUST NOT include
       13.3  Refresh rule
   14. Session Lifecycle (Normative)
       14.0  Phase 0 — pre-flight
       14.1  Phase 1 — code demotion and archival
       14.2  Phase 2 — pack extraction
       14.3  Phase 3 — experiment containerization
       14.4  Phase 4 — prepare the next session
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

   Revision 2 extends the same discipline to the session process
   itself.  Sessions, like capabilities, accrete cost when
   unbounded.  Section 12 bounds them; Section 13 bounds the
   context supplied to them; Section 14 defines their lifecycle.


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

   Session
      A bounded unit of collaborative work executed within a
      single Claude conversation.  Has a declared type (§12.5), a
      declared budget (§12.2), declared deliverables (§12.1), and
      a lifecycle (§14).  Every session is either an experiment
      (in the Section 3.3 sense) or a process session (development
      of non-experimental artefacts such as RFCs, SOPs, or
      infrastructure).

   Session type
      One of: development, exploration, interpretation, hand-off,
      recovery.  Defined normatively in §12.5.

   Hand-off
      The closing artefact of a session.  A structured message
      (template in docs/MPC-SESSION-SOP.md) enumerating the state
      of every declared deliverable with a completion-signature
      command (§12.4).

   Completion signature
      A deterministic command that, when executed, evaluates
      whether a deliverable is in its green (done) state.  §12.4.

   Tool-call ceiling
      The upper bound on tool invocations a session is permitted
      before it MUST halt.  §12.2.

   Halt checkpoint
      A session-prompt-declared point (at 50% and 80% of ceiling)
      at which the session MUST pause and reassess.  §12.2.

   Fork
      A branch of a conversation created at a prior turn,
      inheriting frozen context from the fork point.  §12.7.

   Project knowledge base
      The set of files present in the Claude Projects pane as
      ambient context for every session.  §13.


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
         RFC-003-MPC-TRACE-FORMAT-001.md
         RFC-004-MPC-DYNAMICAL.md
         MPC-SESSION-SOP.md                # operational companion
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
      (b)  It is filed under mpc_packs/<n>/ per Section 6.
      (c)  Its config dataclass declares all dependencies on other
           packs.
      (d)  Its test suite passes against the kernel version
           declared in its config.

7.3  Experiment conformance

   An experiment conforms to RFC-002 if and only if:
      (a)  All Section 3.3 MUST clauses hold.
      (b)  It is filed under experiments/<n>/ per Section 6.
      (c)  Its manifest declares the kernel version and the loaded
           pack manifest.
      (d)  Its run.py executes without modification of any
           mpc_kernel/ or mpc_packs/ file.


8.  Migration from RFC-001 baseline

   The migration is staged.  No step is mandatory before the next
   can begin, but each step compounds the value of the prior one.

   Step 1.  One-time kernel surgery (blocking S5):
      Add the energy field to the canonical PhaseTransitionEvent
      defined in the legacy mpc_engine_rfc001.py monolith, or
      equivalently in the new mpc_kernel/rfc001/events.py.  Update
      MetastableEngine.step to populate it.  This eliminates the
      S4 shadow type.  As of Revision 2, the energy field is
      present in mpc_kernel/rfc001/events.py.

   Step 2.  Directory scaffold (one-time, parallel with S5):
      Create mpc_kernel/, mpc_packs/, experiments/ per Section 6.
      Move the kernel components into mpc_kernel/rfc001/.  Existing
      session files retain their old import paths via backward-compat
      shims for one revision; a deprecation notice is added to the
      shim.  As of Revision 2, this step is complete; the shims are
      archived under legacy_shims_archived/.

   Step 3.  Pack carve-out (per pack, opportunistic):
      For each capability currently embedded in mpc_session2.py,
      mpc_session3.py, mpc_session4.py, file it as a pack under
      mpc_packs/<n>/ with the structure required by Section 6.
      Update affected experiments to import from the pack location.
      Order is not prescribed; carve out packs as they are needed
      by new experiments.  As of Revision 2, z3_socket,
      metareasoner, symbolic_forebrain, decaying_substrate, and
      persistence_substrate are filed; no further carve-out is
      outstanding.

   Step 4.  Session 5 specifically (the first session under RFC-002):
      Rather than a mpc_session5.py monolith, S5 shipped as three
      packs (z3_socket, metareasoner, symbolic_forebrain) and one
      experiment (maze).  Complete.

   Step 5.  Ongoing:
      As biological packs from Appendix A land, they go directly
      into mpc_packs/ and are exercised by new experiments under
      experiments/.  No session adds to the kernel.

   The migration is complete when ALL of the following hold:
      (a)  No file under mpc_session*.py exists outside of a
           historical/ subdirectory.
      (b)  The legacy monolith mpc_engine_rfc001.py does not exist
           at the repo root.  If retained for historical reference,
           it is filed under experiments/historical/ alongside the
           session monoliths it predated.
      (c)  Every active capability is filed under mpc_kernel/,
           mpc_packs/, or experiments/.
      (d)  The reference implementation referred to by this RFC is
           mpc_kernel/ (§11), not any root-level monolith.
      (e)  An experiment's report consists of methods and results,
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
     mpc_packs/<n>/mcp_server.py, not a replacement for the
     in-process pack.

   - An experiment MAY be exposed as an MCP tool ("run this
     experiment with this manifest") at any time.  This is the
     cleanest external-tool surface and does not introduce
     per-step protocol overhead.

   No conformance requirement turns on the presence or absence of
   MCP wrappers.


11. Reference implementation notes

   This section is non-normative.

   The reference implementation as of Revision 2 is the mpc_kernel/
   package (layout per Section 6; semver per §3.1).  Its __version__
   string is the authoritative statement of which kernel is current.
   Packs under mpc_packs/ and experiments under experiments/ are
   reference pack and reference experiment implementations,
   respectively; they are not themselves "the reference
   implementation."

   The legacy monolith mpc_engine_rfc001.py is NOT the reference
   implementation and MUST NOT be treated as one.  It is retained
   only for backward-reading of historical session scripts and is
   slated for relocation to experiments/historical/ per §8 (b).  New
   code MUST import from mpc_kernel, not from mpc_engine_rfc001.

   The first session executed under RFC-002 was Session 5, which
   introduced the maze-navigation domain and shipped the
   z3_socket, metareasoner, and symbolic_forebrain packs.
   Revision 2 of this RFC is itself a product of Session 6, which
   was a process session (drafting this revision and the companion
   SOP) rather than an experiment.


12. Session Budget and Scope (Normative)

   This section defines the bounds within which a session operates.
   It exists because sessions, like capabilities, accrete cost when
   unbounded.  The rules below are the project's response to the
   Session 5 spiral, in which successive turns each believed the
   work was "one more turn away" from completion for an extended
   period, at non-trivial token cost.

12.1  Deliverable-bounded sessions

   A session MUST enumerate its deliverables as either named file
   paths or explicit named artefacts (such as a hand-off message of
   specified shape).  Phrases of the form "progress on X",
   "exploration of Y", or "work toward Z" are NOT deliverables and
   are NOT permitted in a session prompt's deliverables block.

   Each deliverable is binary: it is either in its green (done)
   state per its completion signature (§12.4), or it is not.  A
   deliverable that is 95 percent complete is FAIL on the hand-off
   table until it is green.

   A session MUST NOT begin work on an undeclared deliverable.  If
   a deliverable not present in the prompt becomes necessary,
   Claude MUST surface it in the hand-off as a recommendation for
   a subsequent session, not silently extend scope.

12.2  Hard budget caps

   A session prompt MUST declare a tool-call ceiling.  The ceiling
   is an upper bound on the number of tool invocations the session
   is permitted to make before it MUST halt and write its hand-off.

   Recommended defaults by session type (§12.5):

      development (single pack or single document)    40 calls
      experiments with runs                           60 calls
      interpretation                                  30 calls
      exploration                                     20 calls
      hand-off                                        50 calls
      recovery                                        50 calls

   A session prompt MAY declare a ceiling other than the default
   for its type, but MUST state the ceiling explicitly.  An
   undeclared ceiling is a malformed prompt (§14.0).

   A session prompt MUST declare halt checkpoints at 50 percent and
   80 percent of its ceiling.

   At the 50 percent checkpoint, the session MUST pause and
   re-scope.  If remaining budget cannot plausibly complete all
   remaining deliverables, the session MUST drop deliverables
   rather than attempt to fit them into insufficient budget.
   Dropped deliverables move to the hand-off as recommendations
   for the next session.

   At the 80 percent checkpoint, the session MUST stop starting
   new work and MUST write its hand-off.  A session that reaches
   80 percent and continues working is in spiral behaviour and is
   non-conformant with this section.

12.3  No re-verification

   A session MUST NOT re-read specifications that a prior hand-off
   claims are verified, unless a named deliverable has produced an
   error whose resolution specifically requires re-checking those
   specifications.

   Silent re-verification — re-reading an RFC or prior report
   because the current session "wants to be sure" — is a budget
   leak and is prohibited.  The frontloaded context (§13) is the
   session's ground truth; if something in it is wrong, the
   correct response is to stop, point to the specific line or
   claim, and flag it in the hand-off — not to re-derive it.

   This rule implies that the integrity of the project knowledge
   base (§13) and the hand-off chain (§14) is load-bearing.  A
   hand-off that claims a deliverable green when it is not
   poisons every subsequent session.  See §12.6.

12.4  Completion signature

   A deliverable is "done" only when the hand-off contains a
   deterministic command that, when executed, produces a green
   result.  Examples of acceptable completion signatures:

      test -f docs/RFC-002-MPC-PROJECT-STRUCTURE.md
      wc -l docs/MPC-SESSION-SOP.md  returns >= 400
      pytest mpc_packs/<n>/test_pack.py  passes
      grep -q "§12" docs/RFC-002-MPC-PROJECT-STRUCTURE.md

   A command that requires human judgment to evaluate ("looks
   good", "seems reasonable") is NOT a completion signature.

   Absence of a completion signature is absence of completion.
   The phrase "no command, no done" is normative.

   For deliverables that are themselves narrative content (a
   report, a hand-off message), the completion signature is
   typically a combination of a file-existence check and a
   content check (word count, section heading grep) sufficient to
   detect a truncated or empty file.

12.5  Session types

   This RFC enumerates exactly five session types.  Every session
   MUST declare exactly one type in its prompt header.

   development
      Produces named code, document, or configuration deliverables
      at specified file paths.  Budget default 40 calls.  In
      scope: writing or editing named files; running tests against
      named files.  Out of scope: open-ended investigation,
      unbounded refactoring, or deliverables expressed as
      "progress on X".

   experiments-with-runs
      A development session whose deliverables include executing
      a workload and producing artefacts (plots, traces, reports).
      Budget default 60 calls.  In scope: manifest construction,
      run execution, artefact generation, report drafting.  Out of
      scope: new kernel or pack work unless explicitly declared.

   interpretation
      Produces a written analysis of existing artefacts or
      results.  Budget default 30 calls.  In scope: reading trace
      data, cross-referencing RFCs, producing a report.  Out of
      scope: running new experiments, modifying code, or expanding
      deliverables beyond those stated.

   exploration
      Produces a short written investigation into an open
      question, with no commitment to downstream work.  Budget
      default 20 calls.  In scope: reading, hypothesis formation,
      a single brief report.  Out of scope: code changes, pack
      creation, or open-ended research across multiple topics.

   hand-off
      A session whose sole deliverable is a hand-off message (§14)
      for a prior session that could not produce one (typically
      because it was interrupted).  Budget default 50 calls.  In
      scope: reading the prior session's produced state, writing
      the hand-off.  Out of scope: continuing or extending the
      prior session's work.

   recovery
      Produces a corrected session prompt that replaces a failed
      prior prompt.  Budget default 50 calls.  See §12.6.  In
      scope: diagnosing why the prior hand-off was not green and
      producing a prompt that will be green.  Out of scope:
      executing the failed session's original work.

   A session prompt MAY propose a type not in the above list, but
   in doing so it is proposing an RFC-002 revision, not a session.

12.6  Premature termination protocol

   When a session terminates before its deliverables are green —
   whether because of budget exhaustion, context window overflow,
   user interruption, loss of connection, or an explicit halt at
   the 80 percent checkpoint — the next session MUST be a
   recovery session (§12.5).

   A recovery session's sole deliverable is a corrected
   development-session prompt that replaces the failed one.  A
   recovery session does NOT execute the failed session's work.

   The purpose of this protocol is to prevent the next development
   session from inheriting a hand-off that falsely claims green
   state.  A recovery session forces explicit diagnosis of why
   the prior hand-off was not green, and produces a prompt whose
   deliverables, budget, and context have been corrected against
   that diagnosis.

   A hand-off that claims green state for a deliverable whose
   completion signature does not run green, when executed, is a
   lying hand-off.  A lying hand-off is a §12.3 violation and
   requires a recovery session even if the next session was
   already planned as something else.

12.7  Conversation forking

   The Claude.ai interface permits forking a conversation at a
   prior turn.  A fork creates a new branch inheriting the parent's
   frontloaded context, frozen at the fork point.  Attached files
   are not refreshed; the fork reads the attachments as they stood
   at fork time.

   Forking is permitted as a checkpoint mechanism within a session.

   A recovery session (§12.6) MUST NOT be performed by forking a
   failed session.  Recovery MUST be a fresh session, with current
   attachments, so that it does not inherit the context that
   produced the failure.

   Forks more than one level deep (a fork-of-a-fork) are
   prohibited.  If a second fork feels necessary, the correct
   response is to start a fresh session rather than fork again.

   A fork inherits the budget state of the parent at fork time.
   The child's halt checkpoints are computed against the same
   ceiling as the parent, not against a fresh ceiling.  A fork
   taken at 30 calls of a 50-call parent has 10 calls remaining
   before its 80 percent checkpoint, not 40.

   Operational guidance on when forking is appropriate versus when
   a fresh session is appropriate is maintained in
   docs/MPC-SESSION-SOP.md (informational).


13. Project Knowledge Base Files (Normative)

   This section governs the contents of the Claude Projects pane —
   the ambient context supplied to every session — not the contents
   of the repository on disk.  The two are distinct.  A file MAY
   exist on disk without being in the project pane, and some files
   (session reports older than the most recent) MUST NOT be in the
   project pane even though they remain on disk under
   experiments/historical/.

   The purpose of this section is to bound the ambient context.
   Unbounded project panes produce three failure modes: (1) session
   prompts become unreadable because their frontloaded context
   swamps the actual task; (2) Claude re-reads stale material in
   violation of §12.3; (3) context-window budget is consumed
   before the session begins.

13.1  MUST include

   The project pane MUST contain exactly the following files:

      docs/RFC-001-MPC-BRAIN.md
      docs/RFC-002-MPC-PROJECT-STRUCTURE.md
      docs/RFC-003-MPC-TRACE-FORMAT-001.md
      docs/RFC-004-MPC-DYNAMICAL.md
      README.md
      dev_profile.json                       (most recent)
      docs/MPC-SESSION-SOP.md
      docs/<foundational-paper>.md           (currently driving development)
      experiments/historical/SESSION-<N>-REPORT.md  (exactly one;
                                             the most recent)

   "The foundational paper currently driving development" is
   whichever of the project's foundational documents (e.g.,
   Mechanisms_of_Memory_Persistence.md,
   v3_On_the_Dynamical_Limits...md, or a successor) is the source
   of the next session's intended work.  At any given time there
   is exactly one such paper.  When the active paper changes, the
   outgoing paper is removed from the pane and the incoming paper
   is added; both are not present simultaneously.

   Target total size: under 200 KB of text.  If the §13.1 set
   exceeds 200 KB, the foundational paper MUST be replaced with a
   short extract (a "driving excerpt") produced by an
   interpretation-type session (§12.5); the full paper remains on
   disk but not in the pane.

13.2  MUST NOT include

   The project pane MUST NOT contain any of the following:

      (a)  Image files (PNG, JPG, SVG).  Visuals are artefacts of
           specific experiments or are reference material for
           specific deliverables; they belong with their experiment
           or are loaded on request per §1/§2 of the session
           prompt.
      (b)  Historical session scripts (mpc_session*.py,
           mpc_engine_rfc001.py).  These live under
           experiments/historical/.
      (c)  Superseded monoliths or superseded RFC revisions.
      (d)  More than one session report.  Only the most recent
           belongs in the pane; older reports are accessed on
           request per §2 of the session prompt.
      (e)  Research notes not driving the current session's
           foundational paper.  Notes such as "effector notes",
           "symbolic forebrain architectural notes", or
           "recursive substrate–limit pairing" are accessed on
           request, not by default.
      (f)  Code files that exist in the repository under
           mpc_kernel/ or mpc_packs/.  Claude loads these from
           disk when needed; they do not belong in the pane.
      (g)  Session prompts themselves, past or present.  The
           current session's prompt is supplied as the user
           message, not as a pane attachment.

13.3  Refresh rule

   The following refresh rule is mechanical and requires no
   judgment calls.  After every session's hand-off is accepted:

      (1)  README.md — refreshed if and only if the session
           modified it on disk.  Update the pane copy in that
           case; otherwise leave.

      (2)  dev_profile.json — regenerated after every session
           that touches files on disk.  The pane copy is replaced
           with the fresh generation.  Script: whatever the
           project provides (see README).

      (3)  RFC-001 through RFC-004 — refreshed if and only if
           the session produced a revision of that RFC.

      (4)  docs/MPC-SESSION-SOP.md — refreshed if and only if
           the session modified it on disk.

      (5)  Session report — the newest
           experiments/historical/SESSION-<N>-REPORT.md replaces
           the prior one.  The prior session's report remains on
           disk under experiments/historical/ but leaves the pane.

      (6)  Foundational paper — changed only when the next
           session's work is grounded in a different foundational
           document than the current one, as declared in the
           session prompt.  Changed by removing the outgoing
           paper from the pane and adding the incoming one; both
           are never present simultaneously.

   Ron is responsible for executing this refresh.  The outgoing
   Claude's hand-off MUST include a "pane refresh" line that
   enumerates which of (1)–(6) above need action after this
   session.  If none do, the hand-off states "pane refresh: none."


14. Session Lifecycle (Normative)

   This section defines the phases of a session from pre-flight
   through hand-off.  It absorbs the content of the prior
   SOP_Session_Hand-Off document; that document is retired by
   this revision and MUST be removed from the repository (see §8
   (b) for similar legacy relocation).

   Operational templates and worked examples for each phase live
   in docs/MPC-SESSION-SOP.md.  That document is informational;
   this section is normative.  When the two disagree, this
   section wins.

14.0  Phase 0 — pre-flight

   Before executing any session work, Claude MUST verify that the
   session prompt declares:

      (a)  A session type (one of §12.5).
      (b)  A tool-call ceiling (§12.2).
      (c)  A list of deliverables as named file paths or named
           artefacts (§12.1).
      (d)  Halt checkpoints at 50 percent and 80 percent of the
           ceiling (§12.2).
      (e)  A frontloaded context list (§13) and a backloaded
           context list.

   A session prompt missing any of (a)–(e) is malformed.  Claude
   MUST NOT begin work on a malformed prompt.  The correct
   response to a malformed prompt is a short message identifying
   what is missing and requesting that Ron supply it.

   A session prompt MAY omit (e) if the frontloaded and
   backloaded lists match exactly the §13.1 defaults; in that
   case the prompt states "frontloaded: §13.1 defaults;
   backloaded: standard" and the session proceeds.

14.1  Phase 1 — code demotion and archival

   Before cataloguing new work, the workspace MUST be cleared of
   legacy or deprecated code.  Silent deletions are prohibited.

      (a)  Archive monolithic scripts.  Any lingering single-file
           session scripts (mpc_session*.py, mpc_engine_rfc001.py)
           MUST be moved into experiments/historical/ if they
           survive the session.
      (b)  Relocate demoted packs.  If a pack was replaced or
           retired during the session, its folder MUST be moved to
           mpc_packs/deprecated/ and MUST remain there for at
           least one RFC-002 revision (§5.5).
      (c)  Update deprecation notes.  A deprecation note MUST be
           added to the README.md of any demoted pack, stating
           the reason and the replacement.

14.2  Phase 2 — pack extraction

   Any inline session code that provided a reusable capability
   MUST be extracted into a standalone pack, subject to the
   prototype-to-pack promotion criteria of §5.1.

      (a)  Identify promotable code.  Locate any prototype code
           that was used end-to-end and interacts with the kernel
           exclusively through one of the three plug points (§4).
      (b)  Create pack directory.  Create a new folder at
           mpc_packs/<pack_name>/.
      (c)  Scaffold required files.  The new directory MUST
           contain exactly: __init__.py, pack.py, config.py
           (with declared dependencies on other packs),
           test_pack.py (exercising attach -> use -> detach),
           README.md (interfaces, dependencies, status).
      (d)  Verify namespace isolation.  The pack MUST define its
           own event types and data structures; it MUST NOT
           modify or shadow kernel types (§3.2, §4.4).

14.3  Phase 3 — experiment containerization

   The session's experiment, if any, MUST be cleanly boxed.

      (a)  Create experiment directory.  Create a new folder at
           experiments/<experiment_name>/.
      (b)  Isolate execution logic.  The session's driver code
           (e.g., a maze generator, a specific test runner) MUST
           be moved into experiments/<experiment_name>/run.py.
      (c)  Generate manifest.  Create
           experiments/<experiment_name>/manifest.py, explicitly
           declaring:
              - the kernel version required;
              - the complete list of packs loaded, with their
                configurations.
      (d)  Write the report.  Draft
           experiments/<experiment_name>/report.md, including:
              - final results table;
              - per-component sections;
              - RFC-001 invariant checklist;
              - list of artefacts generated;
              - outstanding issues and open items.
      (e)  Store artefacts.  All output plots (*.png), traces
           (*.json), and logs MUST be moved into
           experiments/<experiment_name>/artifacts/.

   A process session (one producing RFCs, SOPs, or infrastructure
   rather than an experiment, such as Session 6) omits Phase 3.

14.4  Phase 4 — prepare the next session

   With the previous session cleanly archived and componentized,
   the starting state for the next experiment is initialised.

      (a)  Lock kernel version.  Declare the exact semantic
           version (MAJOR.MINOR.PATCH) of the kernel that will be
           used for the next session.
      (b)  Establish target manifest.  Define the baseline packs
           required.  Unless disabled, this defaults to the
           standard manifest per §5.4 (JAXSubstrate, AutoCluster,
           Effector, Calorimeter).
      (c)  Define the domain or workload.  Document the specific
           task, workload, or problem domain the next session is
           meant to solve before writing new execution code.
      (d)  Emit the pane refresh line.  Per §13.3, enumerate
           which pane files need action after this session.
      (e)  Emit the next session's prompt skeleton.  A hand-off
           MUST include a recommendation for the next session's
           type, budget, and deliverables, in a form Ron can
           copy and flesh out.


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
