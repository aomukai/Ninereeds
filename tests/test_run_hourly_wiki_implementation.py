import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "workflow" / "run_hourly_wiki_implementation.py"
spec = importlib.util.spec_from_file_location("hourly_wiki", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RateLimitHeuristicTests(unittest.TestCase):
    def test_unknown_limit_becomes_weekly_after_five_prior_rate_limits_in_last_ten_entries(self):
        self.assertEqual(
            module.refine_rate_limit_type(
                "unknown",
                consecutive_prior_rate_limits=2,
                rate_limits_in_recent_entries=5,
            ),
            "weekly",
        )

    def test_unknown_limit_stays_generic_when_recent_window_is_below_threshold(self):
        self.assertEqual(
            module.refine_rate_limit_type(
                "unknown",
                consecutive_prior_rate_limits=4,
                rate_limits_in_recent_entries=4,
            ),
            "unknown",
        )

    def test_explicit_session_limit_is_not_overridden_by_recent_window(self):
        self.assertEqual(
            module.refine_rate_limit_type(
                "session",
                consecutive_prior_rate_limits=10,
                rate_limits_in_recent_entries=9,
            ),
            "session",
        )

    def test_counts_trailing_rate_limit_streak_from_log(self):
        log_text = """# Wiki Implementation Cron Log

## 2026-04-17 00:00:00 UTC — success
## 2026-04-17 01:00:00 UTC — rate-limited-skip
## 2026-04-17 02:00:00 UTC — weekly-cap-likely-skip
## 2026-04-17 03:00:00 UTC — rate-limited-skip
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "wiki_implementation_run_log.md"
            log_path.write_text(log_text, encoding="utf-8")
            self.assertEqual(module.count_consecutive_rate_limit_skips(log_path), 3)

    def test_counts_rate_limit_entries_within_recent_window(self):
        log_text = """# Wiki Implementation Cron Log

## 2026-04-17 00:00:00 UTC — rate-limited-skip
## 2026-04-17 01:00:00 UTC — success
## 2026-04-17 02:00:00 UTC — rate-limited-skip
## 2026-04-17 03:00:00 UTC — no-op
## 2026-04-17 04:00:00 UTC — rate-limited-skip
## 2026-04-17 05:00:00 UTC — success
## 2026-04-17 06:00:00 UTC — weekly-cap-likely-skip
## 2026-04-17 07:00:00 UTC — success
## 2026-04-17 08:00:00 UTC — rate-limited-skip
## 2026-04-17 09:00:00 UTC — success
## 2026-04-17 10:00:00 UTC — rate-limited-skip
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "wiki_implementation_run_log.md"
            log_path.write_text(log_text, encoding="utf-8")
            self.assertEqual(module.count_rate_limit_skips_in_recent_entries(log_path, window=10), 5)


if __name__ == "__main__":
    unittest.main()
