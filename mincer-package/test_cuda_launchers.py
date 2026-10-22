import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class CudaLauncherTests(unittest.TestCase):
    def run_launcher(self, example, build_status="0", run_status="0", profiling="0"):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = Path(__file__).parent / "examples" / example / "cuda" / "run.sh"
            shutil.copyfile(script, root / "run.sh")
            work = root / "build" / "work"
            if example == "LULESH":
                work.mkdir(parents=True)
                (work / "lulesh.cc").touch()
            else:
                source = work / "examples" / "algorithms" / "bfs"
                source.mkdir(parents=True)
                (source / "bfs.cu").touch()
            binaries = root / "bin"
            binaries.mkdir()
            docker = binaries / "docker"
            docker.write_text(
                "#!/usr/bin/env bash\n"
                'printf "%s\\n" "$*" >> "$MOCK_CALLS"\n'
                'if [[ "$1" == run ]]; then\n'
                '  if [[ "$*" == *"--entrypoint bash"* ]]; then\n'
                '    echo "compiler details"\n'
                '    echo "compiler diagnostic" >&2\n'
                '    exit "$MOCK_BUILD_STATUS"\n'
                "  fi\n"
                '  echo "benchmark results"\n'
                '  exit "$MOCK_RUN_STATUS"\n'
                "fi\n"
                'if [[ "$*" == *"--format"* ]]; then echo "test-image"; fi\n'
            )
            docker.chmod(0o755)
            calls = root / "calls.txt"
            env = dict(
                os.environ,
                PATH=f"{binaries}:{os.environ['PATH']}",
                MOCK_CALLS=str(calls),
                MOCK_BUILD_STATUS=build_status,
                MOCK_RUN_STATUS=run_status,
                MINCER_ALLOW_GPU_PROFILING=profiling,
            )
            result = subprocess.run(
                ["bash", str(root / "run.sh")],
                env=env, capture_output=True, text=True, timeout=10,
            )
            logs = list((root / "build").glob("build_*.log"))
            return (
                result,
                [log.read_text() for log in logs],
                calls.read_text() if calls.exists() else "",
            )

    def test_build_details_are_saved_not_printed_on_success(self):
        for example in ("LULESH", "Gunrock"):
            with self.subTest(example=example):
                result, logs, calls = self.run_launcher(example)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("benchmark results", result.stdout)
                self.assertNotIn("compiler details", result.stdout + result.stderr)
                self.assertEqual(logs, ["compiler details\ncompiler diagnostic\n"])
                self.assertNotIn("--cap-add", calls)
                self.assertNotIn("--privileged", calls)

    def test_build_failure_is_visible_and_skips_measurement(self):
        for example in ("LULESH", "Gunrock"):
            with self.subTest(example=example):
                result, logs, calls = self.run_launcher(example, build_status="2")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("build failed", result.stderr)
                self.assertIn("compiler diagnostic", result.stderr)
                self.assertEqual(len(logs), 1)
                self.assertNotIn("--gpus", calls)

    def test_runtime_failure_is_not_reported_as_complete(self):
        for example in ("LULESH", "Gunrock"):
            with self.subTest(example=example):
                result, _, _ = self.run_launcher(example, run_status="7")
                self.assertEqual(result.returncode, 7)
                self.assertNotIn("Test Complete", result.stdout)

    def test_profiling_capability_is_explicitly_opt_in(self):
        for example in ("LULESH", "Gunrock"):
            with self.subTest(example=example):
                result, _, calls = self.run_launcher(example, profiling="1")
                self.assertEqual(result.returncode, 0)
                self.assertIn("--cap-add SYS_ADMIN", calls)
                self.assertIn("--read-only", calls)
                self.assertNotIn("--privileged", calls)
                result, logs, _ = self.run_launcher(example, profiling="invalid")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("must be 0 or 1", result.stderr)
                self.assertEqual(logs, [])


if __name__ == "__main__":
    unittest.main()
