---
name: tmux-operator
description: "Switches Claude into \"tmux operator mode\" — orients to the current tmux session and biases work toward pane-based workflows: side panes for ssh sessions, long-running commands, log tailing, interactive prompts, sub-agent coordination. Use this skill whenever the user kicks off a new session inside tmux, mentions tmux / panes / windows / splits / sessions, wants to orchestrate sub-agents or parallel work, or any time a side pane would be more useful than running a command inline. Don't wait for the user to say \"use tmux\" — if a task would clearly benefit from a side pane (ssh, long build, watching a log, anything interactive), proactively offer one."
---

# tmux operator mode

You're operating inside (or alongside) a tmux session. This skill biases your default
behaviors so that panes become a normal part of how you work, not an exotic case.

## Step 1: orient before doing anything else

Before suggesting actions, check the lay of the land. One short bash block:

```bash
tmux -V                                                # version (some flags are recent)
[ -n "$TMUX" ] && echo "inside tmux: $TMUX" || echo "outside tmux"
tmux display-message -p '#S:#I.#P  pane=#{pane_id}  win=#{window_id}  sess=#{session_id}  size=#{window_width}x#{window_height}' 2>/dev/null
tmux list-panes -a -F '#{pane_id} #{session_name}:#{window_index}.#{pane_index} #{pane_current_command} (#{pane_width}x#{pane_height})' 2>/dev/null
```

State briefly what you found ("I'm in session X, pane %0, one other pane %1 running ssh")
so the user knows you're oriented. If `$TMUX` is empty, say so — you can still
*start* tmux for the user, but don't assume their current shell is inside one.

## Step 2: consult the wiki for syntax

A comprehensive tmux reference lives at **`/home/jzhanglsw/wikis/tmux.md`**. It has
every command, flag, target form, format string, and orchestration pattern you'll
need. Read the relevant section on demand — don't try to recall every flag from
memory. The sections most worth jumping to:

- §3 Targets — how to address panes/windows correctly
- §8 `send-keys` — the key-name vs. literal-text trap is the #1 source of bugs
- §9 `capture-pane` / `pipe-pane` — reading what a pane has done
- §10 Synchronization (`wait-for`) — clean way to know when a job finishes
- §12 Sub-agent orchestration patterns — driving other Claude instances in panes

If the wiki doesn't have what you need, `man tmux` and `tmux list-commands` are
authoritative. Update the wiki when you learn something it doesn't cover.

## Defaults to follow

These are based on what's worked in practice, not arbitrary preferences. The "why"
matters — apply judgment when conditions differ.

**Use stable IDs (`%N`, `@N`, `$N`), not indexes (`:0.1`).** Capture the id at
creation time and reuse it: `PANE=$(tmux split-window -d -P -F '#{pane_id}')`.
Indexes shift when panes are killed; ids are stable for the life of the server. A
script that uses `:0.1` will silently target the wrong pane after a kill.

**Pick the layout to match the window width.** Side-by-side (`-h`) needs roughly
≥120 cols total to be comfortable; below that, stack vertically (`-v`, the
default). If you split and it looks cramped, switch with
`tmux select-layout even-horizontal | even-vertical`.

**Spawn side panes detached.** `-d` keeps the user's focus where it is so you
don't yank their cursor around. `-P -F '#{pane_id}'` prints the new id so you can
target it next. Together: `tmux split-window -h -d -P -F '#{pane_id}' [cmd]`.

**Never send credentials with `send-keys`.** Passwords, API keys, tokens — if the
target pane is at a password prompt, ask the user to focus that pane and type it
themselves. Credentials sent via `send-keys` end up in this transcript and in
anyone's view of your work; that's a leak the user didn't authorize.

**After `send-keys "command"`, always add `Enter`.** Without it, the command just
sits at the prompt and you'll think the pane is stuck. If you're sending arbitrary
text that might contain words like `Enter` or `Tab`, use `-l` to make tmux treat
it literally: `tmux send-keys -t %2 -l 'text' ; tmux send-keys -t %2 Enter`.

**For multi-line input (long prompts, code blocks), use a buffer.** `send-keys -l`
chokes on long inputs. Pattern: `tmux load-buffer -b X file; tmux paste-buffer -b X -d -t %2`.
One PTY write, no quoting hell.

**Read pane output with `capture-pane -p -J -S -<N>`.** `-p` prints to stdout, `-J`
joins wrapped lines (almost always what you want for parsing), `-S -N` includes the
last N lines of history. The default 2000-line scrollback fills fast on chatty
processes; for jobs that need durable logs use `tmux pipe-pane -O 'cat >> /path'`.

**For "wait until done", prefer `wait-for` over polling.** Idiom:
`tmux send-keys -t %2 'long_cmd; tmux wait-for -S done' Enter; tmux wait-for done`.
Falls back to capture-pane polling only when you can't modify the remote command.

## When to spawn a side pane (don't wait to be asked)

Offer a side pane whenever a task would benefit from one. The user shouldn't have
to say "use tmux" — read the situation:

- **SSH / remote shells** — keeps the session alive and out of the way while we
  keep planning here.
- **Long-running commands** — builds, test suites, `npm run dev`, anything that
  takes more than a few seconds and produces output the user might want to watch.
- **Log tailing** — `tail -f`, `journalctl -f`, `docker logs -f`. The "tail in one
  pane, work in another" layout is a classic for a reason.
- **Interactive REPLs** — Python, node, psql, redis-cli. The REPL persists across
  multiple commands and you can capture state.
- **Anything with an interactive prompt** — host-key acceptance, sudo passwords,
  `yes/no` confirmations. Side pane lets the human focus it directly.
- **Parallel work** — if two subtasks are independent, panes let you (or
  sub-agents) work both simultaneously instead of serializing.

When you propose a side pane, say what you'd run, in which direction (h/v), and
what you'll do with the pane id. Then act if the user agrees.

## Sub-agent orchestration

When the user wants another Claude (or any interactive process) cooperating in a
sibling pane, the standard moves are in **wiki §12**. The three big patterns:

1. **Spawn**: `AGENT=$(tmux split-window -h -d -P -F '#{pane_id}' 'claude')`.
2. **Send a prompt**: for short text, `send-keys -t "$AGENT" -l 'prompt' ; send-keys -t "$AGENT" Enter`. For long or multi-line prompts, use a buffer (see Defaults).
3. **Wait + read**: best — have the sub-agent end its reply with `tmux wait-for -S done` and you `tmux wait-for done`. Failing that, `pipe-pane` to a log and grep for a prompt marker. Last resort: poll `capture-pane` until output stops changing (false-positives on mid-reply pauses).

For fan-out / fan-in across several agents, store ids in an associative array
(`declare -A AGENT; AGENT[role]=$(tmux split-window ...)`) and loop over keys.

## Things that look helpful but aren't

- **Don't rebind bare arrow keys.** They're load-bearing — bash history, line
  editing, vim, every TUI. PageUp/PageDown are safe to rebind for scrollback; bare
  arrows are not.
- **Don't pile on config changes.** If the user asks for one binding, add one.
  Resist the urge to also flip mouse mode, vi keys, status bar, etc. unless they
  ask. Their config, their call.
- **Don't auto-accept ssh host keys at scale.** The first connection prompt is
  fine to confirm. Programmatically setting `StrictHostKeyChecking=no` defeats the
  whole point and silently accepts MITM.
- **Don't `kill-server`** to "reset" something. It ends every session for every
  client. Kill the specific pane or window instead.

## Quick reference: the operations you'll actually use

| Goal | Command |
|---|---|
| Self id | `echo "$TMUX_PANE"` or `tmux display -p '#{pane_id}'` |
| Spawn side pane | `tmux split-window -h -d -P -F '#{pane_id}'` |
| Spawn new window | `tmux new-window -d -P -F '#{window_id}' [cmd]` |
| Type in pane | `tmux send-keys -t %N 'cmd' Enter` |
| Type literal text | `tmux send-keys -t %N -l 'text with keywords' ; tmux send-keys -t %N Enter` |
| Read visible | `tmux capture-pane -t %N -p -J` |
| Read with history | `tmux capture-pane -t %N -p -J -S -200` |
| Stream to file | `tmux pipe-pane -t %N -O 'cat >> /path'` |
| Stop streaming | `tmux pipe-pane -t %N` |
| Wait for signal | `tmux wait-for done` / `-S done` |
| List everything | `tmux list-panes -a -F …` |
| Kill pane | `tmux kill-pane -t %N` |
| Switch layout | `tmux select-layout even-horizontal\|even-vertical\|tiled` |

Everything else: open the wiki.
