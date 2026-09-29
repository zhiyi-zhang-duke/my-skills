---
name: plan-and-implement
description: "A structured workflow for taking a feature from zero to done: gather requirements, research the codebase, write a planning document, implement in dependency order, self-review, iterate on feedback, and update the plan doc. Use for non-trivial multi-file features that start without an existing plan."
---

# Plan and Implement Workflow

A structured workflow for taking a feature from zero to done: gather requirements, research the codebase, write a planning document, implement, review, and iterate.

## When to Use

Use this skill when the user wants to build a new feature or make a non-trivial change that spans multiple files. The user may not have a plan yet — this workflow starts from scratch.

## Phase 1 — Gather Requirements and Research the Codebase

Start by understanding what needs to be built and where it fits in the codebase.

1. **Clarify the goal** — Ask the user what the feature should do, who it's for, and what the expected behavior is. If the user has a rough idea but not a detailed spec, help them refine it.
2. **Identify the relevant code** — Search the codebase for the files, components, utilities, and patterns involved. Read them thoroughly.
3. **Study conventions** — Look at sibling files and similar features to understand how the codebase handles:
   - Async operations (e.g., `useEffect` with cancel flags vs fire-and-forget)
   - GraphQL query/mutation organization (inline types, `gqlOp` wrappers, error handling)
   - Component patterns (state management, event handlers, UI composition)
   - File organization (where types, queries, and utilities live relative to each other)
4. **Note open questions** — Flag anything ambiguous or where a design decision is needed (e.g., "Should users be able to save without re-uploading if a file already exists?").

## Phase 2 — Write the Planning Document

Create a markdown planning document in the repo's `wikis/` folder.

### Naming and Location

- Derive the filename from the current git branch name (e.g., branch `sourceVideoUploadCheck` → `wikis/<topic>/sourceVideoUploadCheck.md`)
- Place it in the appropriate subfolder under `wikis/` (match the team or feature area)
- If no subfolder fits, ask the user where it should go

### Document Structure

The planning document should include:

1. **Goal** — One paragraph explaining what the feature does and why
2. **Implementation steps** — Ordered sections for each file/layer to change, with:
   - The file path
   - What to add or modify
   - **Small code snippets** (5-15 lines max) showing key types, function signatures, or critical logic
   - **Pseudocode** for complex algorithms or flows instead of full implementations
   - High-level descriptions of what needs to happen, not line-by-line code
3. **Key decisions** — Any UX or architectural decisions that need to be made, with options and tradeoffs
4. **Files changed summary** — A table mapping files to the changes planned
5. **Testing notes** — What scenarios should be tested manually or with automated tests

**Keep it concise**: Use short snippets and pseudocode to convey the approach. Avoid pasting entire file contents or full implementations. The goal is a readable design document, not a code dump. Someone reading it should understand the approach and architecture without having to scroll through hundreds of lines of boilerplate.

Example of good snippet style:

```typescript
// Good: Shows the key signature and approach
interface VideoStatus {
    status: "CONVERTED" | "ERROR";
    sizes: Record<string, number>;
}

function transcodeVideo(id: string): Promise<VideoStatus> {
    // 1. Download from GCS
    // 2. Run FFmpeg conversions (mp4, mp4-low, m3u8)
    // 3. Upload results
    // 4. Verify all formats exist
}
```

Instead of:

```typescript
// Bad: Hundreds of lines of full implementation
// (entire file contents pasted here)
```

## Phase 3 — Implement in Dependency Order

Once the plan is reviewed and approved by the user, implement bottom-up:

1. **Data layer first** — Types, GraphQL queries/mutations, utility functions
2. **State and logic** — Hooks, state management, integration with existing code
3. **UI components** — Rendering, styling, user interactions
4. **Tests** — Search for existing test files for each modified module; add tests for new exports matching the existing file's patterns
5. **Stories** — Search for existing story files; add new stories only if needed (internal state changes often don't require them)

After implementation, run linters and tests:

```bash
pnpm eslint --fix <changed-files>
pnpm jest <test-files>
```

## Phase 4 — Self-Review

Before presenting changes, review your own code as a staff engineer would:

- **Initial state** — Does the feature work on page load with pre-existing data, not just after user interaction? This is the most common miss. If a `useEffect` depends on a value that's `null` until the user types, it won't fire on mount.
- **Race conditions** — Are there async operations in event handlers without cancellation? Use `useEffect` with a `let cancel = false` cleanup pattern instead.
- **Code organization** — Are new additions placed logically? Don't insert new code between a private helper and its only consumer.
- **Conventions** — Do new patterns match what the codebase already uses?

### The Initial State Pattern

When adding UI that depends on async data, key the `useEffect` on the displayed/derived value (which has an initial value from props) — not on a user-input-only state variable (which starts as `null`):

```typescript
useEffect(() => {
    if (!displayedValue || displayedValue.length !== EXPECTED_LENGTH) {
        setStatus("idle");
        return;
    }

    let cancel = false;
    setStatus("checking");

    asyncCheck(displayedValue)
        .then((result) => {
            if (!cancel) {
                setStatus(result ? "found" : "not-found");
            }
        })
        .catch(() => {
            if (!cancel) {
                setStatus("error");
            }
        });

    return () => {
        cancel = true;
    };
}, [displayedValue]);
```

## Phase 5 — Iterate on Review Feedback

When the user shares review feedback (from themselves, teammates, or other AI agents):

- **Evaluate each finding independently** — Not all feedback is correct
- **Disagree with clear reasoning** when the reviewer is wrong. For example, if a reviewer suggests a dependency change that would break initial load behavior, explain exactly why the current choice is correct and what the suggested change would break.
- **Apply valid fixes promptly** and re-run lint/tests
- **Don't treat all AI review feedback as authoritative** — AI reviewers catch pattern violations well but can miss context-dependent decisions

## Phase 6 — Update the Planning Document

After implementation and review, update the planning document with:

- **Implementation status** — A table of files changed and what was done in each
- **Review findings** — Issues found during review, their severity, and resolution
- **Remaining work** — A checklist of anything not yet addressed
- **Decisions made** — Any choices during implementation that diverged from the original plan

This makes the document a living record that future sessions or teammates can reference.
