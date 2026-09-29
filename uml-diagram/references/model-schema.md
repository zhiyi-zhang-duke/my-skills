# Architecture Model Schema

The viewer renders a single JSON object. Author it as `model.json`, then build with
`scripts/build_diagram.py`. Everything interactive in the viewer (drill-down, sidebar
detail, flows) comes from this one file, so richness here = richness in the diagram.

## Top level

```json
{
  "title": "YouTube Pipelines",
  "subtitle": "optional short tagline",
  "generated": "2026-07-14",
  "nodes": [ ... ],
  "edges": [ ... ],
  "flows": [ ... ]
}
```

## Nodes

A **flat list** — hierarchy is expressed with `parent`, not nesting. Nodes with
`parent: null` (or omitted) are the top-level view. Any node that has children becomes
drillable: the viewer marks it "⊞ N inside — double-click" and renders its children as
the next level down.

```json
{
  "id": "captions-pipeline",              // unique, kebab-case, stable
  "parent": "yt-pipelines",               // null/omitted = top level
  "name": "Captions Pipeline",
  "stereotype": "pipeline",
  "description": "Copies human-reviewed captions from the content DB to YouTube on a nightly schedule.",
  "tech": "Python 3.11, YouTube Data API",
  "files": ["captions/copy_captions.py", "kubernetes/captions-cron.yaml"],
  "responsibilities": [
    "Diff local caption revisions against published YouTube tracks",
    "Upload changed tracks, honoring API quota"
  ],
  "notes": "Optional extra prose shown at the bottom of the sidebar.",
  "class": {                               // ONLY for leaf class/UML-class nodes
    "attributes": ["- quota: QuotaTracker", "- dry_run: bool"],
    "methods": ["+ run() -> Report", "- upload_track(video_id, srt)"]
  }
}
```

Only `id` and `name` are required, but `description`, `tech`, and `files` are what make
the sidebar worth clicking — fill them in for every node you can. `files` are paths
relative to the repo root.

### Stereotypes

The stereotype picks the node's color and icon. Recognized values:

| Group | Values |
|---|---|
| Runtime | `service`, `api`, `worker`, `pipeline`, `job` |
| Data | `database`, `store`, `cache` (cylinder shape), `queue`, `topic` (pipe shape) |
| Edge of system | `external` (gray), `actor` / `person` (person icon) |
| Front ends | `ui`, `web`, `mobile`, `cli` |
| Code-level | `library`, `module`, `component`, `class`, `function`, `config` |
| Grouping | `system` |

Unrecognized stereotypes render as plain components (with a warning from the build
script). Use `external` for anything your target doesn't own (third-party APIs, other
teams' services). Use `actor` for humans.

## Edges

Directed. **Author edges between the most specific nodes you know** (leaf → leaf is
ideal). The viewer automatically "rolls up": when you're looking at the top level, an
edge between two deeply nested components is drawn between their visible ancestors, and
parallel rolled-up edges aggregate into one arrow labeled "⊕ N interactions" that the
reader can click to fan out into the individual labeled edges in place. Drilling in
progressively reveals the specific edges. This is what makes drill-down work — you never
author per-level edges.

Two hard rules (the build script enforces them):
- An edge must not connect a node to its own ancestor/descendant — connect siblings or
  leaves in different subtrees instead.
- Endpoints must exist.

```json
{
  "from": "captions-pipeline",
  "to": "youtube-api",
  "label": "uploads caption tracks",       // verb-first phrase, ~2-5 words
  "kind": "sync",                           // sync | async | data | dependency
  "tech": "HTTPS / YouTube Data API v3",
  "description": "Optional detail shown when the arrow is clicked."
}
```

Kinds: `sync` = solid + filled arrowhead (blocking call); `async` = solid + open
arrowhead (events, queues, fire-and-forget); `data` = dashed + open (reads/writes,
ETL); `dependency` = dashed + open (imports/uses, compile-time).

## Flows (UML sequence diagrams)

Each flow renders as a sequence diagram under the "Flows" tab. Participants are node
ids — any level of the hierarchy is fine (use whichever level tells the story best).

```json
{
  "id": "nightly-caption-sync",
  "name": "Nightly caption sync",
  "description": "What happens when the cron fires at 02:00 UTC.",
  "participants": ["cron", "captions-pipeline", "content-db", "youtube-api"],  // optional explicit order
  "steps": [
    { "from": "cron", "to": "captions-pipeline", "message": "trigger nightly run", "kind": "async" },
    { "from": "captions-pipeline", "to": "content-db", "message": "fetch approved captions", "kind": "sync" },
    { "from": "content-db", "to": "captions-pipeline", "message": "caption revisions", "kind": "return" },
    { "from": "captions-pipeline", "to": "captions-pipeline", "message": "diff vs published state", "kind": "sync" },
    { "from": "captions-pipeline", "to": "youtube-api", "message": "upload changed tracks", "kind": "sync",
      "note": "batched, quota-aware" }
  ]
}
```

Step kinds: `sync` (filled arrow), `async` (open arrow), `return` (dashed, use for
responses). `from == to` renders a self-call loop. `note` adds a small annotation under
the message.

## What makes a good model (quality bar)

- **4–9 nodes per view.** That applies to the top level AND to each container's
  children. More than ~11 anywhere = add an intermediate grouping container. The build
  script warns about this.
- **Levels follow C4 thinking**: top = system context (your system + actors + external
  systems), next = containers (deployable/runnable things: services, workers, pipelines,
  databases, queues), next = components inside one container (modules, key classes).
  2–3 levels is the sweet spot; add a `class`-node level only for the one or two
  components where internals genuinely matter.
- **Every edge labeled with a verb phrase**: "publishes transcode job", "reads video
  metadata" — never "uses" or "connects to".
- **Include the boundary**: human actors, external SaaS/APIs, and data stores are the
  things overview readers look for first. Don't model only the code you can see.
- **Async vs sync matters.** Queue in the middle? The producer edge and consumer edge
  are both `async`. Distinguishing these is half the value of an architecture diagram.
- **2–4 flows**, covering the most illuminating end-to-end scenarios (the happy path of
  the main job; a failure/retry path if it's interesting). Not one flow per endpoint.
- **Ground every leaf in real files** via `files` so a reader can jump from diagram to
  code.
