#!/usr/bin/env python3
"""Validate a uml-diagram architecture model and build the interactive HTML viewer.

Usage:
    python3 build_diagram.py model.json -o output.html [--check]

Exit codes: 0 = built OK (warnings allowed), 1 = validation errors, 2 = bad invocation.
"""
import argparse
import json
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "viewer.html"
DATA_PLACEHOLDER = "/*__DIAGRAM_DATA__*/null"
TITLE_PLACEHOLDER = "__DIAGRAM_TITLE__"

KNOWN_STEREOTYPES = {
    "service", "api", "worker", "pipeline", "job", "database", "store", "cache",
    "queue", "topic", "external", "ui", "web", "mobile", "cli", "library",
    "module", "component", "actor", "person", "class", "function", "config", "system",
}
EDGE_KINDS = {"sync", "async", "data", "dependency"}
STEP_KINDS = {"sync", "async", "return"}


def validate(model):
    errors, warnings = [], []
    if not isinstance(model, dict):
        return ["model root must be a JSON object"], []
    nodes = model.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return ["model.nodes must be a non-empty array"], []
    if not model.get("title"):
        warnings.append("model.title is missing — the viewer header will say 'Architecture'")

    by_id = {}
    for i, n in enumerate(nodes):
        nid = n.get("id")
        if not nid or not isinstance(nid, str):
            errors.append(f"nodes[{i}] is missing a string 'id'")
            continue
        if nid in by_id:
            errors.append(f"duplicate node id '{nid}'")
        by_id[nid] = n
        if not n.get("name"):
            errors.append(f"node '{nid}' is missing 'name'")
        st = (n.get("stereotype") or "component").lower()
        if st not in KNOWN_STEREOTYPES:
            warnings.append(f"node '{nid}' has unrecognized stereotype '{st}' (will render as a plain component)")
        if not n.get("description"):
            warnings.append(f"node '{nid}' has no description — the detail sidebar will be thin")
        cls = n.get("class")
        if cls is not None and not isinstance(cls, dict):
            errors.append(f"node '{nid}': 'class' must be an object with 'attributes'/'methods' arrays")

    # parent chain integrity + cycle check
    for n in nodes:
        nid = n.get("id")
        if not nid:
            continue
        parent = n.get("parent")
        if parent is not None and parent not in by_id:
            errors.append(f"node '{nid}' references unknown parent '{parent}'")
    for n in nodes:
        seen, cur = set(), n.get("id")
        while cur is not None and cur in by_id:
            if cur in seen:
                errors.append(f"parent cycle involving node '{cur}'")
                break
            seen.add(cur)
            cur = by_id[cur].get("parent")

    children = {}
    for n in nodes:
        p = n.get("parent")
        if p:
            children.setdefault(p, []).append(n["id"])
    roots = [n["id"] for n in nodes if n.get("id") and not n.get("parent")]
    if len(roots) > 11:
        warnings.append(
            f"top level has {len(roots)} nodes — diagrams read best with 4–9 per view; "
            "consider grouping related nodes under a parent container"
        )
    for p, kids in children.items():
        if len(kids) > 11:
            warnings.append(
                f"container '{p}' has {len(kids)} children — consider an intermediate grouping level"
            )

    edges = model.get("edges", [])
    for i, e in enumerate(edges):
        f, t = e.get("from"), e.get("to")
        if f not in by_id:
            errors.append(f"edges[{i}] 'from' references unknown node '{f}'")
        if t not in by_id:
            errors.append(f"edges[{i}] 'to' references unknown node '{t}'")
        if f == t:
            warnings.append(f"edges[{i}] is a self-loop on '{f}' — it will not be drawn")
        kind = e.get("kind", "sync")
        if kind not in EDGE_KINDS:
            errors.append(f"edges[{i}] has invalid kind '{kind}' (use one of {sorted(EDGE_KINDS)})")
        if not e.get("label"):
            warnings.append(f"edges[{i}] ({f} → {t}) has no label — label edges with verb phrases")
        # an edge between an ancestor and its own descendant never renders
        if f in by_id and t in by_id:
            for a, b in ((f, t), (t, f)):
                cur = by_id[b].get("parent")
                while cur is not None:
                    if cur == a:
                        errors.append(
                            f"edges[{i}] connects '{a}' to its own descendant '{b}' — "
                            "connect two siblings/leaves instead"
                        )
                        cur = None
                    else:
                        cur = by_id.get(cur, {}).get("parent")

    unconnected = [
        r for r in roots
        if not any(_lift(e.get("from"), by_id, roots) == r or _lift(e.get("to"), by_id, roots) == r
                   for e in edges if e.get("from") in by_id and e.get("to") in by_id)
    ]
    if unconnected and edges:
        warnings.append(f"top-level node(s) with no connections at all: {', '.join(unconnected)}")

    flows = model.get("flows", [])
    fids = set()
    for i, fl in enumerate(flows):
        fid = fl.get("id")
        if not fid:
            errors.append(f"flows[{i}] is missing 'id'")
        elif fid in fids:
            errors.append(f"duplicate flow id '{fid}'")
        fids.add(fid)
        if not fl.get("name"):
            errors.append(f"flows[{i}] is missing 'name'")
        steps = fl.get("steps", [])
        if not steps:
            warnings.append(f"flow '{fid}' has no steps")
        for j, s in enumerate(steps):
            for endpoint in ("from", "to"):
                if s.get(endpoint) not in by_id:
                    errors.append(f"flow '{fid}' step {j+1} '{endpoint}' references unknown node '{s.get(endpoint)}'")
            if s.get("kind", "sync") not in STEP_KINDS:
                errors.append(f"flow '{fid}' step {j+1} has invalid kind '{s.get('kind')}' (use one of {sorted(STEP_KINDS)})")
            if not s.get("message"):
                warnings.append(f"flow '{fid}' step {j+1} has no message")
        for p in fl.get("participants", []):
            if p not in by_id:
                errors.append(f"flow '{fid}' participants references unknown node '{p}'")

    return errors, warnings


def _lift(nid, by_id, roots):
    """Top-level ancestor of a node."""
    cur = nid
    while cur in by_id and by_id[cur].get("parent"):
        cur = by_id[cur]["parent"]
    return cur


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("model", help="path to the architecture model JSON")
    ap.add_argument("-o", "--output", help="output HTML path (default: <model-name>.html)")
    ap.add_argument("--check", action="store_true", help="validate only, do not write HTML")
    args = ap.parse_args()

    model_path = Path(args.model)
    try:
        model = json.loads(model_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: cannot read model: {e}", file=sys.stderr)
        return 2

    errors, warnings = validate(model)
    for w in warnings:
        print(f"WARNING: {w}")
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        print(f"\n{len(errors)} error(s) — fix the model and re-run.", file=sys.stderr)
        return 1

    n_nodes = len(model["nodes"])
    n_edges = len(model.get("edges", []))
    n_flows = len(model.get("flows", []))
    depth = 1
    by_id = {n["id"]: n for n in model["nodes"] if n.get("id")}
    for n in model["nodes"]:
        d, cur = 1, n.get("parent")
        while cur in by_id:
            d += 1
            cur = by_id[cur].get("parent")
        depth = max(depth, d)
    print(f"Model OK: {n_nodes} nodes, {n_edges} edges, {n_flows} flows, {depth} drill-down level(s).")

    if args.check:
        return 0

    template = TEMPLATE.read_text()
    if DATA_PLACEHOLDER not in template:
        print("ERROR: viewer template is missing the data placeholder", file=sys.stderr)
        return 2
    title = model.get("title", "Architecture")
    html = template.replace(DATA_PLACEHOLDER, json.dumps(model, ensure_ascii=False))
    html = html.replace(TITLE_PLACEHOLDER, title)

    out = Path(args.output) if args.output else model_path.with_suffix(".html")
    out.write_text(html)
    print(f"Wrote {out} ({out.stat().st_size // 1024} KB). Open it with: open {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
