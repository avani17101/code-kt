#!/usr/bin/env python3
"""code-kt prototype probe: thin glue over off-the-shelf tools -> facts/ for the KT protocol.

Read-only, no network. Each probe is optional: if its tool is missing it records `skipped`.
Usage: python3 -I probe.py <repo_path> [--out <dir>] [--top 15]

Probes (backend tool in brackets):
  manifest     languages, LOC, build/readme files           [stdlib]
  imports      internal module dependency graph             [python ast | ctags later]
  calls        function call graph                          [code2flow json]
  centrality   PageRank over call graph, fan-in fallback    [networkx]
  entrypoints  where execution starts (heuristic rules)     [stdlib + pyproject]
  complexity   cyclomatic complexity per function           [lizard]
  hotspots     churn(last N commits) x max CCN per file      [git]
  risks        TODO/FIXME/HACK/XXX markers                  [stdlib]
  tests_map    test file -> internal modules it imports     [python ast]
Every fact carries `path:line` where one exists, so the LLM can cite it.
"""
import argparse, ast, json, os, re, shutil, subprocess, sys, time
from collections import Counter, defaultdict
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__", ".tox", "site-packages"}
EXT_LANG = {".py": "python", ".js": "javascript", ".ts": "typescript", ".tsx": "typescript", ".go": "go",
            ".rs": "rust", ".java": "java", ".rb": "ruby", ".php": "php", ".c": "c", ".cpp": "cpp", ".cs": "csharp"}
BUILD_FILES = ["pyproject.toml", "setup.py", "setup.cfg", "package.json", "go.mod", "Cargo.toml", "Makefile",
               "Dockerfile", "docker-compose.yml", "tox.ini", "noxfile.py", ".github/workflows"]
RISK_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b[:\s]*(.{0,100})")


def run(cmd, cwd, timeout=300):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def source_files(repo):
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in files:
            p = Path(root, f)
            if p.suffix in EXT_LANG:
                yield p


NON_SRC = re.compile(r"(^|/)(tests?|docs?|examples?|benchmarks?|scripts|extras|tools)/|(^|/)(test_[^/]*|[^/]*_test|conftest)\.py$")


def is_src(repo, p):
    return not NON_SRC.search(rel(repo, p))


def rel(repo, p):
    return str(Path(p).resolve().relative_to(repo))


# ---------------------------------------------------------------- probes
def probe_manifest(repo, files):
    langs, loc = Counter(), Counter()
    for p in files:
        lang = EXT_LANG[p.suffix]
        langs[lang] += 1
        try:
            loc[lang] += sum(1 for _ in p.open(errors="ignore"))
        except OSError:
            pass
    readme = [f for f in os.listdir(repo) if f.lower().startswith("readme")]
    build = [b for b in BUILD_FILES if (repo / b).exists()]
    return {"files_by_language": dict(langs), "loc_by_language": dict(loc), "primary_language":
            loc.most_common(1)[0][0] if loc else None, "readme": readme, "build_files": build}


def module_name(repo, p):
    parts = list(Path(rel(repo, p)).with_suffix("").parts)
    if parts and parts[0] in ("src", "lib"):
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def parse_py(p):
    try:
        return ast.parse(p.read_text(errors="ignore"), filename=str(p))
    except (SyntaxError, ValueError):
        return None


def probe_imports(repo, py_files):
    """Internal import edges between modules of this repo (external libs dropped)."""
    mods = {module_name(repo, p): p for p in py_files}
    edges = []
    for name, p in mods.items():
        tree = parse_py(p)
        if not tree:
            continue
        pkg = name.rsplit(".", 1)[0] if not p.name == "__init__.py" else name
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Import):
                targets = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:  # relative import
                    up = pkg.split(".")[: len(pkg.split(".")) - (node.level - 1)]
                    base = ".".join(up + ([base] if base else []))
                targets = [base] + [f"{base}.{a.name}" for a in node.names]
            for t in targets:
                hit = next((m for m in (t, t.rsplit(".", 1)[0]) if m in mods and m != name), None)
                if hit:
                    edges.append({"src": name, "dst": hit, "at": f"{rel(repo, p)}:{node.lineno}"})
    uniq = {(e["src"], e["dst"]): e for e in edges}
    return {"modules": {m: rel(repo, p) for m, p in mods.items()}, "edges": list(uniq.values())}


def ast_call_graph(repo, py_files):
    """Python call graph from stdlib ast. Resolution order for a call `f(...)` / `x.f(...)` in file F:
    1) def of f in the module F imported f from, 2) def of f in F, 3) unique def of f anywhere in repo.
    Otherwise dropped (ambiguous). Edges carry the call-site line so callers can list calls in source order.
    Still approximate (no type inference for `obj.method()`), flagged so the LLM verifies by reading."""
    mod_file = {module_name(repo, p): rel(repo, p) for p in py_files}
    defs, by_file, trees = defaultdict(list), defaultdict(dict), {}
    for p in py_files:
        t = parse_py(p)
        if not t:
            continue
        trees[p] = t
        for n in ast.walk(t):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                loc = f"{rel(repo, p)}:{n.lineno}"
                defs[n.name].append(loc)
                by_file[rel(repo, p)].setdefault(n.name, loc)
    nodes, edges = {}, {}
    for p, t in trees.items():
        here, name = rel(repo, p), module_name(repo, p)
        pkg = name if p.name == "__init__.py" else name.rsplit(".", 1)[0]
        imported = {}  # local name -> file it came from
        for n in ast.walk(t):
            if isinstance(n, ast.ImportFrom):
                base = n.module or ""
                if n.level:
                    up = pkg.split(".")[: len(pkg.split(".")) - (n.level - 1)]
                    base = ".".join(up + ([base] if base else []))
                for a in n.names:
                    f = mod_file.get(base) or mod_file.get(f"{base}.{a.name}")
                    if f:
                        imported[a.asname or a.name] = f
        for fn in ast.walk(t):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            src = f"{here}:{fn.lineno}"
            nodes[src] = {"name": fn.name}
            for c in ast.walk(fn):
                if not isinstance(c, ast.Call):
                    continue
                f = c.func
                cname = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None
                if not cname:
                    continue
                dst = by_file[imported[cname]].get(cname) if cname in imported else None
                if not dst and isinstance(f, ast.Name):
                    dst = by_file[here].get(cname)
                if not dst and len(defs.get(cname, [])) == 1:
                    dst = defs[cname][0]
                if dst and dst != src and (src, dst) not in edges:
                    edges[(src, dst)] = c.lineno
    for locs_name, locs in defs.items():
        for l in locs:
            nodes.setdefault(l, {"name": locs_name})
    return {"backend": "ast-import-aware", "approximate": True, "nodes": nodes,
            "edges": [{"src": a, "dst": b, "line": ln} for (a, b), ln in sorted(edges.items())]}


def probe_calls(repo, lang, outdir, py_files):
    # Python: stdlib-ast backend by default (code2flow drops cross-module calls and crashes on 3.13 ASTs).
    if lang == "python":
        return ast_call_graph(repo, py_files)
    return probe_code2flow(repo, lang, outdir)


def probe_code2flow(repo, lang, outdir):
    if not shutil.which("code2flow"):
        return {"skipped": "code2flow not installed"}
    c2f_lang = {"python": "py", "javascript": "js", "ruby": "rb", "php": "php"}.get(lang)
    if not c2f_lang:
        return {"skipped": f"code2flow does not support {lang}"}
    out = outdir / "_code2flow.json"
    src = [str(d) for d in (repo / "src", repo) if d.exists()][0]
    r = run(["code2flow", src, "--language", c2f_lang, "-o", str(out), "--quiet",
             "--exclude-namespaces", "tests,test,docs,examples"], cwd=repo)
    if not out.exists():
        return {"skipped": f"code2flow failed: {r.stderr[-300:]}"}
    g = json.loads(out.read_text())["graph"]
    nodes = {k: {"name": v.get("name"), "label": v.get("label")} for k, v in g["nodes"].items()}
    edges = [{"src": e["source"], "dst": e["target"]} for e in g["edges"]]
    out.unlink()
    return {"backend": "code2flow", "approximate": False, "nodes": nodes, "edges": edges}


def probe_centrality(calls, imports, top):
    try:
        import networkx as nx
    except ImportError:
        return {"skipped": "networkx not installed"}
    res = {}
    if calls.get("edges"):
        G = nx.DiGraph([(e["src"], e["dst"]) for e in calls["edges"]])
        pr = nx.pagerank(G)
        res["functions"] = [{"id": k, "name": calls["nodes"].get(k, {}).get("name"), "pagerank": round(v, 4),
                             "fan_in": G.in_degree(k)} for k, v in sorted(pr.items(), key=lambda x: -x[1])[:top]]
    if imports.get("edges"):
        G = nx.DiGraph([(e["src"], e["dst"]) for e in imports["edges"]])
        pr = nx.pagerank(G)
        res["modules"] = [{"module": k, "pagerank": round(v, 4), "imported_by": G.in_degree(k)}
                          for k, v in sorted(pr.items(), key=lambda x: -x[1])[:top]]
    return res


def probe_abstractions(repo, py_files, py_all, top):
    """Core abstractions = classes referenced from many *other* modules (src + tests), weighted by size.
    Rationale: PageRank on import/call graphs surfaces utility sinks; a senior dev names the nouns
    everyone else talks about."""
    import math
    classes = {}
    for p in py_files:
        t = parse_py(p)
        for n in ast.walk(t) if t else []:
            if isinstance(n, ast.ClassDef) and not n.name.startswith("_"):
                end = getattr(n, "end_lineno", n.lineno)
                classes.setdefault(n.name, {"at": f"{rel(repo, p)}:{n.lineno}", "nloc": end - n.lineno + 1,
                                            "bases": [ast.unparse(b) for b in n.bases][:3], "refs": set()})
    for p in py_all:
        t = parse_py(p)
        if not t:
            continue
        here = rel(repo, p)
        for n in ast.walk(t):
            name = n.id if isinstance(n, ast.Name) else n.attr if isinstance(n, ast.Attribute) else None
            if name in classes and not classes[name]["at"].startswith(here + ":"):
                classes[name]["refs"].add(here)
    rows = [{"class": k, "at": v["at"], "bases": v["bases"], "nloc": v["nloc"], "referenced_by_files": len(v["refs"]),
             "score": round(len(v["refs"]) * math.log2(v["nloc"] + 1), 1)} for k, v in classes.items()]
    rows.sort(key=lambda r: -r["score"])
    return {"rule": "distinct referencing files x log2(nloc)", "classes": rows[:top]}


def is_library(repo, facts):
    eps = facts["entrypoints"]["entrypoints"]
    return not any(e["kind"] in ("console_script", "script_main", "module_main") for e in eps)


def probe_entrypoints(repo, py_files):
    eps = []
    pyproject = repo / "pyproject.toml"
    if pyproject.exists():
        try:
            import tomllib
            d = tomllib.loads(pyproject.read_text())
            for k, v in d.get("project", {}).get("scripts", {}).items():
                eps.append({"kind": "console_script", "name": k, "target": v, "at": "pyproject.toml"})
        except Exception as e:  # malformed toml is a fact too
            eps.append({"kind": "error", "detail": f"pyproject parse: {e}"})
    setup_cfg = repo / "setup.cfg"
    if setup_cfg.exists():
        import configparser
        cp = configparser.ConfigParser()
        try:
            cp.read(setup_cfg)
            for line in cp.get("options.entry_points", "console_scripts", fallback="").splitlines():
                if "=" in line:
                    k, v = (x.strip() for x in line.split("=", 1))
                    eps.append({"kind": "console_script", "name": k, "target": v, "at": "setup.cfg"})
        except configparser.Error as e:
            eps.append({"kind": "error", "detail": f"setup.cfg parse: {e}"})
    route_re = re.compile(r"^\s*@\w+\.(route|get|post|put|delete|patch|command|group|task)\b")
    for p in py_files:
        tree = parse_py(p)
        real_deco = {d.lineno for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                     for d in n.decorator_list} if tree else set()
        r = rel(repo, p)
        if "test" in r.lower():
            continue
        if p.name == "__main__.py":
            eps.append({"kind": "module_main", "at": f"{r}:1"})
        for i, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
            if re.match(r"^if __name__ == ['\"]__main__['\"]", line):
                eps.append({"kind": "script_main", "at": f"{r}:{i}"})
            elif route_re.match(line) and i in real_deco:
                eps.append({"kind": "decorated_handler", "decorator": line.strip()[:80], "at": f"{r}:{i}"})
    return {"entrypoints": eps[:200], "count": len(eps)}


def probe_complexity(repo, files, top):
    try:
        import lizard
    except ImportError:
        return {"skipped": "lizard not installed"}
    funcs, per_file = [], {}
    for p in files:
        if "test" in rel(repo, p).lower():
            continue
        try:
            a = lizard.analyze_file(str(p))
        except Exception:
            continue
        r = rel(repo, p)
        per_file[r] = max((f.cyclomatic_complexity for f in a.function_list), default=0)
        funcs += [{"name": f.name, "ccn": f.cyclomatic_complexity, "nloc": f.nloc, "at": f"{r}:{f.start_line}"}
                  for f in a.function_list]
    funcs.sort(key=lambda f: -f["ccn"])
    return {"top_functions": funcs[:top], "max_ccn_per_file": per_file}


def probe_hotspots(repo, complexity, top, n_commits=300):
    if not (repo / ".git").exists():
        return {"skipped": "not a git repo"}
    r = run(["git", "log", f"-n{n_commits}", "--numstat", "--format=%x00%an"], cwd=repo)
    churn, authors = Counter(), defaultdict(Counter)
    author = None
    for line in r.stdout.splitlines():
        if line.startswith("\x00"):
            author = line[1:]
        elif line.strip():
            parts = line.split("\t")
            if len(parts) == 3 and Path(parts[2]).suffix in EXT_LANG:
                churn[parts[2]] += 1
                authors[parts[2]][author] += 1
    ccn = complexity.get("max_ccn_per_file", {})
    rows = [{"file": f, "commits": c, "max_ccn": ccn.get(f, 0), "score": c * max(ccn.get(f, 0), 1),
             "top_authors": [a for a, _ in authors[f].most_common(2)]} for f, c in churn.items() if (repo / f).exists()]
    rows.sort(key=lambda x: -x["score"])
    return {"window_commits": n_commits, "hotspots": rows[:top]}


def probe_risks(repo, files, top):
    hits = []
    for p in files:
        for i, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
            m = RISK_RE.search(line)
            if m and ("#" in line or "//" in line):
                hits.append({"tag": m.group(1), "text": m.group(2).strip(), "at": f"{rel(repo, p)}:{i}"})
    return {"count": len(hits), "markers": hits[: top * 3]}


def probe_tests_map(repo, py_files, imports):
    mods = set(imports.get("modules", {}))
    tmap = {}
    for p in py_files:
        r = rel(repo, p)
        if not re.search(r"(^|/)tests?/|test_|_test\.py$", r):
            continue
        tree = parse_py(p)
        if not tree:
            continue
        used = set()
        for node in ast.walk(tree):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            used |= {n for n in names if n in mods}
        if used:
            tmap[r] = sorted(used)
    return {"tests": tmap}


# ---------------------------------------------------------------- diagram
def mermaid_modules(imports, centrality, k=12):
    keep = {m["module"] for m in centrality.get("modules", [])[:k]}
    lines = ["graph LR"]
    for e in imports.get("edges", []):
        if e["src"] in keep and e["dst"] in keep:
            lines.append(f'  {e["src"].replace(".", "_")}["{e["src"]}"] --> {e["dst"].replace(".", "_")}["{e["dst"]}"]')
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--out", default=None)
    ap.add_argument("--top", type=int, default=15)
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    out = Path(a.out or repo / ".code-kt" / "facts").resolve()
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    files = list(source_files(repo))
    py_all = [p for p in files if p.suffix == ".py"]
    py = [p for p in py_all if is_src(repo, p)]
    src_files = [p for p in files if is_src(repo, p)]
    facts = {"manifest": probe_manifest(repo, files)}
    lang = facts["manifest"]["primary_language"]
    facts["imports"] = probe_imports(repo, py) if py else {"skipped": "no python files"}
    facts["calls"] = probe_calls(repo, lang, out, py)
    facts["centrality"] = probe_centrality(facts["calls"], facts["imports"], a.top)
    facts["entrypoints"] = probe_entrypoints(repo, py)
    facts["abstractions"] = probe_abstractions(repo, py, py_all, a.top)
    facts["entrypoints"]["repo_kind"] = "library" if is_library(repo, facts) else "application"
    facts["complexity"] = probe_complexity(repo, src_files, a.top)
    facts["hotspots"] = probe_hotspots(repo, facts["complexity"], a.top)
    facts["risks"] = probe_risks(repo, src_files, a.top)
    facts["tests_map"] = probe_tests_map(repo, py_all, facts["imports"])
    head = run(["git", "rev-parse", "HEAD"], cwd=repo).stdout.strip() if (repo / ".git").exists() else None
    facts["provenance"] = {"repo": repo.name, "commit": head, "generated_unix": int(t0),
                           "seconds": round(time.time() - t0, 1), "python": sys.version.split()[0],
                           "tools": {t: bool(shutil.which(t)) for t in ("code2flow", "ctags", "git")}}
    for k, v in facts.items():
        (out / f"{k}.json").write_text(json.dumps(v, indent=1))
    (out / "modules.mmd").write_text(mermaid_modules(facts["imports"], facts["centrality"]))
    summary = {k: ("skipped: " + v["skipped"]) if isinstance(v, dict) and "skipped" in v else "ok" for k, v in facts.items()}
    print(json.dumps({"out": str(out), "seconds": facts["provenance"]["seconds"], "probes": summary}, indent=1))


if __name__ == "__main__":
    main()
