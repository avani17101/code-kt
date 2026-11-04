# SURVEY — codebase onboarding / knowledge transfer (Nov 2026)

Reading order: `avani_instructions.md` → `CODE_PLAN.md` → `CLAUDE_CODE_BRIEF.md` → `PROJECT_PLAN.md` → this file.

## 1. Closest existing tools

| Tool | What it does | Static analysis? | Paced / interactive? | Evidence per claim? | Gap vs code-kt |
|---|---|---|---|---|---|
| **CodeBoarding** (OSS, VS Code ext, GitHub Action, MCP) | Control-flow-graph extraction + LLM abstraction → multi-level Mermaid architecture diagrams + component docs | Yes (CFG, LSP) | No — a doc set | Links nodes to files | Architecture docs, not a handover. Closest technically; candidate optional backend. On-by-default telemetry. |
| **GNOST** (pip CLI) | Entry points, execution flow, hotspot files, `ONBOARD.md` + Mermaid | Heuristic, explicitly avoids deep AST | No | No | Shallow; Python-only analysis mode |
| **DeepWiki / deepwiki-open / RepoWiki** | LLM-generated multi-page wiki + RAG chat | Mostly no (embeddings) | Chat, unstructured | Weak | Wiki dump; known to misread complex logic |
| **codebase-onboarding skills** (affaan-m/everything-claude-code; alirezarezvani/claude-skills; sehoon787) | One-pass guide + starter CLAUDE.md via Glob/Grep | No (one variant has a size/stack script) | No — single dump | No (only "could not determine" notes) | "Trace one request" is model-guessed; no graphs, no pacing, no checks |
| **Codebase Mentor** (Claude Code / Codex plugin + MCP) | Mentor / change-guide prompts over a hand-authored or generated ONBOARDING.md | No | Prompt-driven | "Source-backed" | Prompt protocol without a fact layer — **verify depth before launch** |
| Swimm, Sourcegraph (commercial) | Code-coupled docs; code search / navigation | Yes (search index) | No | Yes (links) | Docs maintenance / search, not KT |

**Novelty claim (to defend):** none of these combine (a) a deterministic fact layer from off-the-shelf
analysers, (b) a paced, top-down KT protocol modelled on how engineers hand over code (golden path,
core nouns, landmines, first task) with check questions, and (c) an evaluation. Most have no evaluation.

## 2. Program-comprehension literature the protocol rests on

| Work | Finding | Used for |
|---|---|---|
| Brooks 1983, "Towards a theory of the comprehension of computer programs" | Comprehension is top-down hypothesis refinement, guided by "beacons" | L2 map first, then verify; core nouns as beacons |
| Littman, Pinto, Letovsky & Soloway 1986, "Mental models and software maintenance" | Systematic vs **as-needed** strategies; as-needed is common and cheaper but misses interactions | Lazy, path-only reading + explicit "deeper" |
| von Mayrhauser & Vans 1995, "Program comprehension during software maintenance and evolution" | Integrated model: developers switch between top-down, situation and program models | Level structure + free zoom |
| Sillito, Murphy & De Volder 2006, "Questions programmers ask during software evolution tasks" | Question catalogue: where is X, what calls this, what is impacted by changing Y | L5 recipes and check-question bank |
| Dagenais, Ossher, Bellamy, Robillard & de Vries 2010, ICSE, "Moving into a new software project landscape" | Newcomer orientation relies on early "landmarks" and mentors | Golden path + first task |
| Steinmacher et al. (2015+), barriers for OSS newcomers | Orientation and finding a first task are the top barriers | L7 first task |

Citations from memory; verify exact titles and venues before any paper.

## 3. Off-the-shelf analysers (reuse, don't build)

| Need | Tool | Status in prototype |
|---|---|---|
| Python AST / imports / calls | stdlib `ast` | used — import-aware call resolution |
| Multi-language symbols | universal-ctags, tree-sitter CLI | planned (M3) |
| Call graph JS/Ruby/PHP | code2flow | used; **crashes on Python 3.13 ASTs** (AssertionError), so Python uses `ast` |
| Go / Rust graphs | go-callvis, cargo-modules | planned |
| Complexity | lizard | used |
| Graph metrics | networkx | used |
| History | git | used |
| Runtime path (opt-in) | `python -m trace`, coverage.py contexts, `sys.setprofile` | planned (M4) — fixes dynamic-dispatch gaps |
| Heavy optional backend | CodeBoarding | evaluate in M3 |

## 4. Prototype findings (examples/, click @2247b35, httpie @5b604c3)

1. Probe runtime 1.2–1.9 s on ~20–30 kLOC Python repos, no network.
2. **PageRank is the wrong signal for "core abstractions":** it ranks utility sinks (`flush`, `_compat`).
   Rule "classes referenced from the most other files × log size" returns click's
   `Command, Context, Option, Group, ParamType, Parameter, Argument` — what a maintainer would name.
3. Name-based resolution collides with stdlib names (`Path` in both repos) → needs import-aware
   reference counting (M2).
4. Entry-point regexes hit decorator examples inside docstrings; fixed by keeping only real decorator lines.
5. httpie's console scripts live in `setup.cfg`, not `pyproject.toml` — both needed.
6. **Static graphs lose the main flow at callbacks:** httpie's `raw_main(..., main_program=program)`
   (core.py:164 / :100) hides `program → collect_messages`. The golden path reaches 42 functions and
   stops. The protocol bridges such hops by reading (tagged `[R]`); an opt-in runtime trace is the
   systematic fix.
7. Greedy single-chain paths derail into error handling; an **outline** (top callees by reach, in
   call-site order) matches how a dev narrates a function.
8. Libraries have no application entrypoint (click → empty path). Library golden path must start from
   a representative test calling the public API (M2).
