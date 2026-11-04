# claude_report_to_avani — code-kt

## State (2026-11-04)
M0 done: repo scaffold, plugin manifest, skill v0 (SKILL.md + references), probe v0, golden_path v0,
examples for click @2247b35 and httpie @5b604c3. Not yet dogfooded end to end (M1).

## Results so far (prototype, not pre-registered)
| Item | click | httpie | Source |
|---|---|---|---|
| Probe time | 1.4 s | 1.2 s | `examples/*/facts/provenance.json` |
| Python LOC | 30,378 | 19,002 | `manifest.json` |
| Call graph | 678 fns / 504 edges | 567 fns / 502 edges | `calls.json` (ast-import-aware) |
| Top core nouns | Command, Context, Path*, Option, Group | Environment, Path*, ExitStatus, FormatterPlugin | `abstractions.json` |
| Golden path | none (library) | main → core.main → raw_main → …, reach 42; stops at callback | `golden_path.json` |

\* `Path` = stdlib name collision (known bug, M2).

## Blockers / doubts
- **Static call graphs miss the main flow at callbacks** (httpie `main_program=program`, core.py:164).
  Reading-based bridging works but depends on the LLM. The runtime trace (M4) is the real fix, and it
  executes code: needs your OK on the opt-in design.
- code2flow crashes on Python 3.13 ASTs; Python now uses stdlib ast. Fine for Python, but JS coverage
  depends on code2flow too. Check its robustness at M3.
- Codebase Mentor's depth is not yet verified; it may be closer than SURVEY §1 says.
- `marketplace.json` schema written from memory; verify against the Claude Code docs at M7.

## Decisions needed
1. Name (`code-kt` vs `code-onboarding`).
2. Paper (M8) or launch-only.
3. Human pilot participants and ethics.
4. Merge L6 "why" with git-archaeology?

## Change log
- 2026-11-04: M0. code2flow → ast for Python; PageRank → reference-count rule for core nouns; real-
  decorator filter for entrypoints; setup.cfg console scripts; greedy chain → outline golden path.
