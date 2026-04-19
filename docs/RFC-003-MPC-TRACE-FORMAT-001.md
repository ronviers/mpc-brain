MPC Working Group                                         Session Notes
Request for Comments: 003                                  April 2026
Category: Standards Track
Relates to: RFC-001-MPC-BRAIN, RFC-002-MPC-PROJECT-STRUCTURE


         MPC-TRACE-FORMAT: A Wire Format for Experiment Observation


Abstract

   This document defines MPC-TRACE-FORMAT, a JSONL-based wire format
   for observing the state of an MPC experiment as it runs or after
   it has completed.  The format is transport-agnostic: the same
   frames may be written to a file, streamed over a WebSocket, or
   delivered via server-sent events.  Consumers (visualizers,
   analysers, recorders) read frames without knowing which transport
   produced them.

   The format is minimal.  It does not prescribe what to do with the
   data.  It specifies only what is on the wire.


Status of This Memo

   This document is Standards Track under the MPC-BRAIN project.
   It complements RFC-001 (kernel physics) and RFC-002 (project
   structure) by defining the observation surface.  No normative
   content of either RFC is affected.

   Comments and objections are invited in the spirit stated in the
   MPC paper: as tests, not obstacles.


Table of Contents

   1.  Introduction
   2.  Terminology
   3.  Container format
   4.  Frame types
       4.1  meta
       4.2  step
       4.3  event
       4.4  signal
       4.5  action
       4.6  agent
       4.7  end
   5.  Transports
       5.1  File
       5.2  WebSocket
       5.3  Server-sent events
   6.  Producer requirements
   7.  Consumer requirements
   8.  Decimation and sampling
   9.  Versioning
   Appendix A.  Sample trace


1.  Introduction

   An MPC experiment (RFC-002 §3.3) produces substrate-step
   granularity state: engine positions, phases, energies, active
   constraints, bus events, measurement signals, governor actions.
   Visualizers and post-hoc analysers need access to this stream
   without coupling to the experiment's internal data structures.

   MPC-TRACE-FORMAT specifies a neutral wire format for that stream.
   It is deliberately a byte sequence, not a Python object graph,
   so that consumers in other languages or runtimes remain possible.


2.  Terminology

   The key words "MUST", "MUST NOT", "SHOULD", "SHOULD NOT", "MAY"
   are interpreted as in RFC 2119.

   Frame
      One JSON object representing one observation.  Self-contained.

   Producer
      Software that writes frames.  Typically a TraceWriter pack
      attached to an experiment's EventBus.

   Consumer
      Software that reads frames.  Typically a visualizer or
      analyser.

   Transport
      The mechanism by which frames move from producer to consumer.
      File, WebSocket, SSE, or other.


3.  Container format

   The container is JSON Lines (JSONL): one JSON object per line,
   UTF-8 encoded, newline-delimited.  Lines MUST NOT contain
   embedded newlines within their JSON.  Lines MAY be of arbitrary
   length; consumers SHOULD handle lines up to 1 MiB.

   Every frame MUST have the following top-level fields:

      idx         int        monotonic frame index, starts at 0
      t           float      producer time in seconds (substrate or wall)
      kind        string     one of the frame types in §4

   Frame-type-specific payload fields are defined in §4.

   Unknown fields MUST be ignored by consumers (forward compatibility).


4.  Frame types

4.1  meta

   Emitted once, as the first frame (idx=0) of any trace.  Describes
   the experiment configuration so consumers can initialise.

   Fields:
      schema_version   string    MPC-TRACE-FORMAT version ("1")
      kernel_version   string    e.g., "0.4.0"
      experiment       string    e.g., "maze"
      domain           object    domain-specific meta (see below)
      pack_manifest    array     of {name, config} objects
      config           object    experiment configuration snapshot
      started_at       string    ISO-8601 timestamp

   For the maze domain, "domain" contains:
      width            int
      height           int
      walls            array     of [[col_a, row_a], [col_b, row_b]]
      start            [col, row]
      goal             [col, row]
      optimal_path     array     of [col, row]  (A* reference, optional)

   A producer MUST emit exactly one meta frame per trace.  It MUST
   be the first frame.

4.2  step

   Emitted per substrate step, or decimated per §8.  Represents the
   observable state of all engines at one point in substrate time.

   Fields:
      engines          array of objects, each:
         id            string    engine identifier
         cluster_id    string
         phase         string    "c" | "s" | "k" | "r"
         energy        float
         position      array[float]   full position vector
         projection    [x, y]   optional 2D projection for display
      cluster_states   array of objects, each:
         cluster_id    string
         dominant_phase   string
         constraint_count int
         local_budget  float
         n_engines     int

   The projection field is optional.  If absent, consumers render
   from the first two dimensions of position.  For maze experiments,
   the first two dimensions ARE the cell coordinates, so projection
   is naturally (position[0], position[1]).

4.3  event

   Emitted for each event crossing the EventBus.  Type-specific
   payload.

   Fields:
      event_type       string    "PhaseTransition" | "Landauer" |
                                 "BudgetReset" | "Effector" |
                                 "ConstraintRegistered" |
                                 "ConstraintRemoved" | (pack-defined)
      payload          object    event-type-specific

   Canonical event payloads:

   PhaseTransition:
      cluster_id, engine_id, from_phase, to_phase, position, energy

   Landauer:
      cluster_id, engine_id, info_content (bits), cost (kT)

   BudgetReset:
      cluster_id, position

   Effector:
      cluster_id, position, energy_at_c, landauer_cost,
      work_estimate, total_cost

   ConstraintRegistered:
      cluster_id, handle, label, stiffness

   ConstraintRemoved:
      cluster_id, handle, label

   Pack-defined events MAY appear with arbitrary payload shape;
   consumers SHOULD render them as a generic log entry if the
   event_type is unknown.

4.4  signal

   Emitted per plan-interval or decimated per §8.  Represents the
   Metareasoner (or other EventSubscriber) signal snapshot.

   Fields:
      source           string    e.g., "metareasoner"
      cluster_id       string
      signals          object    { signal_name: float, ... }

   All signal values SHOULD be clipped to [0, 1] where applicable.

4.5  action

   Emitted when a Governor (e.g., SymbolicForebrain) executes an
   action.  One frame per action.

   Fields:
      governor         string    e.g., "symbolic_forebrain"
      cluster_id       string
      kind             string    "add_proposition" | "remove_proposition" |
                                 "rebudget" | "noop" | (governor-defined)
      payload          object    kind-specific
      predicate        string    name of the rule that fired, if known

4.6  agent

   Domain-specific frame.  For maze experiments, emitted when the
   agent's current cell changes.

   Fields:
      cell             [col, row]
      reason           string    "commit" | "reset" | "teleport"

   Other domains MAY define their own agent frame shape; consumers
   fall back to ignoring agent frames if the shape is unknown.

4.7  end

   Emitted as the last frame of a trace.  Marks clean completion.

   Fields:
      reason           string    "completed" | "aborted" | "crashed"
      summary          object    experiment-defined summary stats

   Absence of an end frame in a file-based trace means the trace was
   truncated.  Consumers MAY choose to display partial traces.


5.  Transports

5.1  File

   A file transport is a .jsonl file, one frame per line, in frame
   order.  Consumers MAY seek and read in any order; the idx field
   establishes sequence.

   Recommended path under RFC-002:
      experiments/<name>/artifacts/trace.jsonl

5.2  WebSocket

   A WebSocket transport serves the same frames as text messages,
   one frame per message, in order.  The server SHOULD emit an
   initial meta frame to every newly-connected client, replaying
   the initial state even if the experiment is already running.

   Default URL: ws://localhost:8787/trace

   A consumer connects, receives the meta frame, then receives
   subsequent frames as the experiment produces them.  The server
   MAY also accept a query parameter ?replay=1 to send the entire
   trace from idx=0 before switching to live mode.

5.3  Server-sent events

   Alternative to WebSocket.  Each frame is one SSE event with
   data: containing the JSON frame.  Same semantics otherwise.

   Default URL: http://localhost:8787/sse


6.  Producer requirements

   A conforming producer:

   (a)  MUST emit exactly one meta frame as idx=0.
   (b)  MUST increment idx monotonically for every subsequent frame.
   (c)  MUST emit frames in time order (non-decreasing t).
   (d)  SHOULD emit an end frame when the experiment terminates
        cleanly.
   (e)  MAY decimate step and signal frames per §8, but MUST NOT
        decimate event or action frames (these are the ground truth).
   (f)  MUST NOT emit frames whose payload references internal
        Python object identities; all data MUST be serialisable
        scalars, arrays, or nested objects of the same.
   (g)  SHOULD flush after each frame when using file or socket
        transports, so consumers see frames promptly.


7.  Consumer requirements

   A conforming consumer:

   (a)  MUST process frames in idx order.  If a frame arrives with
        idx lower than the last-seen idx, the consumer MAY discard
        it or MAY reset state (for replay scenarios).
   (b)  MUST ignore unknown frame kinds gracefully.
   (c)  MUST ignore unknown fields within known frames.
   (d)  SHOULD render the meta frame's domain-specific data using
        the domain name as a dispatch key.
   (e)  MAY buffer frames and render on a clock independent of
        producer emission rate.


8.  Decimation and sampling

   Step frames at substrate-step granularity produce large traces
   (1500 steps x 2 engines x ~50 bytes = 150 KB per run).  Producers
   MAY reduce this by:

   (a)  Emitting step frames every N substrate steps.  Recommended
        N=10 for maze experiments; N=1 for diagnostic runs.
   (b)  Emitting signal frames only at plan-interval boundaries
        (not every substrate step).
   (c)  Emitting a "step" frame that aggregates N steps into one
        object with an "aggregated": true marker and summary
        statistics.  Consumers SHOULD render aggregated frames as
        a single visual update with no intermediate animation.

   Event and action frames MUST NOT be decimated.  They are the
   canonical record of commitments and governance decisions; losing
   them loses the meaning of the trace.


9.  Versioning

   The schema_version field in the meta frame identifies the format
   version.  This document defines version "1".  Breaking changes
   increment the major version; consumers MUST refuse to process a
   trace whose major version they do not understand.

   Additive changes (new frame types, new optional fields) do not
   change the version.  Consumers MUST ignore unknown kinds and
   fields (§7.b, §7.c).


Appendix A.  Sample trace

   A minimal maze trace (formatted with indentation here for
   readability; actual JSONL has no indentation and one object
   per line):

   {"idx":0,"t":0.0,"kind":"meta","schema_version":"1",
    "kernel_version":"0.4.0","experiment":"maze",
    "domain":{"width":3,"height":3,
              "walls":[[[0,0],[1,0]],[[1,1],[2,1]]],
              "start":[0,0],"goal":[2,2]},
    "pack_manifest":[{"name":"z3_socket","config":{}},
                     {"name":"metareasoner","config":{"window":50}}],
    "config":{"n_steps":1500,"plan_interval":20},
    "started_at":"2026-04-17T19:00:00Z"}

   {"idx":1,"t":0.1,"kind":"step",
    "engines":[{"id":"eng-0","cluster_id":"A","phase":"s",
                "energy":0.42,"position":[0.05,0.03,0.0,0.0],
                "projection":[0.05,0.03]}],
    "cluster_states":[{"cluster_id":"A","dominant_phase":"s",
                       "constraint_count":4,"local_budget":8.0,
                       "n_engines":1}]}

   {"idx":2,"t":0.15,"kind":"event",
    "event_type":"ConstraintRegistered",
    "payload":{"cluster_id":"A","handle":"h-0","label":"cell(0,0)",
               "stiffness":0.4}}

   {"idx":3,"t":2.3,"kind":"event",
    "event_type":"PhaseTransition",
    "payload":{"cluster_id":"A","engine_id":"eng-0",
               "from_phase":"s","to_phase":"c",
               "position":[0.0,0.0,0.0,0.0],"energy":0.38}}

   {"idx":4,"t":2.3,"kind":"event",
    "event_type":"Effector",
    "payload":{"cluster_id":"A","position":[0.0,0.0,0.0,0.0],
               "energy_at_c":0.38,"landauer_cost":0.0,
               "work_estimate":0.1,"total_cost":0.48}}

   {"idx":5,"t":2.3,"kind":"agent","cell":[0,0],"reason":"commit"}

   {"idx":6,"t":2.4,"kind":"signal","source":"metareasoner",
    "cluster_id":"A",
    "signals":{"under_budget":0.0,"distant_start":0.01,
               "exploration_saturation":1.0,"thermal_pressure":0.0,
               "idle":0.0}}

   {"idx":7,"t":2.5,"kind":"action","governor":"symbolic_forebrain",
    "cluster_id":"A","kind":"add_proposition",
    "payload":{"label":"cell(1,0)","strength":0.4},
    "predicate":"exploration_saturated"}

   {"idx":8,"t":15.0,"kind":"end","reason":"completed",
    "summary":{"commits":9,"cells_visited":5,"goal_reached":false}}


End of MPC-TRACE-FORMAT-001.
