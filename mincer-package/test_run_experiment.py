import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import run_experiment as runner


class RunnerTests(unittest.TestCase):
    def test_matching_reference_is_logged_as_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "log.txt"
            runner.write_log({}, "hello\n", [], log)
            self.assertIn("PASS: Output matches reference", log.read_text())
            runner.write_log({}, "hello\n", None, log)
            self.assertIn("SKIP: No reference file provided", log.read_text())

    def run_workload(self, script, reference=None):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "run.sh").write_text(script)
            args = ["run_experiment.py", "--path", directory]
            if reference is not None:
                reference_path = Path(directory, "reference.txt")
                reference_path.write_text(reference)
                args.extend(["--reference", str(reference_path)])
            stdout = io.StringIO()
            with patch.object(sys, "argv", args), patch.object(
                runner, "get_system_info", return_value={"os": "test"}
            ), contextlib.redirect_stdout(stdout):
                status = runner.main()
            runs = list(Path(directory, "experiment_logs").iterdir())
            self.assertEqual(len(runs), 1)
            return status, stdout.getvalue(), Path(runs[0], "output.txt").read_text()

    def test_failure_has_nonzero_status_and_saved_diagnostics(self):
        status, console, output = self.run_workload("echo failure >&2\nexit 7\n")
        self.assertEqual(status, 1)
        self.assertIn("failure", output)
        self.assertIn("return code 7", output)
        self.assertNotIn("test completed successfully", console)

    def test_success_preserves_stderr(self):
        status, _, output = self.run_workload("echo result\necho warning >&2\n")
        self.assertEqual(status, 0)
        self.assertEqual(output, "result\nwarning\n")

    def test_reference_match_and_mismatch(self):
        for reference, expected in [("result\n", 0), ("different\n", 1)]:
            with self.subTest(reference=reference):
                status, _, _ = self.run_workload("echo result\n", reference)
                self.assertEqual(status, expected)


if __name__ == "__main__":
    unittest.main()
