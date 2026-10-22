#include "XSbench_header.h"

#ifdef PAPI

#include <papi.h>

#define PACKAGE_ENERGY_EVENT "rapl::RAPL_ENERGY_PKG:cpu=0"
#define DRAM_ENERGY_EVENT "rapl::RAPL_ENERGY_DRAM:cpu=0"

typedef struct {
    int energy_event_set;
    int performance_event_set;
    int papi_initialized;
    int failed;
    int energy_ready;
    int performance_ready;
    int energy_started;
    int performance_started;
    int energy_collected;
    int performance_collected;
    long long energy_values[2];
    long long performance_values[2];
} Monitor;

static Monitor monitor = {
    .energy_event_set = PAPI_NULL,
    .performance_event_set = PAPI_NULL
};

static void report_papi_error(const char *operation, int status)
{
    fprintf(stderr, "ERROR: PAPI %s failed: %s (status %d)\n",
            operation, PAPI_strerror(status), status);
    monitor.failed = 1;
}

static int add_required_named_event(int event_set, const char *event_name)
{
    int status = PAPI_query_named_event(event_name);
    if (status != PAPI_OK) {
        char operation[256];
        snprintf(operation, sizeof(operation),
                 "availability check for %s", event_name);
        report_papi_error(operation, status);
        return 1;
    }

    status = PAPI_add_named_event(event_set, event_name);
    if (status != PAPI_OK) {
        char operation[256];
        snprintf(operation, sizeof(operation), "addition of %s", event_name);
        report_papi_error(operation, status);
        return 1;
    }
    return 0;
}

static int add_required_event(int event_set, int event_code,
                              const char *event_name)
{
    int status = PAPI_query_event(event_code);
    if (status != PAPI_OK) {
        char operation[160];
        snprintf(operation, sizeof(operation),
                 "availability check for %s", event_name);
        report_papi_error(operation, status);
        return 1;
    }

    status = PAPI_add_event(event_set, event_code);
    if (status != PAPI_OK) {
        char operation[160];
        snprintf(operation, sizeof(operation), "addition of %s", event_name);
        report_papi_error(operation, status);
        return 1;
    }
    return 0;
}

int init_rapl_monitoring(void)
{
    int status = PAPI_library_init(PAPI_VER_CURRENT);
    if (status != PAPI_VER_CURRENT) {
        if (status < PAPI_OK) {
            report_papi_error("library initialization", status);
        } else {
            fprintf(stderr,
                    "ERROR: PAPI version mismatch: expected 0x%x, received 0x%x\n",
                    PAPI_VER_CURRENT, status);
            monitor.failed = 1;
        }
        return 1;
    }
    monitor.papi_initialized = 1;

    int energy_errors = 0;
    int performance_errors = 0;

    status = PAPI_create_eventset(&monitor.energy_event_set);
    if (status != PAPI_OK) {
        report_papi_error("energy event-set creation", status);
        energy_errors++;
    } else {
        energy_errors += add_required_named_event(monitor.energy_event_set,
                                                  PACKAGE_ENERGY_EVENT);
        energy_errors += add_required_named_event(monitor.energy_event_set,
                                                  DRAM_ENERGY_EVENT);
    }

    status = PAPI_create_eventset(&monitor.performance_event_set);
    if (status != PAPI_OK) {
        report_papi_error("performance event-set creation", status);
        performance_errors++;
    } else {
        performance_errors += add_required_event(
            monitor.performance_event_set, PAPI_TOT_CYC, "PAPI_TOT_CYC");
        performance_errors += add_required_event(
            monitor.performance_event_set, PAPI_TOT_INS, "PAPI_TOT_INS");
    }

    monitor.energy_ready = energy_errors == 0;
    monitor.performance_ready = performance_errors == 0;
    return monitor.failed ? 1 : 0;
}

int start_rapl_measurement(void)
{
    if (!monitor.energy_ready && !monitor.performance_ready) {
        monitor.failed = 1;
        return 1;
    }

    if (monitor.energy_ready) {
        int status = PAPI_start(monitor.energy_event_set);
        if (status != PAPI_OK) {
            report_papi_error("energy counter start", status);
        } else {
            monitor.energy_started = 1;
        }
    }

    if (monitor.performance_ready) {
        int status = PAPI_start(monitor.performance_event_set);
        if (status != PAPI_OK) {
            report_papi_error("performance counter start", status);
        } else {
            monitor.performance_started = 1;
        }
    }

    return monitor.failed ? 1 : 0;
}

int stop_rapl_measurement(void)
{
    if (monitor.energy_started) {
        int status = PAPI_stop(monitor.energy_event_set, monitor.energy_values);
        if (status != PAPI_OK) {
            report_papi_error("energy counter stop", status);
        } else {
            monitor.energy_collected = 1;
        }
        monitor.energy_started = 0;
    }

    if (monitor.performance_started) {
        int status = PAPI_stop(monitor.performance_event_set,
                               monitor.performance_values);
        if (status != PAPI_OK) {
            report_papi_error("performance counter stop", status);
        } else {
            monitor.performance_collected = 1;
        }
        monitor.performance_started = 0;
    }

    if (monitor.energy_collected &&
        (monitor.energy_values[0] <= 0 || monitor.energy_values[1] <= 0)) {
        fprintf(stderr,
                "ERROR: PAPI returned non-positive package or DRAM energy; "
                "energy will not be reported.\n");
        monitor.energy_collected = 0;
        monitor.failed = 1;
    }
    if (monitor.performance_collected &&
        (monitor.performance_values[0] <= 0 ||
         monitor.performance_values[1] <= 0)) {
        fprintf(stderr,
                "ERROR: PAPI returned non-positive cycles or instructions; "
                "performance counters will not be reported.\n");
        monitor.performance_collected = 0;
        monitor.failed = 1;
    }

    return monitor.failed ? 1 : 0;
}

int print_rapl_results(double runtime)
{
    int measurement_failed = monitor.failed;

    if (monitor.energy_collected) {
        const double package_joules = (double)monitor.energy_values[0] / 1.0e9;
        const double dram_joules = (double)monitor.energy_values[1] / 1.0e9;
        const double combined_joules = package_joules + dram_joules;
        printf("PAPI RAPL energy measurement: PASS\n");
        printf("Package energy (socket 0): %lld nJ (%.6f J)\n",
               monitor.energy_values[0], package_joules);
        printf("DRAM energy (socket 0): %lld nJ (%.6f J)\n",
               monitor.energy_values[1], dram_joules);
        printf("Package + DRAM energy (socket 0): %.6f J\n", combined_joules);
        if (runtime > 0.0) {
            printf("Average package power (socket 0): %.3f W\n",
                   package_joules / runtime);
            printf("Average DRAM power (socket 0): %.3f W\n",
                   dram_joules / runtime);
            printf("Average package + DRAM power (socket 0): %.3f W\n",
                   combined_joules / runtime);
        }
    } else {
        printf("PAPI RAPL energy measurement: FAILED; no energy values reported\n");
        measurement_failed = 1;
    }

    if (monitor.performance_collected) {
        const long long cycles = monitor.performance_values[0];
        const long long instructions = monitor.performance_values[1];
        printf("PAPI performance measurement (main thread): PASS\n");
        printf("PAPI_TOT_CYC (main thread): %lld\n", cycles);
        printf("PAPI_TOT_INS (main thread): %lld\n", instructions);
        if (runtime > 0.0) {
            printf("Main-thread cycle rate over simulation wall time: %.3f Gcycles/s\n",
                   (double)cycles / runtime / 1.0e9);
            printf("Main-thread instruction rate over simulation wall time: %.3f MIPS\n",
                   (double)instructions / runtime / 1.0e6);
        }
        printf("IPC (main-thread instructions/cycles): %.6f\n",
               (double)instructions / (double)cycles);
    } else {
        printf("PAPI performance measurement: FAILED; no counter values reported\n");
        measurement_failed = 1;
    }
    return measurement_failed;
}

int cleanup_rapl_monitoring(void)
{
    int cleanup_failed = 0;
    int *event_sets[] = {
        &monitor.energy_event_set,
        &monitor.performance_event_set
    };

    for (size_t i = 0; i < sizeof(event_sets) / sizeof(event_sets[0]); ++i) {
        if (*event_sets[i] == PAPI_NULL) {
            continue;
        }
        int status = PAPI_cleanup_eventset(*event_sets[i]);
        if (status != PAPI_OK) {
            report_papi_error("event-set cleanup", status);
            cleanup_failed = 1;
        }
        status = PAPI_destroy_eventset(event_sets[i]);
        if (status != PAPI_OK) {
            report_papi_error("event-set destruction", status);
            cleanup_failed = 1;
        }
    }
    if (monitor.papi_initialized) {
        PAPI_shutdown();
    }
    return cleanup_failed || monitor.failed ? 1 : 0;
}

#endif
