# code-kt

I felt like a need for a tool to onboard on any codebase and built one!
Ever felt like a need for a KT-session? Here is a claude skill to try..
It explores the codebase and builds a step by step tutorial to onboard you!


**Knowledge transfer for codebases, the way a senior dev does it.**

Joining a repo? A good handover isn't a wiki. A senior engineer:
- says what the repo is,
- draws five boxes,
- walks one real request through the code,
- names the few things that matter,
- warns you about the traps,
- gives you a small first task.

code-kt is an agent skill that does that: one level at a time, with check questions, and
`path:line` evidence on every claim.

```
You:     onboard me on this repo
Claude:  L1 — httpie is a command-line HTTP client [R README.md:30]. Kind: application [F]. Entry: `http` → httpie.__main__:main [F setup.cfg:77] …
         next / deeper <x> / skip / stop
```

## How it works

1. **Facts, not guesses.** `scripts/probe.py` runs off-the-shelf analysers and writes `.code-kt/facts/`
   in ~2 s. It is read-only, makes no network calls and executes nothing. The analysers are:
   - Python `ast`: imports, an import-aware call graph and class references
   - code2flow (JS/Ruby/PHP)
   - lizard: complexity
   - git: churn, owners
   - networkx
2. **A golden path.** `scripts/golden_path.py` outlines the main branch from the entrypoint, in call order.
3. **A paced protocol.** `SKILL.md` walks seven levels:

   | Level | Covers |
   |---|---|
   | L1 | what & run |
   | L2 | map |
   | L3 | golden path |
   | L4 | core nouns |
   | L5 | how to change X |
   | L6 | landmines & why |
   | L7 | first task |

   Every claim is tagged `[F]` tool fact, `[R]` read, or `[I]` inference. Where static analysis goes
   blind (callbacks, DI), the agent reads the code to bridge the hop and says so.

## Install

```bash
# Claude Code
/plugin marketplace add <owner>/code-kt
/plugin install code-kt@code-kt

# Any agent that reads SKILL.md: copy skills/code-kt into its skills directory
```
Requirements: Python ≥ 3.11, git. Optional: `pip install lizard networkx code2flow`.

## Commands during a tour
- `next`, `skip`, `stop`, `resume`
- `deeper <symbol|file>`
- `quick` (L1–L3 only)
- `export` (writes ONBOARDING.md)

## Examples
`examples/click`, `examples/httpie`: generated facts and golden paths. Full tours coming in v0.2.

## Status
v0.1, Python-first. Planned before v1:
- TS/JS and Go
- an opt-in runtime trace
- an evaluation against prompt-only onboarding, DeepWiki and CodeBoarding

See `docs/PROJECT_PLAN.md`.

## Why not X?
DeepWiki, CodeBoarding and the existing onboarding skills produce documents. code-kt produces
*understanding*: paced, verified, and ending in a first change. See `docs/SURVEY.md`.

MIT licensed.
