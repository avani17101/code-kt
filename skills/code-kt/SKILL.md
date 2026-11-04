---
name: code-kt
description: Dev-to-dev knowledge transfer for an unfamiliar codebase. Use when someone says "onboard me", "KT me on this repo", "walk me through this codebase", "explain how this repo works", or is taking over / joining a project. Runs read-only static analysis (AST, import and call graphs, complexity, git history) and then gives a paced, top-down tour with file:line evidence, the way a senior engineer hands a codebase over.
---

# code-kt — knowledge transfer the way a senior dev does it

A senior engineer handing over a codebase does not dump a wiki. They say what it is, draw five boxes,
walk one real request through the code, name the few things that matter, warn you about the traps,
and give you a small first task. This skill does exactly that, in that order, one level at a time,
with every claim tied to evidence.

## Hard rules

1. **Evidence on every claim.** Tag each statement:
   - `[F]` fact from `.code-kt/facts/*.json` (tool output) — cite the `path:line` it carries
   - `[R]` you read the code — cite `path:line`
   - `[I]` your inference — say what it rests on
   No untagged claims about the code. If you cannot support it, say "not determined".
2. **Top-down and lazy.** Read only the files on the current level's path. Never scan the whole repo
   by reading files; the probe already did the scan. Use `Grep` for targeted lookups.
3. **One level per turn.** Each level ≤ ~25 lines + at most one diagram, then one check question and
   the menu `next / deeper <thing> / skip / stop`. Wait for the human.
4. **Diagrams come from facts.** Mermaid built from `imports.json`, `calls.json`, `golden_path.json`,
   `abstractions.json`. Never draw an edge you cannot cite.
5. **Read-only.** Scripts never write outside `.code-kt/`, never touch the network, never execute repo
   code. Running the project (tests, a command, a trace) needs the human's explicit yes.
6. **Static analysis is incomplete — say so.** Callbacks, dependency injection, `obj.method()` on
   untyped objects, plugins and decorators break static call graphs. When the golden path stops early
   or jumps oddly, open the last file, find the real next hop by reading, and mark it `[R]`.

## Step 0 — probe (once per repo, ~2 s)

```bash
python3 -I -W ignore <skill_dir>/scripts/probe.py <repo> --out <repo>/.code-kt/facts
python3 -I <skill_dir>/scripts/golden_path.py <repo>/.code-kt/facts > <repo>/.code-kt/facts/golden_path.json
```
`<skill_dir>` is the directory containing this file. Read `references/facts_schema.md` once if you need
field meanings. Check `provenance.json` and every `skipped` entry; tell the human in one line what
backends ran and what is approximate.

Then ask **one** question (skip if already stated): what are you here to do — fix a bug, add a feature
in area X, own the whole thing, or review it? Tailor L5–L7 to the answer.

Persist progress in `<repo>/.code-kt/kt_state.md` (level reached, the human's goal, what they already
know, open questions). On "resume", read it and continue.

## The levels

Full templates and examples: `references/kt_protocol.md`. Read it before L1.

| Level | The senior-dev move | Built from |
|---|---|---|
| L1 What & run | 3 lines: what it is, who uses it, how to run and test it | manifest, build files, README (verify commands exist) |
| L2 Map | 4–7 boxes and the arrows between them | imports + centrality, grouped by package |
| L3 Golden path | one real request/command traced end to end, numbered, `path:line` per hop | golden_path.json, then **read each hop** |
| L4 Core nouns | the 3–6 types everyone talks about: what, who creates it, lifecycle | abstractions.json, then read class bodies |
| L5 How to change X | recipes for the human's goal: files to touch, tests to update | golden path + tests_map, verified by reading |
| L6 Landmines & why | hot + complex files, TODO/HACK, owners, why it is weird (commit messages) | hotspots, complexity, risks, `git log` on hot files |
| L7 First task | the smallest real change on the golden path + how to verify it | all of the above |

**Library vs application** (`entrypoints.json → repo_kind`). For an application, L3 starts at the
console script / main. For a library, the golden path is "what happens when a user calls the main public
API": pick the test in `tests_map.json` that touches the most core nouns and trace from the public
symbol it calls.

## Check questions

End L2–L6 with one question that tests understanding, not recall: "A request with an expired token —
which hop rejects it?", "You need a new CLI flag. Which two files?" Grade the answer in one line; fix
misconceptions before moving on. Record weak spots in `kt_state.md` and revisit them in L7.

## Commands the human can use

- `next` / `skip` / `stop` / `resume`
- `deeper <symbol|file|box>` — zoom into one thing with the same rules (outline → read → cite)
- `quick` — L1–L3 only
- `export` — write `<repo>/ONBOARDING.md`: the levels covered so far + diagrams + evidence tags.
  Ask before writing outside `.code-kt/`.

## What not to do

- No directory-by-directory tour. No dependency lists. No restating the README.
- No architecture claims from folder names alone.
- No "comprehensive overview" in one message. Pace is the product.
