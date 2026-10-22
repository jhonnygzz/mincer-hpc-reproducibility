import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


LAUNCHER = (
    Path(__file__).parent
    / "examples"
    / "XSBench"
    / "openmp-threading"
    / "run.sh"
)


class XSBenchLauncherTests(unittest.TestCase):
    def run_launcher(self, *, profiling="0", threads="4", build_status="0",
                     run_status="0", sudo_docker="0"):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            example = root / "example"
            example.mkdir()
            shutil.copyfile(LAUNCHER, example / "run.sh")

            binaries = root / "bin"
            binaries.mkdir()
            docker = binaries / "docker"
            docker.write_text(
                "#!/usr/bin/env bash\n"
                'printf "%s\\n" "$*" >> "$MOCK_DOCKER_CALLS"\n'
                'if [[ "$1" == run && "$*" == *"make clean"* ]]; then\n'
                '  echo "compiler diagnostic"\n'
                '  exit "$MOCK_BUILD_STATUS"\n'
                "fi\n"
                'if [[ "$1" == run && "$*" == *"./XSBench"* ]]; then\n'
                '  echo "Verification checksum: 954318 (Valid)"\n'
                '  exit "$MOCK_RUN_STATUS"\n'
                "fi\n"
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

            result = subprocess.run(
                ["bash", str(example / "run.sh")],
                env=dict(
                    os.environ,
                    PATH=f"{binaries}:{os.environ['PATH']}",
                    MOCK_DOCKER_CALLS=str(root / "docker-calls.txt"),
                    MOCK_SUDO_CALLS=str(root / "sudo-calls.txt"),
                    MOCK_BUILD_STATUS=build_status,
                    MOCK_RUN_STATUS=run_status,
                    MINCER_ALLOW_CPU_PROFILING=profiling,
                    MINCER_XSBENCH_THREADS=threads,
                    MINCER_USE_SUDO_DOCKER=sudo_docker,
                ),
                capture_output=True,
                text=True,
                timeout=10,
            )
            calls_path = root / "docker-calls.txt"
            calls = calls_path.read_text() if calls_path.exists() else ""
            sudo_calls_path = root / "sudo-calls.txt"
            sudo_calls = (
                sudo_calls_path.read_text() if sudo_calls_path.exists() else ""
            )
            logs = list((example / "build").glob("build_*.log"))
            return result, calls, sudo_calls, [log.read_text() for log in logs]

    def test_default_launch_is_restricted_and_mounts_sysfs_read_only(self):
        result, calls, _, logs = self.run_launcher()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Verification checksum: 954318 (Valid)", result.stdout)
        self.assertEqual(logs, ["compiler diagnostic\n"])
        self.assertIn("--cap-drop=ALL", calls)
        self.assertIn("--mount type=bind,src=/sys,dst=/sys,readonly", calls)
        self.assertIn("-m history -s large -p 500000 -l 34 -G unionized -t 4", calls)
        self.assertNotIn("--cap-add=PERFMON", calls)
        self.assertNotIn("--privileged", calls)

    def test_profiling_capability_is_explicit_opt_in(self):
        result, calls, _, _ = self.run_launcher(profiling="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("host counter policy must also permit access", result.stdout)
        self.assertIn("--cap-drop=ALL --cap-add=PERFMON --user 0:0", calls)
        self.assertNotIn("--privileged", calls)

    def test_sudo_docker_is_noninteractive_and_explicit(self):
        result, _, sudo_calls, _ = self.run_launcher(sudo_docker="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("-n docker info", sudo_calls)
        self.assertIn("-n docker image inspect", sudo_calls)

    def test_invalid_thread_count_fails_before_docker(self):
        result, calls, _, logs = self.run_launcher(threads="0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MINCER_XSBENCH_THREADS must be a positive integer", result.stderr)
        self.assertEqual(calls, "")
        self.assertEqual(logs, [])

    def test_build_and_runtime_failures_are_visible(self):
        result, _, _, logs = self.run_launcher(build_status="2")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("XSBench build failed", result.stderr)
        self.assertIn("compiler diagnostic", result.stderr)
        self.assertEqual(len(logs), 1)

        result, _, _, _ = self.run_launcher(run_status="8")
        self.assertEqual(result.returncode, 8)


if __name__ == "__main__":
    unittest.main()
