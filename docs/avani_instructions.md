# avani_instructions — code-kt

Standing instructions. Add to this file; don't restate in chat. Reading order:
this file → `CODE_PLAN.md` → `CLAUDE_CODE_BRIEF.md` → `PROJECT_PLAN.md` → `SURVEY.md`.

## Relationship
- Avani is research lead / mentor; Claude is the mentee doing engineering + research.
- She deep-dives and guides implementation. Surface design choices before making them when they affect
  what the skill tells a human or what the eval measures.
- Serious, public, open-source work under external scrutiny. Correctness beats speed.

## Engineering
1. Minimal code changes; smallest diff; no scope expansion mid-task.
2. Reuse over reimplementation: off-the-shelf analysers first; glue only.
3. SWE best practice incl. HLD/LLD docs (`CODE_PLAN.md`).
4. Readable code and docs; docstrings state the rule or formula (e.g. golden-path ranking, abstraction score).
5. Review every change; one concern per PR.
6. Maximum transparency in component interaction: probes ↔ facts ↔ skill.

## Architecture
7. Backends are swappable without callers knowing (Probe registry; first available backend wins).
8. Composable: golden path, trace and eval consume facts only, never analyser internals.
9. Clean and extendible: adding a language or backend must not require editing other probes, the
   skill, or the eval.

## Research integrity
10. Verifiable: every number traceable to a file → config → commit. Facts carry provenance.
11. Replicable: refactors behaviour-preserving; prove it by regenerate-and-diff on `examples/`.
12. Validated: pre-register H1–H4 thresholds before any full eval run; report falsifiers; 3 seeds;
    distributions, not anecdotes.

## Reporting
13. `claude_report_to_avani.md` standing report: state, results vs pre-reg, blockers and doubts stated
    very clearly, decisions needed, change log.
14. This file is the standing-instructions file; add to it.
15. Write reasoning down, not just conclusions.

## Specific directions (code-kt)
16. The product is the **protocol**: paced, top-down, one level per turn, check questions. Never trade
    pace for completeness.
17. No untagged claims in any KT output: `[F]` tool fact, `[R]` read, `[I]` inference, each with `path:line`.
18. Scripts are read-only, network-free, and never execute repo code. Runtime tracing is a separate
    opt-in script that asks the human first.
19. Report static-analysis blind spots honestly (bridge rate = % of golden-path hops that needed `[R]`).
20. Eval quiz questions are written from code before looking at any arm's KT output.
21. Same model, temperature and budget for every eval arm; baselines get a fair prompt.
22. Showcase outputs (`examples/`) are regenerated from a pinned commit, never hand-edited.
