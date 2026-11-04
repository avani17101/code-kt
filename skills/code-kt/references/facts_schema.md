# facts/ schema

`probe.py` writes one JSON file per probe into `<repo>/.code-kt/facts/`. A probe whose tool is missing
writes `{"skipped": "<reason>"}`. All locations are `path:line`, relative to the repo root.

| File | Key fields | Backend | Caveats |
|---|---|---|---|
| `manifest.json` | `files_by_language`, `loc_by_language`, `primary_language`, `readme`, `build_files` | stdlib | LOC = raw lines |
| `imports.json` | `modules{module: path}`, `edges[{src, dst, at}]` | Python `ast` | internal imports only; Python only for now |
| `calls.json` | `backend`, `approximate`, `nodes{id: {name}}`, `edges[{src, dst, line}]` | Python: `ast` import-aware; JS/Ruby/PHP: code2flow | no type inference: `obj.method()` resolves only if the name is unique; callbacks/DI invisible |
| `centrality.json` | `modules[{module, pagerank, imported_by}]`, `functions[{id, name, pagerank, fan_in}]` | networkx | PageRank favours utility sinks — use for L2 grouping, **not** for core nouns |
| `abstractions.json` | `classes[{class, at, bases, nloc, referenced_by_files, score}]` | Python `ast` | score = distinct referencing files × log2(nloc); name collisions with stdlib (e.g. `Path`) inflate counts |
| `entrypoints.json` | `repo_kind`, `entrypoints[{kind, name?, target?, at}]` | pyproject, setup.cfg, `__main__`, real decorators | kinds: console_script, module_main, script_main, decorated_handler |
| `complexity.json` | `top_functions[{name, ccn, nloc, at}]`, `max_ccn_per_file` | lizard | source files only |
| `hotspots.json` | `window_commits`, `hotspots[{file, commits, max_ccn, score, top_authors}]` | git | score = commits × max CCN; shallow clones shrink the window |
| `risks.json` | `count`, `markers[{tag, text, at}]` | regex on comments | TODO/FIXME/HACK/XXX |
| `tests_map.json` | `tests{test_file: [modules]}` | Python `ast` | import-level, not coverage |
| `provenance.json` | `commit`, `seconds`, `tools`, `python` | — | cite the commit when you export |
| `modules.mmd` | Mermaid of the top modules' import edges | — | raw material for L2, regroup by role |
| `golden_path.json` | `start`, `outline[{call, def, called_at, reach, then[...]}]` | `golden_path.py` | a reading order, not a proof — verify each hop |

Excluded from source analysis: `tests/ docs/ examples/ benchmarks/ scripts/ extras/ tools/`, `test_*.py`,
`*_test.py`, `conftest.py` (tests still feed `tests_map` and the abstraction reference counts).
