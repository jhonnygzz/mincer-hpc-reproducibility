import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


EXAMPLE = (
    Path(__file__).parent
    / "examples"
    / "MatrixMultiplication"
    / "cpu"
)


class MatrixKernelTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("cc"), "a C compiler is required")
    def test_both_layouts_match_analytical_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "test_matrix_kernels"
            subprocess.run(
                [
                    "cc",
                    "-O2",
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Wpedantic",
                    "-Werror",
                    str(EXAMPLE / "matrix_kernels.c"),
                    str(EXAMPLE / "test_matrix_kernels.c"),
                    "-lm",
                    "-o",
                    str(executable),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            result = subprocess.run(
                [str(executable)], check=True, capture_output=True, text=True
            )
            self.assertIn(
                "Both matrix layouts match the analytical reference.",
                result.stdout,
            )


class MatrixLauncherTests(unittest.TestCase):
    def run_launcher(self, profiling="0", build_status="0", run_status="0"):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in (
                "matrix_multiplication.c",
                "matrix_kernels.c",
                "matrix_kernels.h",
                "run.sh",
            ):
                shutil.copyfile(EXAMPLE / name, root / name)

            binaries = root / "bin"
            binaries.mkdir()
            docker = binaries / "docker"
            docker.write_text(
                "#!/usr/bin/env bash\n"
                'printf "%s\\n" "$*" >> "$MOCK_CALLS"\n'
                'if [[ "$1" == run && "$*" == *"gcc"* ]]; then\n'
                '  echo "compiler diagnostic"\n'
                '  exit "$MOCK_BUILD_STATUS"\n'
                "fi\n"
                'if [[ "$1" == run ]]; then\n'
                '  echo "matrix results"\n'
                '  exit "$MOCK_RUN_STATUS"\n'
                "fi\n"
            )
            docker.chmod(0o755)
            calls = root / "calls.txt"
            result = subprocess.run(
                ["bash", str(root / "run.sh")],
                env=dict(
                    os.environ,
                    PATH=f"{binaries}:{os.environ['PATH']}",
                    MOCK_CALLS=str(calls),
                    MOCK_BUILD_STATUS=build_status,
                    MOCK_RUN_STATUS=run_status,
                    MINCER_ALLOW_CPU_PROFILING=profiling,
                ),
                capture_output=True,
                text=True,
                timeout=10,
            )
            logs = list((root / "build").glob("build_*.log"))
            return (
                result,
                calls.read_text() if calls.exists() else "",
                [log.read_text() for log in logs],
            )

    def test_default_run_does_not_request_profiling_capability(self):
        result, calls, logs = self.run_launcher()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("matrix results", result.stdout)
        self.assertEqual(logs, ["compiler diagnostic\n"])
        self.assertNotIn("--cap-add", calls)
        self.assertNotIn("--privileged", calls)

    def test_profiling_capability_is_explicit_opt_in(self):
        result, calls, _ = self.run_launcher(profiling="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("host counter policy must also permit access", result.stdout)
        self.assertIn("--cap-add=PERFMON", calls)
        self.assertIn("--cap-drop=ALL", calls)
        self.assertNotIn("--privileged", calls)

    def test_sudo_docker_requires_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in (
                "matrix_multiplication.c",
                "matrix_kernels.c",
                "matrix_kernels.h",
                "run.sh",
            ):
                shutil.copyfile(EXAMPLE / name, root / name)
            binaries = root / "bin"
            binaries.mkdir()
            docker = binaries / "docker"
            docker.write_text(
                "#!/usr/bin/env bash\n"
                'printf "%s\\n" "$*" >> "$MOCK_CALLS"\n'
            )
            docker.chmod(0o755)
            sudo = binaries / "sudo"
            sudo.write_text(
                "#!/usr/bin/env bash\n"
                'printf "%s\\n" "$*" >> "$MOCK_SUDO_CALLS"\n'
                '[[ "$1" == "-n" ]] && shift\n'
                'exec "$@"\n'
            )
            sudo.chmod(0o755)
            calls = root / "calls.txt"
            result = subprocess.run(
                ["bash", str(root / "run.sh")],
                env=dict(
                    os.environ,
                    PATH=f"{binaries}:{os.environ['PATH']}",
                    MOCK_CALLS=str(calls),
                    MOCK_SUDO_CALLS=str(root / "sudo-calls.txt"),
                    MINCER_USE_SUDO_DOCKER="1",
                ),
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("-n docker", (root / "sudo-calls.txt").read_text())

    def test_invalid_profiling_setting_fails_before_build(self):
        result, calls, logs = self.run_launcher(profiling="unexpected")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MINCER_ALLOW_CPU_PROFILING must be 0 or 1", result.stderr)
        self.assertNotIn("gcc", calls)
        self.assertEqual(logs, [])

    def test_build_and_runtime_failures_are_reported(self):
        result, _, logs = self.run_launcher(build_status="2")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("build failed", result.stderr)
        self.assertIn("compiler diagnostic", result.stderr)
        self.assertEqual(len(logs), 1)

        result, _, _ = self.run_launcher(run_status="7")
        self.assertEqual(result.returncode, 7)
        self.assertNotIn("matrix results", result.stderr)


if __name__ == "__main__":
    unittest.main()
