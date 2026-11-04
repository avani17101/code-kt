# PROJECT_PLAN — code-kt

Reading order: `avani_instructions.md` → `CODE_PLAN.md` → `CLAUDE_CODE_BRIEF.md` → this file → `SURVEY.md`.

## 1. What and why

An open-source agent skill that gives **dev-to-dev knowledge transfer** on any repo: what it is, a
5-box map, one real request traced end to end, the core nouns, how to change X, landmines and why,
and a first task. It is paced one level at a time, with check questions and `path:line` evidence on
every claim. Facts come from off-the-shelf analysers (ast, ctags/tree-sitter, code2flow, lizard, git,
networkx); the LLM narrates and bridges what static analysis cannot see.

Existing tools are wikis or one-shot guides (SURVEY §1). None is paced, evidence-tagged, built on a
deterministic fact layer, and evaluated.

## 2. Users and outcomes

| User | Outcome we promise |
|---|---|
| Engineer joining a team / inheriting a repo | Can explain the golden path and make a first change in one session |
| OSS newcomer | Finds the right files for a first PR without asking maintainers |
| Coding agent (secondary) | `.code-kt/facts` + ONBOARDING.md lower tokens-to-correct-fix |
| Maintainer | Regenerated ONBOARDING.md per release via GitHub Action |

## 3. Pre-registered hypotheses (fill exact numbers at M5 freeze, before full runs)

| ID | Hypothesis | Metric | Direction | Falsifier |
|---|---|---|---|---|
| H1 | Evidence-tagged KT is more accurate than prompt-only onboarding | % of checkable claims verified true against facts + code (auto-checker + 50-claim human audit) | code-kt > baseline B2 by ≥ 15 pp | gap < 5 pp, or code-kt < 90 % |
| H2 | KT transfers understanding | Quiz accuracy (15 Qs/repo: where / how / impact) for a fresh agent given only the KT output | code-kt > B1–B4 | not above B2 by ≥ 10 pp |
| H3 | KT makes first changes cheaper | Tokens and turns to a correct fix on held-out tasks (SWE-bench-style, 5 per repo), agent with KT vs without | ≥ 20 % fewer tokens, equal or better pass rate | no reduction or lower pass rate |
| H4 | Humans prefer paced KT | Small human pilot (n = 6–10, within-subject, 2 repos counterbalanced): quiz + time + preference | code-kt ≥ wiki on quiz, preferred by majority | worse quiz score |

**Baselines:** B0 none; B1 README only; B2 prompt-only "onboard me" (Claude Code, same model);
B3 an existing codebase-onboarding skill (affaan-m); B4 DeepWiki (public repos) or CodeBoarding output.
Same model and temperature for all arms; 3 seeds; report distributions, not single runs.

**Repos (8):** click, httpie, fastapi, TransformerLens, langgraph (Python); express or zod (TS);
cobra (Go); one messy internal-style app (pick at M5). Quiz questions are written from code before any
KT output is seen; Avani reviews them.

## 4. Milestones (part-time, ~8 weeks)

| M | Week | Deliverable | Gate (Avani reviews) |
|---|---|---|---|
| M0 | 0.5 | Repo scaffold, plugin manifest, skill v0, probe v0, examples (done: this commit) | runs on click + httpie |
| M1 | 1 | Dogfood: full L1–L7 tour on httpie and click by hand; fix protocol wording | Avani reads both transcripts; every claim tagged; no untagged guesses |
| M2 | 1.5 | Probe v1 (Python): import-aware class refs, library golden path from tests, `git log` why-snippets, facts schema tests | regenerate-and-diff on both examples; known bugs from SURVEY §4 closed |
| M3 | 1.5 | Multi-language: ctags/tree-sitter symbols + imports for TS/JS and Go; code2flow for JS; optional CodeBoarding backend | probe ok on 1 TS + 1 Go repo in < 30 s |
| M4 | 1 | Opt-in runtime trace backend (one command or one test → real call path, merged into golden path) | bridges httpie `main_program` gap without reading |
| M5 | 1.5 | Eval harness: claim extractor + auto-checker (H1), quiz runner (H2), task runner (H3); pre-registration frozen | pre-reg committed before any full run |
| M6 | 1 | Full eval runs, 8 repos × 5 arms × 3 seeds; human pilot (H4) | results vs pre-reg in `claude_report_to_avani.md` |
| M7 | 0.5 | Launch package: README results table, 60-s GIF, 6 showcase ONBOARDING.md, GitHub Action, ClawHub + `npx skills` + marketplace entries | Avani signs off |
| M8 | opt. | Workshop paper / arXiv (eval as contribution) | — |

## 5. Launch plan

1. Same day: Show HN ("Onboards you to a codebase the way a senior dev would"), r/ClaudeAI,
   r/ChatGPTCoding, X thread with GIF + results table.
2. Distribution: own marketplace (`/plugin marketplace add <owner>/code-kt`), ClawHub
   (`clawhub install code-kt`), `npx skills`, awesome-claude-skills / awesome-claude-code PRs.
3. Week after: PRs adding generated ONBOARDING.md to 2–3 OSS projects that ask for contributor docs.
4. Trust angle (ClawHub had malicious skills): scripts are read-only, no network, < 600 lines, auditable.

## 6. Risks

| Risk | Mitigation |
|---|---|
| "Another onboarding skill" — no attention | Lead with eval table + showcase repos, not features |
| Static analysis misses dynamic flow | `[R]` bridging (now) + runtime trace (M4); report bridge rate as a metric |
| Python-first looks narrow | M3 TS + Go before launch |
| LLM still hallucinates despite tags | H1 auto-checker in CI on examples; untagged-claim lint |
| Running repo code is unsafe | Trace is opt-in, asks first, never in CI on untrusted repos |
| Overlap with git-archaeology idea | Share the commit-mining code: L6 "why" = git-archaeology's core; decide at M2 |

## 7. Decisions needed from Avani

1. Name: `code-kt` (working) vs `code-onboarding` vs other.
2. Venue ambition: launch-only, or M8 paper.
3. Human pilot: who (MBZUAI colleagues?) and whether ethics sign-off is needed.
4. Merge L6 with git-archaeology, or keep separate.
