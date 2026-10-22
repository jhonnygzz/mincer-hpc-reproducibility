import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


LAUNCHER = (
    Path(__file__).parent / "examples" / "XSBench" / "hip" / "run.sh"
)
RENDER_DEVICES = tuple(sorted(Path("/dev/dri").glob("renderD*")))
REQUIRED_DEVICES = (Path("/dev/kfd"), *RENDER_DEVICES)
DEVICES_READY = bool(RENDER_DEVICES) and all(
    device.is_char_device() and os.access(device, os.R_OK | os.W_OK)
    for device in REQUIRED_DEVICES
)
EXPECTED_EVENTS = [
    "rocp_sdk:::SQ_INSTS_SALU",
    "rocp_sdk:::SQ_INSTS_VALU",
    "rocp_sdk:::TCC_HIT",
    "rocp_sdk:::TCC_MISS",
    "rocp_sdk:::TCC_EA_RDREQ_32B",
    "rocp_sdk:::TCC_EA_WRREQ_64B",
    "rocp_sdk:::SQ_INSTS_VMEM_RD",
    "rocp_sdk:::SQ_INSTS_VMEM_WR",
]


class XSBenchHipMeasurementSourceTests(unittest.TestCase):
    def test_event_order_is_fixed_and_measurement_failures_are_checked(self):
        source = (
            Path(__file__).parent / "examples" / "XSBench" / "hip" / "Main.cpp"
        ).read_text()
        event_source = (
            Path(__file__).parent
            / "examples"
            / "XSBench"
            / "hip"
            / "rocp_sdk_events.cpp"
        ).read_text()
        event_table = event_source.split(
            "const char *const XSBenchGpuEvents[XSBENCH_GPU_EVENT_COUNT] = {", 1
        )[1]
        event_table = event_table.split("};", 1)[0]
        events = [
            line.split('"')[1]
            for line in event_table.splitlines()
            if '"' in line
        ]

        self.assertEqual(events, EXPECTED_EVENTS)
        self.assertIn("PAPI_add_named_event(EventSet, XSBenchGpuEvents[i])", source)
        self.assertIn(
            "PAPI_add_named_event(EventSet, event_name)",
            (
                Path(__file__).parent
                / "examples"
                / "XSBench"
                / "hip"
                / "check_rocp_sdk_events.cpp"
            ).read_text(),
        )
        self.assertIn("retval = PAPI_start(EventSet)", source)
        self.assertIn("PAPI_stop(EventSet, gpu_counter_values)", source)
        self.assertIn("hipDeviceSynchronize()", source)
        self.assertIn("PAPI_cleanup_eventset", source)
        self.assertNotIn("num_events++", source)
        self.assertNotIn("PAPI_ROCP_SDK_DISPATCH_MODE", source)


@unittest.skipUnless(DEVICES_READY, "AMD GPU devices are not accessible")
class XSBenchHipLauncherTests(unittest.TestCase):
    def run_launcher(self, *, arch="gfx908", build_status="0",
                     run_status="0", sudo_docker="0", device=None):
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
                '  echo "compiler details"\n'
                '  echo "compiler diagnostic" >&2\n'
                '  exit "$MOCK_BUILD_STATUS"\n'
                "fi\n"
                'if [[ "$1" == run ]]; then\n'
                '  echo "Verification checksum: 952131 (Valid)"\n'
                '  echo "PAPI rocp_sdk event measurements:"\n'
                '  echo "rocp_sdk:::SQ_INSTS_SALU: 100"\n'
                '  echo "rocp_sdk:::SQ_INSTS_VALU: 200"\n'
                '  echo "rocp_sdk:::TCC_HIT: 300"\n'
                '  echo "rocp_sdk:::TCC_MISS: 400"\n'
                '  echo "rocp_sdk:::TCC_EA_RDREQ_32B: 500"\n'
                '  echo "rocp_sdk:::TCC_EA_WRREQ_64B: 600"\n'
                '  echo "rocp_sdk:::SQ_INSTS_VMEM_RD: 700"\n'
                '  echo "rocp_sdk:::SQ_INSTS_VMEM_WR: 800"\n'
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

            environment = dict(
                os.environ,
                PATH=f"{binaries}:{os.environ['PATH']}",
                MOCK_DOCKER_CALLS=str(root / "docker-calls.txt"),
                MOCK_SUDO_CALLS=str(root / "sudo-calls.txt"),
                MOCK_BUILD_STATUS=build_status,
                MOCK_RUN_STATUS=run_status,
                MINCER_AMD_ARCH=arch,
                MINCER_USE_SUDO_DOCKER=sudo_docker,
            )
            if device is not None:
                environment["MINCER_AMD_DEVICE"] = device

            result = subprocess.run(
                ["bash", str(example / "run.sh")],
                env=environment,
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
            return result, calls.splitlines(), sudo_calls, [
                log.read_text() for log in logs
            ]

    def test_default_launch_uses_narrow_devices_and_restricted_container(self):
        result, calls, _, logs = self.run_launcher(device="0")
        run_calls = [call for call in calls if call.startswith("run ")]
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AMD GPU index 0", result.stdout)
        self.assertIn("Verification checksum: 952131 (Valid)", result.stdout)
        self.assertEqual(logs, ["compiler details\ncompiler diagnostic\n"])
        self.assertEqual(len(run_calls), 2)
        self.assertIn("--device=/dev/kfd:/dev/kfd:rw", run_calls[1])
        self.assertIn("--env ROCR_VISIBLE_DEVICES=0", run_calls[1])
        self.assertIn("--env HIP_VISIBLE_DEVICES=0", run_calls[1])
        self.assertIn("-m event", run_calls[1])
        self.assertIn("--cap-drop=ALL", run_calls[1])
        self.assertIn("--read-only", run_calls[1])
        self.assertNotIn("--privileged", run_calls[1])
        self.assertNotIn("--security-opt", run_calls[1])
        self.assertNotIn("--cap-add", run_calls[1])
        self.assertIn("rocp_sdk:::TCC_EA_WRREQ_64B: 600", result.stdout)
        self.assertIn("XSBench HIP completed successfully.", result.stdout)

    def test_invalid_architecture_fails_before_docker(self):
        result, calls, _, logs = self.run_launcher(arch="gfx908;false")
        run_calls = [call for call in calls if call.startswith("run ")]
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MINCER_AMD_ARCH must be a GPU target", result.stderr)
        self.assertEqual(run_calls, [])
        self.assertEqual(logs, [])

    def test_invalid_device_index_fails_before_docker(self):
        result, calls, _, logs = self.run_launcher(device="0,1")
        run_calls = [call for call in calls if call.startswith("run ")]
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MINCER_AMD_DEVICE must be a nonnegative GPU index", result.stderr)
        self.assertEqual(run_calls, [])
        self.assertEqual(logs, [])

    def test_default_device_is_index_zero(self):
        result, calls, _, _ = self.run_launcher()
        run_calls = [call for call in calls if call.startswith("run ")]
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--env ROCR_VISIBLE_DEVICES=0", run_calls[1])
        self.assertIn("--env HIP_VISIBLE_DEVICES=0", run_calls[1])

    def test_build_failure_is_logged_and_skips_measurement(self):
        result, calls, _, logs = self.run_launcher(build_status="2")
        run_calls = [call for call in calls if call.startswith("run ")]
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("XSBench HIP build failed", result.stderr)
        self.assertIn("compiler diagnostic", result.stderr)
        self.assertEqual(len(run_calls), 1)
        self.assertEqual(len(logs), 1)
        self.assertNotIn("completed successfully", result.stdout)

    def test_runtime_failure_is_not_reported_as_complete(self):
        result, calls, _, _ = self.run_launcher(run_status="8")
        run_calls = [call for call in calls if call.startswith("run ")]
        self.assertEqual(result.returncode, 8)
        self.assertEqual(len(run_calls), 2)
        self.assertNotIn("completed successfully", result.stdout)

    def test_sudo_docker_is_noninteractive_and_explicit(self):
        result, _, sudo_calls, _ = self.run_launcher(sudo_docker="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("-n docker info", sudo_calls)
        self.assertIn("-n docker image inspect", sudo_calls)


if __name__ == "__main__":
    unittest.main()
