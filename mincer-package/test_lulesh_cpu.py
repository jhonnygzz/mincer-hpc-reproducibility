import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


EXAMPLE = Path(__file__).parent / "examples" / "LULESH" / "cpu"


class LuleshLauncherTests(unittest.TestCase):
    def launch(self, *, profiling="0", threads="4", sudo="0", build="0", run="0"):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "build" / "work").mkdir(parents=True)
            (root / "build" / "work" / "lulesh.cc").touch()
            shutil.copyfile(EXAMPLE / "run.sh", root / "run.sh")
            binaries = root / "bin"
            binaries.mkdir()
            docker = binaries / "docker"
            docker.write_text(
                '#!/usr/bin/env bash\n'
                'printf "%s\\n" "$*" >> "$CALLS"\n'
                'if [[ "$1" == run && "$*" == *"make clean"* ]]; then\n'
                '  echo "compiler diagnostic"; exit "$BUILD_STATUS"\n'
                'fi\n'
                'if [[ "$1" == run && "$*" == *"./lulesh.kk"* ]]; then\n'
                '  echo "benchmark output"; exit "$RUN_STATUS"\n'
                'fi\n'
            )
            docker.chmod(0o755)
            sudo_script = binaries / "sudo"
            sudo_script.write_text(
                '#!/usr/bin/env bash\n'
                'printf "%s\\n" "$*" >> "$SUDO_CALLS"\n'
                '[[ "$1" == -n ]] || exit 9\nshift\nexec "$@"\n'
            )
            sudo_script.chmod(0o755)
            result = subprocess.run(
                ["bash", str(root / "run.sh")], capture_output=True, text=True,
                timeout=10,
                env=dict(os.environ, PATH=f"{binaries}:{os.environ['PATH']}",
                         CALLS=str(root / "calls"), SUDO_CALLS=str(root / "sudo-calls"),
                         BUILD_STATUS=build, RUN_STATUS=run,
                         MINCER_ALLOW_CPU_PROFILING=profiling,
                         MINCER_LULESH_THREADS=threads, MINCER_USE_SUDO_DOCKER=sudo),
            )
            calls = (root / "calls").read_text() if (root / "calls").exists() else ""
            sudo_calls = ((root / "sudo-calls").read_text()
                          if (root / "sudo-calls").exists() else "")
            logs = list((root / "build").glob("build_*.log"))
            return result, calls, sudo_calls, [log.read_text() for log in logs]

    def test_restricted_default_and_pdf_workload(self):
        result, calls, _, logs = self.launch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--cap-drop=ALL", calls)
        self.assertNotIn("--cap-add", calls)
        self.assertNotIn("--privileged", calls)
        self.assertIn("--read-only --tmpfs /tmp", calls)
        self.assertIn("OMP_NUM_THREADS=4", calls)
        self.assertIn("./lulesh.kk -s 96 -i 10", calls)
        self.assertEqual(logs, ["compiler diagnostic\n"])
        for script in (EXAMPLE / "run.sh",
                       EXAMPLE.parents[3] / "setup_cpu.sh",
                       EXAMPLE.parents[3] / "prepare_lulesh_cpu.sh"):
            self.assertNotIn("sysctl", script.read_text())
            self.assertNotIn("/proc/sys/kernel", script.read_text())

    def test_explicit_profiling_and_noninteractive_sudo(self):
        result, calls, sudo_calls, _ = self.launch(profiling="1", sudo="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--cap-drop=ALL --cap-add=PERFMON --user 0:0", calls)
        self.assertIn("-n docker info", sudo_calls)
        self.assertNotIn("--privileged", calls)

    def test_invalid_configuration_is_rejected(self):
        for options in (dict(threads="0"), dict(profiling="yes"), dict(sudo="yes")):
            with self.subTest(options=options):
                result, calls, _, _ = self.launch(**options)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("ERROR:", result.stderr)
                self.assertNotIn("./lulesh.kk", calls)

    def test_build_and_runtime_errors_are_visible(self):
        result, calls, _, _ = self.launch(build="2")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("LULESH build failed", result.stderr)
        self.assertIn("compiler diagnostic", result.stderr)
        self.assertNotIn("./lulesh.kk", calls)
        result, _, _, _ = self.launch(run="8")
        self.assertEqual(result.returncode, 8)


class LuleshCompiledChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.root = Path(cls.directory.name)
        (cls.root / "papi.h").write_text(r"""
#pragma once
#include <cstdlib>
#include <cstring>
#define PAPI_NULL -1
#define PAPI_OK 0
#define PAPI_VER_CURRENT 7
inline bool failing(const char *stage) {
    const char *failure = std::getenv("FAIL_STAGE");
    return failure && std::strcmp(failure, stage) == 0;
}
inline int result(const char *stage) { return failing(stage) ? -7 : 0; }
inline const char *PAPI_strerror(int) { return "test counter failure"; }
inline int PAPI_library_init(int) { return failing("init") ? -7 : 7; }
inline int PAPI_create_eventset(int *set) { *set = 1; return result("create"); }
inline int PAPI_query_named_event(const char *) { return result("query"); }
inline int PAPI_add_named_event(int, const char *) { return result("add"); }
inline int PAPI_start(int) { return result("start"); }
inline int PAPI_stop(int, long long *values) {
    for (int i = 0; i < 6; ++i) values[i] = 100 + i;
    if (failing("zero_cycles")) values[0] = 0;
    if (failing("negative")) values[2] = -1;
    if (failing("zero_l1")) values[2] = 0;
    return result("stop");
}
inline int PAPI_cleanup_eventset(int) { return result("cleanup"); }
inline int PAPI_destroy_eventset(int *set) { *set = PAPI_NULL; return result("destroy"); }
inline void PAPI_shutdown() {}
""")
        (cls.root / "monitor-test.cpp").write_text(r"""
#include "papi_metrics.h"
int main() {
    PAPIMetrics monitor;
    bool ok = monitor.initialize();
    if (ok) ok = monitor.start();
    if (ok) ok = monitor.stop();
    if (!monitor.printResults()) ok = false;
    if (!monitor.cleanup()) ok = false;
    return ok ? 0 : 1;
}
""")
        (cls.root / "numeric-test.cpp").write_text(r"""
#include "validate_result.h"
#include <limits>
#include <string>
#include <vector>
int main(int argc, char **argv) {
    std::vector<double> energy(96 * 96 * 96, 0.0);
    energy[0] = 3.833852e8;
    std::string mode = argc > 1 ? argv[1] : "valid";
    if (mode == "origin") energy[0] *= 1.01;
    if (mode == "origin_inside") energy[0] *= 1 + 0.9e-6;
    if (mode == "origin_outside") energy[0] *= 1 + 1.1e-6;
    if (mode == "nan") energy[100] = std::numeric_limits<double>::quiet_NaN();
    if (mode == "negative") energy[100] = -1;
    if (mode == "symmetry") energy[1] = 1;
    if (mode == "symmetry_inside") energy[1] = 0.9e-10;
    if (mode == "symmetry_outside") energy[1] = 1.1e-10;
    int cycles = mode == "iterations" ? 9 : 10;
    return validateResult(energy.data(), 96, cycles) ? 0 : 1;
}
""")
        for output, sources in (
            ("monitor", [cls.root / "monitor-test.cpp", EXAMPLE / "papi_metrics.cpp"]),
            ("numeric", [cls.root / "numeric-test.cpp"]),
        ):
            subprocess.run(
                ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                 f"-I{cls.root}", f"-I{EXAMPLE}", *map(str, sources),
                 "-o", str(cls.root / output)], check=True, capture_output=True, text=True,
            )

    def test_numerical_validation_rejects_bad_results(self):
        valid_modes = ("valid", "origin_inside", "symmetry_inside")
        for mode in (*valid_modes, "origin", "nan", "negative", "symmetry",
                     "iterations", "origin_outside", "symmetry_outside"):
            with self.subTest(mode=mode):
                result = subprocess.run([str(self.root / "numeric"), mode],
                                        capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0 if mode in valid_modes else 1)
                self.assertIn("PASS" if mode in valid_modes else "FAILED", result.stdout)

    def test_papi_failures_never_report_measurement_success(self):
        for stage in ("init", "create", "query", "add", "start", "stop",
                      "zero_cycles", "negative"):
            with self.subTest(stage=stage):
                result = subprocess.run(
                    [str(self.root / "monitor")], env=dict(os.environ, FAIL_STAGE=stage),
                    capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(result.returncode, 1)
                self.assertIn("PAPI measurement: FAILED", result.stdout)
                self.assertNotIn("PAPI_TOT_CYC (main thread):", result.stdout)
                self.assertIn("ERROR:", result.stderr)

    def test_papi_success_and_zero_cache_misses(self):
        for stage in ("", "zero_l1"):
            with self.subTest(stage=stage):
                result = subprocess.run(
                    [str(self.root / "monitor")], env=dict(os.environ, FAIL_STAGE=stage),
                    capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("PAPI measurement (main thread): PASS", result.stdout)
                self.assertIn("IPC (main-thread instructions/cycles): 1.010000", result.stdout)
                self.assertEqual(result.stdout.count("(main thread):"), 7)

    def test_papi_cleanup_failures_propagate(self):
        for stage in ("cleanup", "destroy"):
            with self.subTest(stage=stage):
                result = subprocess.run(
                    [str(self.root / "monitor")], env=dict(os.environ, FAIL_STAGE=stage),
                    capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(result.returncode, 1)
                self.assertIn("ERROR:", result.stderr)


if __name__ == "__main__":
    unittest.main()
