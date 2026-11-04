# CLAUDE_CODE_BRIEF — code-kt

You are the engineer on **code-kt**, an open-source agent skill for dev-to-dev knowledge transfer.
Avani is research lead and reviews every gate.

**Read in this order before doing anything:**
1. `docs/avani_instructions.md` — standing rules (they override this brief)
2. `docs/CODE_PLAN.md` — architecture, contracts, milestones
3. this brief
4. `docs/PROJECT_PLAN.md` — goals, pre-registered hypotheses, eval, launch
5. `docs/SURVEY.md` — related tools and prototype findings
6. `skills/code-kt/SKILL.md`, `references/kt_protocol.md`, `references/facts_schema.md`

## State at handover (M0 done)

- `skills/code-kt/scripts/probe.py` — 10 probes, stdlib ast + lizard + networkx + git (+ code2flow for
  JS/Ruby/PHP). 1.2–1.9 s on click / httpie.
- `skills/code-kt/scripts/golden_path.py` — outline-style path from the console-script entrypoint.
- `examples/click`, `examples/httpie` — generated facts (commits 2247b35 / 5b604c3).
- Known gaps (SURVEY §4): stdlib name collisions in abstractions; libraries get no golden path;
  callbacks break the path (httpie `main_program`); Python-only imports/abstractions.

## Your next task: M1 → M2

**M1 (protocol only, no code):** run the skill by hand on httpie and click from L1 to L7, saving
transcripts to `examples/<repo>/transcript.md` and exports to `examples/<repo>/ONBOARDING.md`. Edit
`SKILL.md` / `kt_protocol.md` wherever the protocol produced an untagged claim, a too-long level, or a
weak check question. Stop and report at the M1 gate.

**M2 (code), one PR each, in this order:**
1. Probe registry refactor (CODE_PLAN §4.1), output byte-identical on `examples/`.
2. Import-aware class reference counting (§4.5). Expected diff: `Path` leaves the top 3 in both examples.
3. Library golden path from tests (§4.4). Expected: non-empty path for click.
4. `why` snippets for top-3 hotspots into `hotspots.json`.
5. `tests/fixtures/` + unit tests + CI regenerate-and-diff.

## Rules of engagement

- Smallest diff that does the job; no scope creep. Ask before adding a dependency.
- No network or execution in `scripts/probe.py` and `golden_path.py`. Ever.
- Every number you report must point to a file in `examples/` or `eval/results/`.
- Keep `docs/claude_report_to_avani.md` current: state, results vs pre-reg, blockers, decisions needed, change log.
- Add new standing rules to `avani_instructions.md`; don't restate them in chat.
