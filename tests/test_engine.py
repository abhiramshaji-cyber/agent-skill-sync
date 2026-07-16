from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_skill_sync.engine import COMMAND_MARKER, Paths, sync, tree_hash


class SyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.paths = Paths(
            self.root / "claude-skills",
            self.root / "codex-skills",
            self.root / "claude-commands",
            self.root / "state.json",
        )
        for path in (self.paths.claude_skills, self.paths.codex_skills, self.paths.claude_commands):
            path.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def skill(self, root: Path, name: str, body: str, secret: bool = False) -> Path:
        path = root / name
        path.mkdir()
        (path / "SKILL.md").write_text(f"---\nname: {name}\ndescription: test\n---\n{body}\n")
        if secret:
            (path / ".env").write_text("SHOULD_NOT_COPY=yes")
        return path

    def test_dry_run_does_not_write(self) -> None:
        self.skill(self.paths.claude_skills, "alpha", "claude")
        report = sync(self.paths, direction="claude-to-codex")
        self.assertEqual(report.changed, 1)
        self.assertFalse((self.paths.codex_skills / "alpha").exists())
        self.assertFalse(self.paths.state_file.exists())

    def test_copy_excludes_secrets_and_is_idempotent(self) -> None:
        source = self.skill(self.paths.claude_skills, "alpha", "claude", secret=True)
        first = sync(self.paths, direction="claude-to-codex", apply=True)
        destination = self.paths.codex_skills / "alpha"
        self.assertEqual(first.changed, 1)
        self.assertEqual(tree_hash(source, codex_compatible=True), tree_hash(destination))
        self.assertFalse((destination / ".env").exists())
        second = sync(self.paths, direction="claude-to-codex", apply=True)
        self.assertEqual(second.changed, 0)

    def test_bidirectional_state_propagates_single_side_change(self) -> None:
        claude = self.skill(self.paths.claude_skills, "alpha", "initial")
        sync(self.paths, direction="both", apply=True)
        (claude / "SKILL.md").write_text("---\nname: alpha\ndescription: test\n---\nchanged\n")
        report = sync(self.paths, direction="both", apply=True)
        self.assertEqual(report.changed, 1)
        self.assertEqual(
            tree_hash(claude, codex_compatible=True),
            tree_hash(self.paths.codex_skills / "alpha"),
        )

    def test_first_run_difference_is_conflict(self) -> None:
        self.skill(self.paths.claude_skills, "alpha", "claude")
        self.skill(self.paths.codex_skills, "alpha", "codex")
        report = sync(self.paths, direction="both", conflict="skip", apply=True)
        self.assertEqual(report.conflicts, 1)

    def test_one_way_difference_requires_explicit_conflict_policy(self) -> None:
        claude = self.skill(self.paths.claude_skills, "alpha", "claude")
        codex = self.skill(self.paths.codex_skills, "alpha", "codex")
        skipped = sync(self.paths, direction="claude-to-codex", apply=True)
        self.assertEqual(skipped.conflicts, 1)
        overwritten = sync(
            self.paths,
            direction="claude-to-codex",
            conflict="claude",
            apply=True,
        )
        self.assertEqual(overwritten.changed, 1)
        self.assertEqual(tree_hash(claude, codex_compatible=True), tree_hash(codex))

    def test_codex_copy_removes_claude_only_frontmatter(self) -> None:
        source = self.skill(self.paths.claude_skills, "alpha", "body")
        (source / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: <run> " + "x" * 1100 + "\nmodel: opus\nargument-hint: value\n---\nbody\n"
        )
        sync(self.paths, direction="claude-to-codex", apply=True)
        copied = (self.paths.codex_skills / "alpha" / "SKILL.md").read_text()
        self.assertNotIn("model:", copied)
        self.assertNotIn("argument-hint:", copied)
        self.assertNotIn("<run>", copied)

    def test_commands_are_reversible_and_managed(self) -> None:
        command = self.paths.claude_commands / "ship.md"
        helper = self.paths.claude_commands / "ship.py"
        helper.write_text("print('ship')\n")
        command.write_text("---\ndescription: Ship the current branch\n---\nRun ship.py $ARGUMENTS\n")
        report = sync(self.paths, direction="claude-to-codex", apply=True)
        target = self.paths.codex_skills / "claude-command-ship"
        self.assertEqual(report.changed, 1)
        self.assertEqual((target / "command.md").read_text(), command.read_text())
        self.assertIn(COMMAND_MARKER, (target / "SKILL.md").read_text())
        self.assertEqual((target / "ship.py").read_text(), helper.read_text())

    def test_state_is_valid_json(self) -> None:
        self.skill(self.paths.claude_skills, "alpha", "initial")
        sync(self.paths, direction="both", apply=True)
        state = json.loads(self.paths.state_file.read_text())
        self.assertEqual(state["version"], 1)
        self.assertIn("alpha", state["skills"])


if __name__ == "__main__":
    unittest.main()
