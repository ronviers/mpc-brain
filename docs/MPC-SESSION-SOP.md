# MPC-SESSION-SOP: Operational Companion to RFC-002 §§12–14

**Status:** Informational. Operational companion to RFC-002-MPC-PROJECT-STRUCTURE, Revision 2.
**Relates to:** RFC-002 §§12 (Session Budget and Scope), 13 (Project Knowledge Base Files), 14 (Session Lifecycle).

---

## 0. Purpose and precedence

This document is the operational companion to RFC-002-MPC-PROJECT-STRUCTURE §§12–14. RFC-002 defines the rules; this document provides the prompt templates, hand-off templates, recovery templates, operational guidance, and worked examples needed to apply those rules in practice. When this document and RFC-002 disagree, RFC-002 wins and this document is to be corrected.

The templates below are literal starting points. Copy them, fill them in, do not silently drop required sections. Anything labelled **MUST** in a template maps to a **MUST** in RFC-002.

---

## 1. Prompt templates by session type

There are five session types (RFC-002 §12.5): development, exploration, interpretation, hand-off, recovery. A separate "experiments-with-runs" budget default exists as a development sub-class; it shares the development template with a different ceiling.

Each template below includes every RFC-002 §14.0 required element. A prompt that omits any labelled block is malformed (§14.0) and Claude is required to request correction before proceeding.

### 1.1 Development template

```markdown
**Session number:** <N>
**Session type:** development
**Governing standard:** RFC-002-MPC-PROJECT-STRUCTURE, Rev. 2

## 0. Orientation — read first, stop at the end of this section

You are starting Session <N>. This is a development session: the work is
<one-sentence statement of what gets built or written>. It is/is not a coding
session.

**Deliverables (<count>):**

1. <path/to/file> — <what it is, in one sentence>
2. <path/to/file> — <what it is, in one sentence>
3. <named artefact, e.g., "cleanup list in final message"> — <what it is>

**Budget ceiling:** <N> tool calls.
**Halt checkpoints:**
- At <N/2> tool calls (50%): stop, count deliverables complete, re-scope.
  Do NOT start a new deliverable that cannot finish in the remaining budget.
- At <0.8·N> tool calls (80%): stop new work. Write the hand-off regardless of state.

**Do not spiral.** <One sentence reminder specific to this session's risk.>

## 1. Context attached to this chat (frontloaded)

Read in this order, once each. Do not re-verify claims in them.

1. **dev_profile.json** — current project state.
2. **<document being modified, if any>** — exception to the normal rule:
   when a deliverable modifies a specific document, that document is frontloaded.
3. **<other required context>**

## 2. Context available on request (backloaded)

Do NOT load these unless a specific decision depends on them.

- <file> — only if <condition>.
- <file> — only if <condition>.

## 3. Task

### 3.1 <Deliverable 1 description>
<Exact specification: what sections, what changes, what invariants.>

### 3.2 <Deliverable 2 description>
<Exact specification.>

### 3.3 <Deliverable 3 description>
<Exact specification.>

## 4. Anti-patterns — do not do these

1. Do not re-verify what the frontloaded docs already claim.
2. Do not ask for confirmation before writing.
3. Do not treat this as a <wrong-kind-of-session> task.
4. Do not expand scope. New sections not in §3 are out of scope.
5. Do not treat "close" as done. 95% is FAIL until the completion signature runs green.
6. If you find yourself writing "next session can quickly finish this..." — stop.

## 5. Hand-off requirements — what your final message MUST contain

1. Deliverables status table (one row per deliverable):
   PASS/FAIL/PARTIAL + completion-signature command.
2. Tool-call count used vs. ceiling.
3. <Additional items specific to this session, e.g., a cleanup list>
4. Deviations from the approved approach, if any, with reasons.
5. Recommendation for Session <N+1>: type and prompt skeleton.

If you halt at the 80% checkpoint without finishing, items 1–5 are still required.

Begin.
```

### 1.2 Experiments-with-runs template

Identical structure to §1.1 with these changes:

- Budget ceiling default is 60 (vs. 40 for single-file development).
- §3 deliverables include a manifest, a run, and at least one artefact path.
- §4 adds one anti-pattern: "Do not re-tune a run that already produced a valid artefact; if the artefact exists at the named path, that deliverable is green."
- §5 adds a required item: "Artefact inventory — one line per artefact produced, with its path under experiments/<name>/artifacts/."

### 1.3 Interpretation template

```markdown
**Session number:** <N>
**Session type:** interpretation
**Governing standard:** RFC-002-MPC-PROJECT-STRUCTURE, Rev. 2

## 0. Orientation

You are starting Session <N>. This is an interpretation session: the work is
producing a written analysis of <specific existing artefacts>. No code changes,
no new experiments, no new packs.

**Deliverables (1):**

1. <path/to/report.md> — <one-sentence description of what it argues>.

**Budget ceiling:** 30 tool calls.
**Halt checkpoints:** 15 (re-scope) / 24 (stop new work).

## 1. Frontloaded context

1. dev_profile.json
2. The artefacts being interpreted: <paths>
3. The RFC(s) whose predictions are being tested: <paths>

## 2. Backloaded context

- Prior session reports — only if a specific claim requires it.
- Foundational papers — only if the analysis reaches their domain.

## 3. Task

Produce <path/to/report.md> containing:
- Summary (one paragraph).
- Evidence reviewed (bullet list of artefact paths with one-sentence
  characterisations each).
- Claims, with inline citation to specific artefacts.
- What this does and does not settle.

## 4. Anti-patterns

1. Do not run new experiments to test interpretations.
2. Do not refactor code in the course of analysis.
3. Do not produce deliverables other than the named report.

## 5. Hand-off requirements

1. Deliverables status table: PASS/FAIL/PARTIAL + completion signature.
2. Tool-call count used vs. 30.
3. Cross-references added or invalidated (for downstream sessions).
4. Recommendation for Session <N+1>.
```

### 1.4 Exploration template

```markdown
**Session number:** <N>
**Session type:** exploration
**Governing standard:** RFC-002-MPC-PROJECT-STRUCTURE, Rev. 2

## 0. Orientation

You are starting Session <N>. This is an exploration session: the work is
investigating <one open question> and producing a single short report.
There is no commitment to downstream work.

**Deliverables (1):**

1. <path/to/short-note.md> — under 500 words, answering a bounded question.

**Budget ceiling:** 20 tool calls.
**Halt checkpoints:** 10 / 16.

## 1. Frontloaded context
1. dev_profile.json
2. The single document or artefact the question relates to: <path>

## 2. Backloaded context
- Everything else, on request.

## 3. Task
Answer the question: "<exact question>".  Produce a short note at the path
above that states:
- The question as posed.
- What was checked.
- A bounded answer (or a clean statement that the question is not yet
  answerable with current artefacts).

## 4. Anti-patterns
1. Do not expand the question.
2. Do not produce more than the one named deliverable.
3. Do not turn exploration into development.

## 5. Hand-off requirements
Same shape as §1.3.
```

### 1.5 Hand-off template (the session type)

A hand-off-type session exists when a prior session produced usable state but no hand-off message (typically because it was interrupted). Its job is to write the hand-off for what was actually produced, not to continue the work.

```markdown
**Session number:** <N>
**Session type:** hand-off
**Governing standard:** RFC-002-MPC-PROJECT-STRUCTURE, Rev. 2

## 0. Orientation

You are starting Session <N>. Session <N-1> was interrupted and did not emit
a hand-off. Your job is to inspect the state Session <N-1> produced and write
the hand-off it owed. You are NOT here to continue Session <N-1>'s work.

**Deliverables (1):**

1. A hand-off message in this chat, shape per §2 of MPC-SESSION-SOP.

**Budget ceiling:** 50 tool calls.
**Halt checkpoints:** 25 / 40.

## 1. Frontloaded context
1. dev_profile.json (current)
2. Session <N-1>'s prompt
3. Whatever files Session <N-1> produced (paths supplied below)

## 2. Backloaded context
- Prior session reports.
- Anything older than Session <N-1>.

## 3. Task
Inspect what Session <N-1> actually produced. For each deliverable it
declared, determine PASS / FAIL / PARTIAL by running its completion
signature. Write the hand-off per the hand-off template (§2 below).

If a deliverable has no runnable completion signature because none was
declared, flag it as NON-CONFORMANT on the deliverable row, treat as FAIL,
and recommend a recovery session.

## 4. Anti-patterns
1. Do not complete unfinished deliverables. That is not your job.
2. Do not re-verify deliverables that are already green.
3. Do not produce a lying hand-off. If something is not green, say so.

## 5. Hand-off requirements
Same shape as §2 below, produced at the end of this session.
```

### 1.6 Recovery template

A recovery session's sole deliverable is a corrected session prompt. It does not execute the failed session's work.

```markdown
**Session number:** <N>
**Session type:** recovery
**Governing standard:** RFC-002-MPC-PROJECT-STRUCTURE, Rev. 2 §12.6

## 0. Orientation

You are starting Session <N>. Session <N-1> did not produce a green hand-off.
You are here to diagnose why and produce a corrected prompt for Session <N+1>.

**You are not here to finish Session <N-1>'s work.** You are here to produce
a prompt whose hand-off will be green when Session <N+1> runs it.

**Deliverables (1):**

1. A corrected session prompt, in this chat, conformant with RFC-002 §14.0.
   Ron will use it verbatim as the prompt for Session <N+1>.

**Budget ceiling:** 50 tool calls.
**Halt checkpoints:** 25 / 40.

## 1. Frontloaded context
1. dev_profile.json (current)
2. Session <N-1>'s prompt
3. Session <N-1>'s hand-off (or the reason it is missing)

## 2. Backloaded context
- Anything older than Session <N-1>, on request.

## 3. Task
Produce the diagnosis and the corrected prompt.

Diagnosis section (in your final message, before the prompt):
- Why Session <N-1>'s hand-off was not green. Be specific; cite the
  deliverable and its failed completion signature.
- Which of the RFC-002 §12 discipline rules, if any, Session <N-1> violated
  (§12.1 unbounded deliverables, §12.2 missing checkpoints, §12.3
  re-verification, §12.4 absent completion signature, §12.5 wrong type,
  §12.7 disallowed fork).
- What changed in the project state since Session <N-1>'s prompt was
  written (stale frontloaded attachments, new dev_profile, etc.).

Corrected prompt:
- Apply the diagnosis: fix deliverable scoping, budget, checkpoints,
  frontload/backload lists, and anti-pattern warnings specific to the
  failure mode you identified.
- Do not copy the failed prompt verbatim. Write a prompt that would
  have succeeded.

## 4. Anti-patterns
1. Do not begin executing the failed work. You are not a development session.
2. Do not fork from Session <N-1>. Recovery is always a fresh session (§12.7).
3. Do not produce a prompt whose deliverables are the same size as Session
   <N-1>'s. If the prior session failed, scope was almost certainly too large.

## 5. Hand-off requirements
1. Diagnosis (one short paragraph).
2. Corrected prompt (a code block; Ron will copy it).
3. Tool-call count used vs. 50.
```

---

## 2. Hand-off template

Every session's closing message MUST contain the following, regardless of outcome. Absence is a §14 violation.

```markdown
## Hand-off — Session <N>

### Deliverables status

| # | Deliverable | Status | Completion signature |
|---|-------------|--------|---------------------|
| 1 | <path or artefact> | PASS / FAIL / PARTIAL | `<runnable command>` |
| 2 | <path or artefact> | PASS / FAIL / PARTIAL | `<runnable command>` |
| 3 | <path or artefact> | PASS / FAIL / PARTIAL | `<runnable command>` |

For any PARTIAL row, list the specific remaining work as a checklist
immediately below the table. Do NOT say "nearly done" or "next session can
quickly finish this."

### Budget

- Tool calls used: <N> / <ceiling>.
- Halt checkpoints hit: <50% yes/no> / <80% yes/no>.

### Files touched this session

- <path> — <created | modified | moved | deleted>
- <path> — <...>

### Anti-pattern flags

- Re-verification (§12.3): <none | list each incident>
- Scope expansion (§12.1): <none | list>
- Malformed prompt accepted (§14.0): <none | describe>
- Fork use (§12.7): <none | describe>

### Pane refresh required (§13.3)

Enumerate which of (1)–(6) in §13.3 need action:
- (1) README.md: <yes / no>
- (2) dev_profile.json: <yes / no>
- (3) RFC-001..004: <none / list which>
- (4) MPC-SESSION-SOP.md: <yes / no>
- (5) Session report rotation: <yes; new is SESSION-<N>-REPORT.md / no>
- (6) Foundational paper: <no change / swap from X to Y>

### Deviations from skeleton or approved approach

<None, or a short list with reasons.>

### Files to be touched next session

- <path> — <why>

### Recommendation for Session <N+1>

Type: <development / experiments-with-runs / interpretation / exploration /
       hand-off / recovery>

Prompt skeleton:

```markdown
<paste the filled template from §1 with deliverables, budget,
frontloaded/backloaded lists, and task specified>
```
```

A hand-off that is missing the deliverables status table, the completion signatures, or the recommendation for the next session is itself malformed and must be treated by the next session as grounds for a recovery session (§12.6).

---

## 3. When to fork (informational)

This section is operational guidance, not normative rule. The normative rules on forking live in RFC-002 §12.7. Read that first; use this for judgment.

### 3.1 Fork is appropriate when:

1. **Before a risky or expensive action you might want to undo.** Large refactor, long simulation run, an architectural commitment. The fork is a safety net: if the risky action goes badly, you return to the parent and try something else with the setup cost already paid.
2. **To A/B test two viable approaches after orientation is complete.** Forking preserves the orientation cost. Running both approaches from scratch pays orientation twice.
3. **To preserve a green hand-off while exploring a variation.** The canonical branch stays clean; the fork carries the speculative work. If the speculation pays off, promote the fork. If it does not, the canonical branch is untouched.

### 3.2 Fork is the wrong tool when:

4. **The parent session is spiraling.** A fork inherits the faulty premises that caused the spiral. The correct response is a fresh recovery session per §12.6. Forking a spiral produces two spirals.
5. **Project state has changed since the fork point.** A new dev_profile, a new RFC, an updated report — these are not present in the fork because the fork froze attachments at fork time. A fresh session with current attachments is correct.
6. **The goal is "try one more turn."** That phrase is a spiral signature. Hand-off and start fresh.

### 3.3 Fork hygiene

7. Name the fork in the first post-fork message: "Exploratory fork to try X. Canonical branch is <timestamp or descriptor>." This prevents confusion later about which branch carries real work.
8. When a fork produces a green hand-off and the parent does not, the fork becomes canonical. Retire the parent. The question "which branch do I keep?" is always answered by "which one is green."
9. If you find yourself wanting to fork a fork, stop. Two levels deep means the cost model is broken. RFC-002 §12.7 prohibits it; this guidance explains why: the probability that a second-level fork produces something better than a fresh session is low, and the confusion cost of maintaining a tree of branches is high.

### 3.4 Worked examples

**Appropriate fork.** Session is an experiments-with-runs session. Orientation (reading the manifest, loading packs, sanity-checking the pack list against RFC-002) is complete at call 18 of 60. The next action is a 1500-step simulation run that could fail partway. Fork before the run. If the run produces usable artefacts, continue in the child. If the run fails, return to the parent and adjust the manifest without having to repeat orientation.

**Inappropriate fork (anti-example).** Session is a development session at call 30 of 40. Work is not converging: the deliverable has been "almost done" for the last eight calls. Claude considers forking "to try finishing this time" with a different approach to the last few edits. This is a §12.6 recovery situation, not a fork situation. The parent is spiraling; forking inherits the spiral. Hand off, mark the deliverable PARTIAL, and Session N+1 is recovery-type.

---

## 4. Project pane maintenance checklist

After every session's hand-off is accepted, Ron runs through this list. Each item maps directly to an RFC-002 §13.3 refresh rule.

- [ ] **(1) README.md.** If the session modified README.md on disk, re-upload it to the project pane. Otherwise skip.
- [ ] **(2) dev_profile.json.** Run the profile regeneration script (see README). Replace the pane copy with the fresh output.
- [ ] **(3) RFC-001 through RFC-004.** If the session produced a new revision of any RFC, re-upload that RFC to the pane. Confirm no older revision remains in the pane.
- [ ] **(4) docs/MPC-SESSION-SOP.md.** If the session modified the SOP on disk, re-upload to the pane.
- [ ] **(5) Session report rotation.** Remove the prior session's report from the pane. Upload this session's report in its place. Confirm exactly one `SESSION-<N>-REPORT.md` is present in the pane.
- [ ] **(6) Foundational paper.** If the hand-off declared a swap (e.g., switching from `Mechanisms_of_Memory_Persistence.md` to a new driving paper), remove the outgoing paper and add the incoming one. Otherwise skip.
- [ ] **Size check.** Confirm total pane size is under 200 KB. If over, the foundational paper is to be replaced with a driving excerpt (§13.1).
- [ ] **Exclusion check.** Confirm pane contains no PNG/JPG/SVG, no historical session scripts, no session prompts, no research notes not driving the current session (§13.2).

The hand-off's "Pane refresh required" block tells Ron which of items (1)–(6) need action. If the hand-off says "pane refresh: none", only the size and exclusion checks are needed.

---

## 5. Worked examples

### 5.1 Worked example: filled-in development prompt (this session)

The prompt that produced this document is itself the exemplar development prompt. Its shape maps to the §1.1 template as follows:

```markdown
**Session number:** 6
**Session type:** development
**Governing standard:** RFC-002-MPC-PROJECT-STRUCTURE (Rev. 1, being revised to Rev. 2 by this session)

## 0. Orientation — read first, stop at the end of this section

You are starting Session 6 of the MPC Brain project. This is a development
session: the work is drafting two documents and moving some files. It is not
a coding session (no kernel changes, no pack changes, no experiments).

**Deliverables (3):**

1. docs/RFC-002-MPC-PROJECT-STRUCTURE.md — revised. Adds §12, §13, §14.
   Absorbs the current SOP. Increments the revision header.
2. docs/MPC-SESSION-SOP.md — new. Operational companion to RFC-002.
   Contains prompt templates for each session type, the hand-off template,
   the recovery template, and two worked examples.
3. A short cleanup list in the final message (not a file): which files Ron
   should `git rm` and which he should move, aligned with the project-pane
   rules defined in §13.

**Budget ceiling:** 50 tool calls.
**Halt checkpoints:**
- At 25 tool calls (50%): stop, count deliverables complete, re-scope.
- At 40 tool calls (80%): stop new work. Write the hand-off regardless of state.

**Do not spiral.** Session 5 consumed a week of tokens because each iteration
was convinced it was "one more session away." The §12 rules being drafted
here exist precisely to prevent this.

## 1. Context attached to this chat (frontloaded)

1. dev_profile.json — current project state.
2. RFC-002-MPC-PROJECT-STRUCTURE.md (current) — being revised; exception
   to the normal frontload rule because this deliverable modifies it.
3. SOP_Session_Hand-Off.md (current) — being absorbed into RFC-002 §14.
4. Workflow discipline and §12/§13/§14 skeleton — embedded in §3 below.

## 2. Context available on request (backloaded)

- RFC-001-MPC-BRAIN.md — only if a §12/§13/§14 clause needs line-check.
- RFC-003, RFC-004 — only if cross-references need checking.
- Prior session reports — only if a worked example needs a concrete
  artefact shape.
- Foundational papers — not needed for this session.

## 3. Task
[Specifications for each of the three deliverables, as in the live prompt.]

## 4. Anti-patterns
[Six anti-patterns, as in the live prompt, including "Do not re-verify",
"Do not ask for confirmation", "Do not treat this as a coding task",
"Do not expand scope", "Do not treat 'close' as done", "If you find
yourself writing 'next session can quickly finish this...' — stop."]

## 5. Hand-off requirements
[Deliverables status table, tool-call count, cleanup list, deviations,
recommendation for Session 7.]
```

### 5.2 Worked example: filled-in hand-off (hypothetical Session 7)

Assume Session 7 is an experiments-with-runs session that activates RFC-004's dynamical track against the maze domain. Ceiling 60, so halt checkpoints at 30 and 48. The session runs a 1200-step demo and produces its artefacts. Hand-off:

```markdown
## Hand-off — Session 7

### Deliverables status

| # | Deliverable | Status | Completion signature |
|---|-------------|--------|---------------------|
| 1 | experiments/dynamical_maze/manifest.py | PASS | `python -c "from experiments.dynamical_maze.manifest import MANIFEST; assert MANIFEST.kernel_version == '0.4.0'"` |
| 2 | experiments/dynamical_maze/run.py | PASS | `python -m experiments.dynamical_maze.run --dry-run` exits 0 |
| 3 | experiments/dynamical_maze/artifacts/trajectories.png | PASS | `test -s experiments/dynamical_maze/artifacts/trajectories.png` |
| 4 | experiments/dynamical_maze/report.md | PARTIAL | `grep -q "^## Final Results" experiments/dynamical_maze/report.md` returns 0, but `grep -q "^## Outstanding Issues" ...` returns 1 (section missing) |
| 5 | Artefact inventory in hand-off | PASS | this table |

#### PARTIAL remaining work (deliverable 4)

- [ ] Add "## Outstanding Issues" section to report.md (one paragraph
      describing the two anomalous trajectories in run 7-c).
- [ ] Append a row to the Final Results table for run 7-c.

### Budget

- Tool calls used: 54 / 60.
- Halt checkpoints hit: 50% yes / 80% yes.
- At 80% checkpoint, deliverable 4 was 90% complete; per §12.2, stopped
  new work and wrote this hand-off. Remaining two bullets above are the
  only outstanding items.

### Files touched this session

- experiments/dynamical_maze/manifest.py — created
- experiments/dynamical_maze/run.py — created
- experiments/dynamical_maze/report.md — created (partial)
- experiments/dynamical_maze/artifacts/trajectories.png — created
- experiments/dynamical_maze/artifacts/energy_trace.json — created

### Anti-pattern flags

- Re-verification (§12.3): none.
- Scope expansion (§12.1): none.
- Malformed prompt accepted (§14.0): none.
- Fork use (§12.7): one appropriate fork, at call 22 of 60, before the
  1200-step run. The run produced usable artefacts and the child became
  canonical; the parent was retired per §3.3 rule 8.

### Pane refresh required (§13.3)

- (1) README.md: no
- (2) dev_profile.json: yes
- (3) RFC-001..004: no
- (4) MPC-SESSION-SOP.md: no
- (5) Session report rotation: yes; new is SESSION-7-REPORT.md; outgoing
      is SESSION-6-REPORT.md (this one drops from the pane; stays on disk
      under experiments/historical/)
- (6) Foundational paper: no change; still RFC-004-driving excerpt.

### Deviations

- Added a fork at call 22 (logged above); this was the first use of the
  §12.7 mechanism and is flagged for potential refinement of the "when to
  fork" operational guidance.

### Files to be touched next session

- experiments/dynamical_maze/report.md — complete the Outstanding Issues
  section and Final Results row 7-c (the two PARTIAL bullets above).

### Recommendation for Session 8

Type: **recovery** (mandatory per §12.6, since deliverable 4 did not
close green).

Prompt skeleton:

```markdown
**Session number:** 8
**Session type:** recovery
**Governing standard:** RFC-002-MPC-PROJECT-STRUCTURE Rev. 2 §12.6

## 0. Orientation
Session 7 halted at the 80% checkpoint with deliverable 4 (report.md) at
90%. Your job: produce a corrected development prompt for Session 9 that
closes the two remaining bullets and nothing else.

**Deliverables (1):**
1. A Session 9 development prompt, in this chat.

**Budget ceiling:** 50 tool calls.
**Halt checkpoints:** 25 / 40.

## 1. Frontloaded context
1. dev_profile.json (current)
2. Session 7's prompt
3. experiments/dynamical_maze/report.md (current partial state)

## 2. Backloaded context
- Session 7's artefacts — only if needed to produce the Outstanding
  Issues paragraph's content.

## 3. Task
Diagnose why deliverable 4 fell to PARTIAL (most likely: the report was
scoped alongside a 1200-step run in a 60-call budget, leaving insufficient
budget for the trailing write-up). Produce a Session 9 prompt whose single
deliverable is completing the two bullets, with a 20-call ceiling.

## 4. Anti-patterns
1. Do not begin completing the report yourself. You are recovery.
2. Do not scope the Session 9 prompt at more than 20 calls.

## 5. Hand-off
Diagnosis + corrected prompt.
```
```

---

## 6. Cross-reference summary

| Rule | RFC-002 § | Template / guidance in this document |
|------|-----------|-------------------------------------|
| Name deliverables | 12.1 | §1 templates, deliverables block |
| Declare ceiling & checkpoints | 12.2 | §1 templates, orientation block |
| Do not re-verify | 12.3 | §1 anti-patterns |
| Completion signature | 12.4 | §2 hand-off template |
| Session type declaration | 12.5 | §1 templates, header |
| Premature termination → recovery | 12.6 | §1.6 recovery template |
| Forking | 12.7 | §3 "When to fork" |
| Pane contents | 13.1–13.2 | §4 maintenance checklist |
| Pane refresh | 13.3 | §2 hand-off, "Pane refresh required" block |
| Phase 0 pre-flight | 14.0 | §1 templates (every block is a §14.0 check) |
| Phases 1–4 | 14.1–14.4 | §2 hand-off "Files touched" + pane refresh |

---

*End of MPC-SESSION-SOP.*
