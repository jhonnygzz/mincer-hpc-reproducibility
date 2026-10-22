import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from test_xsbench_hip import DEVICES_READY


ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "mincer-package/examples/LULESH/hip"


@unittest.skipUnless(DEVICES_READY, "AMD GPU devices are not accessible")
class LuleshHipLauncherTests(unittest.TestCase):
    def launch(self, *, build="0", run="0", device="0", threads="1"):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "build/work").mkdir(parents=True)
            (root / "build/work/lulesh.cc").touch()
            shutil.copyfile(EXAMPLE / "run.sh", root / "run.sh")
            (root / "bin").mkdir()
            docker = root / "bin/docker"
            docker.write_text(
                '#!/usr/bin/env bash\n'
                'echo "$*" >> "$CALLS"\n'
                'if [[ "$*" == *"make clean"* ]]; then\n'
                '  echo "compiler diagnostics"; exit "$BUILD_STATUS"\n'
                'fi\n'
                'if [[ "$*" == *"./lulesh.kk"* ]]; then exit "$RUN_STATUS"; fi\n'
            )
            docker.chmod(0o755)
            env = dict(os.environ, PATH=f"{root / 'bin'}:{os.environ['PATH']}",
                       CALLS=str(root / "calls"), BUILD_STATUS=build, RUN_STATUS=run,
                       MINCER_AMD_DEVICE=device, MINCER_USE_SUDO_DOCKER="0",
                       MINCER_LULESH_THREADS=threads)
            result = subprocess.run(["bash", str(root / "run.sh")],
                                    env=env, capture_output=True, text=True, timeout=10)
            calls = (root / "calls").read_text() if (root / "calls").exists() else ""
            return result, calls

    def test_pdf_workload_isolation_and_permissions(self):
        result, calls = self.launch(device="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ROCR_VISIBLE_DEVICES=1", calls)
        self.assertIn("HIP_VISIBLE_DEVICES=0", calls)
        self.assertIn("--cap-drop=ALL", calls)
        self.assertIn("--read-only --tmpfs /tmp", calls)
        self.assertIn("./lulesh.kk -s 96 -i 10", calls)
        for option in ("--privileged", "--cap-add", "seccomp=unconfined"):
            self.assertNotIn(option, calls)

    def test_build_failure_never_runs_stale_binary(self):
        result, calls = self.launch(build="3")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("compiler diagnostics", result.stderr)
        self.assertNotIn("./lulesh.kk", calls)

    def test_runtime_failure_propagates(self):
        result, _ = self.launch(run="9")
        self.assertEqual(result.returncode, 9)

    def test_invalid_configuration(self):
        for options in (dict(device="-1"), dict(threads="0")):
            with self.subTest(options=options):
                result, calls = self.launch(**options)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("ERROR:", result.stderr)
                self.assertNotIn("./lulesh.kk", calls)


class LuleshHipSourceTests(unittest.TestCase):
    def test_exact_measurements_and_checked_lifecycle(self):
        source = (EXAMPLE / "papi_metrics.h").read_text()
        for event in ("SQ_INSTS_SALU", "SQ_INSTS_VALU", "SQ_WAVES",
                      "TCC_HIT_sum", "TCC_MISS_sum", "busy_percent",
                      "power_average", "temp_current"):
            self.assertIn(f'"{event}"', source)
        self.assertNotIn("rocp_sdk", source)
        for call in ("PAPI_start", "PAPI_stop", "PAPI_add_named_event",
                     "PAPI_cleanup_eventset", "PAPI_destroy_eventset"):
            self.assertIn(f"check({call}", source)
        self.assertLess(source.index("PAPI_library_init"), source.index("hipGetDeviceCount"))
        self.assertIn("rsmi_dev_pci_id_get", source)
        self.assertIn("not whole-run averages or energy", source)
        self.assertNotIn("Vector ALU Utilization", source)

    def test_patch_fences_and_reuses_numerical_checks(self):
        patch = (EXAMPLE / "monitoring.patch").read_text()
        self.assertEqual(patch.count("+  Kokkos::fence();"), 2)
        self.assertIn("validateResult(energy.data(), opts.nx, locDom.cycle())", patch)
        preparation = (ROOT / "prepare_lulesh_hip.sh").read_text()
        self.assertIn("cpu/validate_result.h", preparation)
        self.assertIn("1b1383c6001f3bfe9fe309ca923c2d786600cc79", preparation)
        self.assertIn("870fea7443a915336d9a545b0267dd6eb5bed396", preparation)


class LuleshHipCompiledMetricsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.root = Path(cls.directory.name)
        (cls.root / "hip").mkdir()
        (cls.root / "rocm_smi").mkdir()
        (cls.root / "papi.h").write_text(r"""
#pragma once
#include <cstdlib>
#include <cstring>
#include <initializer_list>
#define PAPI_NULL -1
#define PAPI_OK 0
#define PAPI_VER_CURRENT 7
#define PAPI_EDELAY_INIT -26
inline bool fail(const char *name) {
    const char *mode = std::getenv("FAIL");
    return mode && std::strcmp(mode, name) == 0;
}
inline int status(const char *name) { return fail(name) ? -1 : 0; }
struct PAPI_component_info_t { int disabled; const char *disabled_reason; };
inline int PAPI_library_init(int) { return fail("init") ? -1 : 7; }
inline int PAPI_get_component_index(const char *) { return fail("component") ? -1 : 0; }
inline const PAPI_component_info_t *PAPI_get_component_info(int) {
    static PAPI_component_info_t info{PAPI_EDELAY_INIT, "lazy initialization"}; return &info;
}
inline const char *PAPI_strerror(int) { return "injected failure"; }
inline int PAPI_query_named_event(const char *) { return status("query"); }
inline int PAPI_create_eventset(int *set) {
    static int id = 0; *set = ++id; return status("create");
}
inline int PAPI_add_named_event(int, const char *) { return status("add"); }
inline int PAPI_start(int set) { return status(set == 1 ? "start-counter" : "start-smi"); }
inline int PAPI_stop(int set, long long *values) {
    for (int i = 0; i < (set == 1 ? 5 : 3); ++i)
        values[i] = set == 1 ? 100 : (i == 0 ? 11 : (i == 1 ? 46000000 : 28000));
    if (fail("invalid-smi") && set == 2) values[0] = 101;
    return status(set == 1 ? "stop-counter" : "stop-smi");
}
inline int PAPI_cleanup_eventset(int) { return status("cleanup"); }
inline int PAPI_destroy_eventset(int *set) { *set = -1; return status("destroy"); }
inline void PAPI_shutdown() {}
""")
        (cls.root / "hip/hip_runtime.h").write_text(r"""
#pragma once
#include <cstdio>
constexpr int hipSuccess = 0;
inline int hipGetDeviceCount(int *count) { *count = fail("visibility") ? 2 : 1; return 0; }
inline int hipDeviceGetPCIBusId(char *id, int size, int) {
    std::snprintf(id, size, "0000:23:00.0"); return 0;
}
""")
        (cls.root / "rocm_smi/rocm_smi.h").write_text(r"""
#pragma once
#include <cstdint>
constexpr int RSMI_STATUS_SUCCESS = 0;
inline int rsmi_init(int) { return status("smi-init"); }
inline int rsmi_num_monitor_devices(uint32_t *count) { *count = 2; return 0; }
inline int rsmi_dev_pci_id_get(uint32_t index, uint64_t *id) {
    *id = index == 1 && !fail("pci-match") ? 0x2300 : 0x8300; return 0;
}
inline int rsmi_shut_down() { return status("smi-shutdown"); }
""")
        (cls.root / "main.cpp").write_text(r"""
#include "papi_metrics.h"
int main() {
    PAPIMetrics metrics;
    bool ok = metrics.initialize();
    if (ok) ok = metrics.start();
    if (ok) ok = metrics.stop();
    if (ok) ok = metrics.printResults();
    if (!metrics.cleanup()) ok = false;
    return ok ? 0 : 1;
}
""")
        subprocess.run(
            ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
             f"-I{cls.root}", f"-I{EXAMPLE}", str(cls.root / "main.cpp"),
             "-o", str(cls.root / "metrics")],
            check=True, capture_output=True, text=True,
        )

    def test_complete_measurement_and_physical_device_mapping(self):
        result = subprocess.run([str(self.root / "metrics")], capture_output=True,
                                text=True, env=dict(os.environ, FAIL=""))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SMI device 1", result.stdout)
        self.assertIn("power_average:device=1:sensor=0: 46000000 uW", result.stdout)
        self.assertIn("temp_current:device=1:sensor=0: 28000 mC", result.stdout)
        self.assertIn("PAPI measurement: PASS", result.stdout)

    def test_every_required_failure_is_nonzero_and_explicit(self):
        for failure in ("init", "component", "query", "create", "add",
                        "start-counter", "start-smi", "stop-counter", "stop-smi",
                        "cleanup", "destroy", "visibility", "pci-match",
                        "smi-init", "smi-shutdown", "invalid-smi"):
            with self.subTest(failure=failure):
                result = subprocess.run([str(self.root / "metrics")],
                                        capture_output=True, text=True,
                                        env=dict(os.environ, FAIL=failure))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("ERROR:", result.stderr)


if __name__ == "__main__":
    unittest.main()
