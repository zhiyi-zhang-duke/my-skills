---
name: uml-diagram
description: "Generates feature-rich, interactive UML architecture diagrams as a single self-contained HTML file — C4-style drill-down from system context into containers, components, and classes, plus UML sequence diagrams for key flows, a saved layout (boxes you drag stay put across drill-down, reloads, and rebuilds), clickable detail sidebars, search, and SVG export. Use when the user asks for a UML/architecture/system/component/sequence diagram or codebase map, or wants to visualize how a service, pipeline, or worker fits together."
---

# UML Explorer v2

Turn a codebase (or a slice of one — a service, pipeline, or worker) into an
interactive UML architecture diagram: one self-contained HTML file with drill-down.

Your job is **analysis and modeling, not rendering**. You investigate the code and
author a JSON *architecture model*; the bundled viewer template renders it with
auto-layout, pan/zoom, breadcrumb drill-down, a detail sidebar, search, sequence
diagrams, and SVG export. Do not write custom HTML/JS — all rendering effort goes
through the model.

## Workflow

### 1. Scope the target

Identify what the user pointed at: a whole repo, one directory, or one named
service/pipeline/worker inside a bigger repo. Decide the drill-down levels up front:

- **Top level** — system context: the target as a whole, the humans and schedulers that
  trigger it, external systems it talks to, shared data stores.
- **Second level** — the runnable/deployable pieces inside it (services, workers,
  pipelines, cron jobs, databases, queues).
- **Third level** — components inside the 1–3 most interesting containers only.
- A **class level** (UML class boxes with attributes/methods) only where internals
  genuinely earn it.

If the user pointed at a *specific* pipeline/worker, that thing is the top-level
system and its siblings become `external` context nodes.

### 2. Investigate the code

You are diagramming the **runtime architecture** — processes, triggers, and data flow —
not the folder tree. Folder structure is evidence, not the answer. Hunt for:

- Entrypoints: `main.*`, `cmd/`, `Makefile`, `start.sh`, `Procfile`, `__main__`
- Deployment/config: Dockerfiles, `kubernetes/`, `app.yaml`, `docker-compose`,
  cron manifests, CI configs — these tell you what actually runs, and how many of them
- Boundaries: queue/topic names, HTTP clients and servers, DB connection strings,
  third-party SDK imports, env vars
- READMEs and design docs for intent (verify claims against code — docs drift)

For a large repo, spawn 2–3 Explore subagents in parallel (one per subsystem) and have
each return: runnable units, what triggers them, what they read/write, external calls,
and the key file paths. For a small target, read directly.

### 3. Author the model

Read [references/model-schema.md](references/model-schema.md) for the schema and the
quality bar, then write `model.json` (put it next to the output HTML — see step 4).
The parts that matter most:

- Flat node list, hierarchy via `parent`; 4–9 nodes per view at every level.
- Author edges **leaf-to-leaf**; the viewer rolls them up to whatever level is on
  screen. Never connect a node to its own ancestor.
- Verb-first edge labels ("publishes transcode job"), `kind` distinguishing
  sync/async/data.
- Rich sidebars: `description`, `tech`, `files`, `responsibilities` on every node you
  can — this is the "detail" half of drill-down.
- 2–4 `flows` (sequence diagrams) for the scenarios that best explain the system.

### 4. Build and verify

```bash
python3 <skill-dir>/scripts/build_diagram.py model.json -o <target-name>-architecture.html
```

The script validates (unknown ids, ancestor edges, oversized views, unlabeled edges…)
and injects the model into the viewer template. Fix errors; take warnings seriously —
they encode the quality bar. Default output location: the user's current project
directory (it's their artifact to keep), unless they named a destination.

Verify before delivering — the fastest reliable check is a headless render:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
  --screenshot=/tmp/uml-check.png --window-size=1500,900 --virtual-time-budget=2000 \
  "file://<absolute-path-to-output>.html"
```

Read the screenshot and check: nodes present and non-overlapping, edges labeled,
nothing clipped, no error banner. If Chrome isn't available, `open` the file and ask
the user to eyeball it. Also spot-check a second view by appending `#ctx=<node-id>` to
the URL to screenshot a drilled-in level.

### 5. Deliver

`open` the HTML and tell the user, briefly, how to drive it: click = inspect details,
double-click = drill in, Esc = back up, dashed boxes are context from outside the
current view, Flows tab = sequence diagrams, `/` = search, and the SVG button exports
the current view for docs/slides.

Mention the saved layout, since it is what this version adds: dragging a box pins it,
and the arrangement is stored per drill-down view in the browser's `localStorage`
(keyed by the model title), so it survives drilling in and out, closing the tab, and
rebuilding the file from the same model. **Reset layout ↺** discards the pins for the
current view; shift-clicking it discards every view. Two caveats worth stating once:
the layout lives in that browser profile, not in the HTML file, so it doesn't travel
if they send the file to someone else (export SVG for that), and a rebuild that renames
node ids drops the pins for the renamed nodes.

## Judgment calls that make or break the diagram

- **Abstraction beats completeness.** A top level with 25 boxes has failed even if
  every box is accurate. Group aggressively; the detail still exists one
  double-click down, and search finds anything by name.
- **Don't invent architecture.** If you can't find evidence a connection exists, leave
  it out or mark it in `notes` as unverified. A wrong arrow is worse than a missing one.
- **Name things the way the team does** (queue names, service names from configs), not
  generic labels like "Backend".
- **The sidebar is the payoff for clicking.** A node whose sidebar just restates its
  name wastes the interaction — say what it does, what it's built with, and where the
  code lives.
