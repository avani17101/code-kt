#!/usr/bin/env python3
"""Pick the 'one request end to end' path a senior dev would walk, from facts/ only.

Rule: start at the first console_script target. Under each function keep the --width callees that reach
the most distinct functions (main branches, not error/log side branches; tie-break hotspot rank, then
core-abstraction files), list them in call-site order, recurse to --depth. Stop at depth --max or when no unvisited in-repo callee remains.
The path is a *reading order*; the LLM must open each file:line on it and verify before narrating.
Usage: python3 -I golden_path.py <facts_dir> [--depth 4] [--width 3]
"""
import argparse, json
from collections import defaultdict
from pathlib import Path


def load(d, k):
    p = Path(d, f"{k}.json")
    return json.loads(p.read_text()) if p.exists() else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("facts")
    ap.add_argument("--depth", type=int, default=4)
    ap.add_argument("--width", type=int, default=3)
    a = ap.parse_args()
    calls, eps = load(a.facts, "calls"), load(a.facts, "entrypoints")
    hot = {h["file"]: i for i, h in enumerate(load(a.facts, "hotspots").get("hotspots", []))}
    core_files = {c["at"].split(":")[0] for c in load(a.facts, "abstractions").get("classes", [])[:8]}
    nodes, out = calls.get("nodes", {}), defaultdict(list)
    for e in calls.get("edges", []):
        out[e["src"]].append(e["dst"])

    def file_of(n):  # code2flow ids are opaque; ast backend ids are path:line
        lab = nodes.get(n, {}).get("label") or n
        return lab.split(":")[0]

    start = None
    for ep in eps.get("entrypoints", []):
        if ep["kind"] == "console_script":
            mod, fn = ep["target"].split(":")
            want = mod.replace(".", "/")
            start = next((k for k, v in nodes.items() if v.get("name", "").split(".")[-1] == fn
                          and k.startswith(want + ".py:")), None)
            if not start:  # code2flow names look like '__main__::main'
                start = next((k for k, v in nodes.items() if str(v.get("name", "")).endswith(f"::{fn}")
                              and mod.split(".")[-1] in str(v.get("name"))), None)
            if start:
                break
    if not start:
        print(json.dumps({"path": [], "reason": "no resolvable application entrypoint (library?)"}))
        return

    reach_cache = {}

    def reach(n, cap=2000):  # distinct functions reachable from n (bounded BFS)
        if n not in reach_cache:
            seen_r, stack = {n}, [n]
            while stack and len(seen_r) < cap:
                for c in out.get(stack.pop(), []):
                    if c not in seen_r:
                        seen_r.add(c)
                        stack.append(c)
            reach_cache[n] = len(seen_r)
        return reach_cache[n]

    def rank(n):
        f = file_of(n)
        return (-reach(n), hot.get(f, 99), 0 if f in core_files else 1)

    line_of = {(e["src"], e["dst"]): e.get("line", 0) for e in calls.get("edges", [])}
    seen = {start}

    def outline(n, depth):
        """Top-`--width` callees by reach, shown in call-site order: how a dev narrates a function."""
        if depth >= a.depth:
            return []
        kids = sorted((c for c in out.get(n, []) if c not in seen), key=rank)[: a.width]
        kids.sort(key=lambda c: line_of.get((n, c), 0))
        seen.update(kids)
        return [{"call": nodes.get(c, {}).get("name"), "def": c, "called_at": f"{n.split(':')[0]}:{line_of.get((n, c))}",
                 "reach": reach(c), "then": outline(c, depth + 1)} for c in kids]

    print(json.dumps({"backend": calls.get("backend"), "approximate": calls.get("approximate"),
                      "start": {"name": nodes.get(start, {}).get("name"), "def": start, "reach": reach(start)},
                      "outline": outline(start, 0)}, indent=1))


if __name__ == "__main__":
    main()
