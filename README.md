# Agent Skill Sync

Synchronize local skills between Claude Code and Codex without making either
tool the permanent source of truth. It also converts Claude slash commands into
Codex skills while retaining the original command file for later updates.

## Why

Claude Code and Codex both use `SKILL.md` directories, but they install them in
different roots. Claude also has standalone files under `~/.claude/commands`;
Codex does not expose the same command-file format. This CLI reconciles skills
directly and adapts each command into both a `claude-command-*` Codex skill and
a deprecated-but-supported Codex custom prompt. Helper files referenced by a
command are copied into the generated skill as well.

## Safety model

- Every sync is a dry-run unless `--apply` is passed.
- First-run differences are conflicts and are skipped by default.
- Later bidirectional runs use saved hashes to propagate a one-sided edit.
- `.env`, credential, secret, token, private-key, VCS, cache, and dependency
  files are excluded.
- Symlinked skill directories are materialized as regular files at the target.
- Claude-only frontmatter is removed from Codex copies; source files stay intact.
- System and hidden skills are never synchronized.
- Existing command targets are changed only when marked as managed by this CLI.
- Existing custom prompts are changed only when marked as managed by this CLI.

The state file contains hashes only and defaults to
`~/.config/agent-skill-sync/state.json`.

## Install

```bash
python3 -m pip install -e .
```

No runtime dependencies are required.

## Use

```bash
# Inventory
skill-sync scan

# Preview a two-way reconciliation
skill-sync sync

# Import Claude skills and commands into Codex
skill-sync sync --direction claude-to-codex --apply

# Prefer one side when both changed before the first tracked sync
skill-sync sync --conflict claude --apply

# Leave a known divergent skill untouched
skill-sync sync --direction claude-to-codex --exclude adk-validate --apply
```

Claude commands become Codex skills named `claude-command-<command>` and custom
prompts under `~/.codex/prompts`. After restarting Codex, invoke `/pr-new` from
Claude as `/prompts:pr-new` in Codex. Custom prompts are deprecated by Codex, so
the generated skill remains the durable representation and bundles helper files.

## MCP bridge

The sync engine shares instructions; the MCP bridge lets one coding agent call
the other as a tool:

```bash
skill-sync bridge status
skill-sync bridge codex-calls-claude
skill-sync bridge claude-calls-codex
```

Configure one direction in normal use. `skill-sync bridge both` is supported but
warns because two agents that can call each other can recurse.

## Test

```bash
python3 -m unittest discover -s tests -v
```

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT. See [LICENSE](LICENSE).
