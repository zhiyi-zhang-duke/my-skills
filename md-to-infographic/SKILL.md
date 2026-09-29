---
name: md-to-infographic
description: "Convert one or more Markdown files into a visual, dark-mode HTML infographic at the same location as the source file. Use this skill whenever the user wants a Markdown file turned into a visual page, an infographic, a \"pretty version\", an HTML render with stat cards / severity badges / diagrams, or asks to \"visualize\", \"make this look nice\", \"make a webpage from this doc\", or \"render this as HTML\". Trigger even if they don't say \"infographic\" — phrases like \"make a visual version of research.md\" or \"html-ify these notes\" should match. Do NOT use for general Markdown→HTML conversion where the user wants a plain document render (use a normal converter); this skill specifically produces an opinionated dark-mode infographic with a TL;DR pinned at the top."
---

# md-to-infographic

Turn Markdown files into self-contained, dark-mode HTML infographics. The output is a single `.html` file written next to the source `.md`, with no external dependencies.

## When you're invoked

The user will give you one or more paths to Markdown files. Convert each one into an infographic-style HTML file at the same location, replacing `.md` with `.html`. Examples of how the user might phrase this:

- "Make an html version of research.md"
- "Visualize these: notes/q1.md notes/q2.md"
- "Turn this into a dark-mode infographic: docs/findings.md"
- "/md-to-infographic foo.md bar.md"

If the user passes multiple files, treat them independently — generate one HTML per Markdown. Don't merge them.

## Hard requirements

These are non-negotiable because they are the user's stated preferences:

1. **TL;DR / bottom line at the top.** Find the summary, conclusion, or "one-liner" in the source Markdown and surface it as a prominent card right under the hero. If there is no explicit summary, synthesize a 1–2 sentence version from the doc's main thesis. The user wants the punchline first, details after.
2. **Output goes next to the input.** `path/to/file.md` → `path/to/file.html`. Same directory, same basename, `.html` extension. Overwrite silently if it already exists — this is a regenerated artifact.
3. **Dark mode only.** Don't add a light/dark toggle. The whole page is dark-themed. The palette is fixed (see below) so multiple generated infographics look like a coherent set.
4. **Self-contained.** All CSS is inline in a `<style>` block in the `<head>`. No external stylesheets, no CDN fonts, no JavaScript libraries. The file must work offline and render correctly when opened with `file://`.
5. **Infographic style, not a plain doc render.** This is the whole point. If you find yourself just wrapping `<p>` tags around paragraphs, stop and reread the "Visual patterns" section.

## Workflow

1. **Read the source Markdown end-to-end.** Don't skim. You need to understand the structure to design the infographic well.
2. **Identify the bottom line.** Look for an explicit TL;DR/summary/conclusion section. If absent, synthesize one. Save it for the top card.
3. **Identify visual hooks.** Skim for things that turn into infographic elements:
   - Numeric stats → stat cards
   - Severity-rated items (high/medium/low, critical/warn/info) → color-coded issue cards
   - Lists of file:line references → clickable code-ref pills
   - "X then Y then Z" sequences → flow diagrams
   - Pros/cons or do/don't lists → two-column grids
   - Step-by-step instructions → numbered keypaths
4. **Pick a structure.** Sections become numbered chapters in the output (`01`, `02`, etc.). Aim for 4–7 sections; collapse trivial ones.
5. **Open the template.** Read `assets/template.html` — it has the full CSS and component examples. Use it as your starting point and adapt content into its components. Don't reinvent the styling.
6. **Write the HTML to the target path.** Same directory as the source `.md`.
7. **Report back briefly.** State the output path(s) and a one-liner about what visual treatment you chose. Don't dump the HTML into chat.

## Visual patterns to use

Read `assets/template.html` for the full CSS and example markup of each pattern. Pick the patterns that match the source content; don't force-fit. A doc about a single decision doesn't need a fan-out diagram, and a prose-heavy spec might just need stat cards and section headers.

| Pattern | Use when source has |
|---|---|
| **TL;DR card** | Always — it's the top-pinned summary |
| **Stat grid** | Numbers worth highlighting (counts, percentages, durations) |
| **Severity issue cards** | Items rated high/medium/low or similar |
| **Code-ref pills** | `path:line` or `[file](./path#L12)` references — make them clickable |
| **Flow diagram** | Sequential pipeline / fan-out (`A → ×N → B → ×M → C`) |
| **Keypath list** | Ordered steps where each step has a code reference |
| **Two-column grid** | Pros/cons, do/don't, "what's wrong" / "what's not wrong" |
| **Plain section** | Prose that doesn't fit any of the above — still wrap in a card, don't leave it floating |

## Why these rules exist

- **Dark mode only:** The user explicitly asked for this. Adding a toggle wastes tokens and adds JS that breaks the "self-contained, no JS" property.
- **Same-location output:** Keeps the source/render pair together. Easy to find, easy to diff, easy to commit alongside.
- **TL;DR at top:** The user reads the punchline first. If the source Markdown buries the conclusion (which is common in research notes), the infographic shouldn't.
- **Inline CSS:** A single file you can email, attach, drop in a wiki, or open from a USB stick. No "asset 404" risk.
- **Opinionated styling:** When several infographics get generated over time, they should look like a series. A locked palette makes that automatic.

## Preserve source labels

When the source uses explicit labels for ordered items (`Week 1`, `Week 2`, `Phase 1`, `Step 1`, action item owners like `Jack` / `Priya`, severity words `High` / `Medium` / `Low`), keep that text in the rendered output. Visual decorations (colored badges, numbered counters, icons) are additive — they replace nothing. A reader scanning the infographic should still find the same words they would skim in the Markdown. Replacing `"Week 1"` with a CSS counter that renders `"W1"` loses information; render both, or just keep `"Week 1"` and skip the counter.

## Edge cases

- **Empty Markdown file:** Don't generate. Tell the user the file is empty and ask if they want a placeholder or to skip.
- **Markdown that's mostly code blocks:** Render the code blocks as styled `<pre>` blocks inside cards. Don't try to infographic-ify code itself.
- **Existing HTML with the same name:** Overwrite. The user can `git diff` if they need to compare.
- **Relative paths in file references:** If the source `.md` lives at `wikis/agentic_coding/foo.md` and references `./services/x.go`, that link will break in the HTML at the same depth. Rewrite relative links so they remain valid from the HTML's location, or convert them to absolute repo-root paths if you can determine the repo root.
- **Multi-file invocations:** Process each file independently. If one fails, report it and continue with the others.

## Examples of how to think about a source doc

**Example 1:** A research findings doc with a "## Findings (prioritized)" section listing high/medium/low severity issues, each with a `path:line` reference.

→ Hero with the doc title, then a TL;DR card, then a "Snapshot" section with a stat grid (count of issues, count by severity), then a "Where the code lives" keypath, then severity issue cards in a list, then a two-column "not issues / open questions" grid.

**Example 2:** A short product spec describing a new feature, mostly prose with a few bullet lists.

→ Hero with the feature name, TL;DR card with the one-sentence pitch, a "What it does" section as 2–3 stat cards or short cards, a "How it works" section as either a flow diagram or numbered keypath, an "Open questions" card. Less ornate than Example 1; let the simpler source guide you.

**Example 3:** A meeting notes / standup doc with action items.

→ Hero, TL;DR (the decision/outcome), a stat grid for action item counts by owner, action items as cards (not severity-coded — owner-coded or just plain), a "context" section for the discussion. If the doc is just a transcript with no clear summary, synthesize one.

## GitHub Pages

Generated HTML files can be published to GitHub Pages via:
`git@github.com:zhiyi-zhang-duke/glados-pages.git`
Served at: `https://zhiyi-zhang-duke.github.io/glados-pages/<filename>.html`
Local clone (if needed): `~/glados-pages/`

After generating an infographic, **offer** to push it there — don't push automatically. Something like: "Want me to push this to GitHub Pages?" If the user says yes, clone the repo if not already present, copy the file in, commit, push, and return the public URL.

## Reporting back

After generating, give the user a tight summary:

> Generated `path/to/file.html`. Used: TL;DR card, stat grid (4 metrics), 5 severity issue cards, 1 fan-out diagram. Open it in a browser. Want me to push it to GitHub Pages?

That's it. Don't paste the HTML, don't explain the CSS, don't list every section. The user will look at the file.
