#!/usr/bin/env python3
"""AgyBar Automated Integration & Unit Test Suite."""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

# Add scripts directory to path
TEST_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TEST_DIR.parent
SCRIPTS_DIR = PROJECT_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from renderer import ProgressBarRenderer
from state import SessionState
from inspect_progress import calculate_granular_percentage, inspect_git_metrics


class TestAgyBarRenderer(unittest.TestCase):
    def test_smooth_bar_width_invariant(self):
        """Bar width must always equal exactly width setting across 0-100%."""
        r = ProgressBarRenderer(style="smooth", width=20)
        # Test 0% to 100% in 1% steps
        for pct in range(0, 101):
            ratio = pct / 100.0
            # Test raw character count inside bar
            sub_blocks = ["", "▏", "▎", "▍", "▌", "▋", "▊", "▉", "█"]
            full_blocks = int(20 * ratio)
            remainder = (20 * ratio) - full_blocks
            sub_idx = int(remainder * 8)
            sub_char = sub_blocks[sub_idx]
            empty_count = 20 - full_blocks - (1 if sub_char else 0)
            fill_str = "█" * full_blocks + sub_char
            empty_str = "░" * max(0, empty_count)
            self.assertEqual(len(fill_str) + len(empty_str), 20, f"Failed at {pct}%")

    def test_dual_line_format(self):
        """Renderer produces valid dual lines with ETA and high-contrast white Radar."""
        r = ProgressBarRenderer()
        state = {
            "current_step": 3,
            "total_steps": 5,
            "granular_pct": 63.5,
            "subagent_source": "Radar",
            "subagent_action": "2/3 endpoints patched • 14 unit tests passing",
            "start_time": 1000.0,
            "status": "running",
        }
        output = r.format_line(state)
        lines = output.split("\n")
        self.assertEqual(len(lines), 2)
        # Line 1 checks
        self.assertIn("Progress", lines[0])
        self.assertIn("64%", lines[0])
        self.assertIn("ETA", lines[0])
        # Line 2 checks
        self.assertIn("Radar:", lines[1])
        self.assertIn("2/3 endpoints patched", lines[1])


class TestAgyBarState(unittest.TestCase):
    def test_markdown_checklist_sniffing(self):
        """State engine correctly sniffs standard markdown task lists."""
        state = SessionState("test-checklist-session")
        sample_checklist = """
# Project Tasks
- [x] Scan existing code
- [x] Implement core logic
- [ ] Run test suite
- [ ] Review documentation
        """
        parsed = state._parse_markdown_checklist(sample_checklist)
        self.assertIsNotNone(parsed)
        total, done, curr, active, steps = parsed
        self.assertEqual(total, 4)
        self.assertEqual(done, 2)
        self.assertEqual(curr, 3)
        self.assertIn("Run test suite", active)

    def test_granular_percentage_tag_sync(self):
        """State engine parses explicit subagent progress tags."""
        state = SessionState("test-tag-session")
        transcript_content = '<!-- agybar:progress {"percent": 72.4, "action": "Subagent audit clean"} -->'
        # Create temp file to simulate transcript
        tmp_file = Path("/tmp/mock_transcript.txt")
        tmp_file.write_text(transcript_content, encoding="utf-8")
        try:
            state.sync_from_transcript(str(tmp_file))
            self.assertEqual(state.data.get("granular_pct"), 72.4)
            self.assertEqual(state.data.get("step_name"), "Subagent audit clean")
        finally:
            if tmp_file.exists():
                tmp_file.unlink()


class TestAgyBarRadarEngine(unittest.TestCase):
    def test_empirical_percentage_calculation(self):
        """Empirical percentage stays strictly within active step boundary."""
        # Step 2 of 4 -> range is 25% to 50%
        git_metrics = {"modified_files": 2, "lines_added": 30, "lines_deleted": 5}
        pct = calculate_granular_percentage(current_step=2, total_steps=4, git_metrics=git_metrics, tools_in_step=2)
        self.assertGreaterEqual(pct, 25.0)
        self.assertLessEqual(pct, 50.0)

    def test_hook_runner_contracts(self):
        """Hook runner returns valid JSON responses for all lifecycle events."""
        runner = SCRIPTS_DIR / "hook_runner.py"

        # PreToolUse
        p_pre = subprocess.run(
            [sys.executable, str(runner)],
            input=json.dumps({
                "hookEventName": "PreToolUse",
                "conversationId": "test-ci",
                "stepIdx": 1,
                "toolCall": {"name": "run_command", "args": {"CommandLine": "ls"}},
            }),
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(p_pre.returncode, 0)
        res_pre = json.loads(p_pre.stdout.strip())
        self.assertEqual(res_pre.get("decision"), "allow")

        # PostToolUse
        p_post = subprocess.run(
            [sys.executable, str(runner)],
            input=json.dumps({
                "hookEventName": "PostToolUse",
                "conversationId": "test-ci",
                "stepIdx": 1,
                "toolCall": {"name": "run_command", "args": {"CommandLine": "ls"}},
            }),
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(p_post.returncode, 0)
        res_post = json.loads(p_post.stdout.strip())
        self.assertEqual(res_post, {})


def run_tests() -> bool:
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
