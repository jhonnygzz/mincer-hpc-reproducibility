#include "papi_metrics.h"
#include <cstdio>

namespace {
const char *const eventNames[] = {
    "PAPI_TOT_CYC", "PAPI_TOT_INS", "PAPI_L1_DCM",
    "PAPI_L1_ICM", "PAPI_L1_LDM", "PAPI_L1_TCM"
};

bool checked(int status, const char *operation, const char *event = "") {
    if (status == PAPI_OK) {
        return true;
    }
    std::fprintf(stderr, "ERROR: PAPI %s %s failed: %s (status %d)\n",
                 operation, event, PAPI_strerror(status), status);
    return false;
}
}

bool PAPIMetrics::initialize() {
    int status = PAPI_library_init(PAPI_VER_CURRENT);
    if (status != PAPI_VER_CURRENT) {
        std::fprintf(stderr, "ERROR: PAPI initialization/version check failed (status %d).\n",
                     status);
        return false;
    }
    initialized = true;
    if (!checked(PAPI_create_eventset(&eventSet), "event-set creation")) {
        return false;
    }
    bool complete = true;
    for (const char *name : eventNames) {
        if (!checked(PAPI_query_named_event(name), "availability check", name)) {
            complete = false;
        } else if (!checked(PAPI_add_named_event(eventSet, name), "event addition", name)) {
            complete = false;
        }
    }
    ready = complete;
    return ready;
}

bool PAPIMetrics::start() {
    if (!ready) {
        std::fprintf(stderr, "ERROR: Required PAPI event set is incomplete; measurement cannot start.\n");
        return false;
    }
    started = checked(PAPI_start(eventSet), "counter start");
    return started;
}

bool PAPIMetrics::stop() {
    if (!started) {
        std::fprintf(stderr, "ERROR: PAPI counters were not started; no measurements available.\n");
        return false;
    }
    collected = checked(PAPI_stop(eventSet, values), "counter stop");
    if (!collected) {
        return false;
    }
    started = false;
    for (int i = 0; i < 6; ++i) {
        if (values[i] < 0 || (i < 2 && values[i] == 0)) {
            std::fprintf(stderr, "ERROR: PAPI returned an invalid count for %s.\n", eventNames[i]);
            collected = false;
        }
    }
    return collected;
}

bool PAPIMetrics::printResults() const {
    if (!collected) {
        std::printf("PAPI measurement: FAILED; no counter values reported\n");
        return false;
    }
    std::printf("PAPI measurement (main thread): PASS\n");
    for (int i = 0; i < 6; ++i) {
        std::printf("%s (main thread): %lld\n", eventNames[i], values[i]);
    }
    std::printf("IPC (main-thread instructions/cycles): %.6f\n",
                static_cast<double>(values[1]) / values[0]);
    return true;
}

bool PAPIMetrics::cleanup() {
    bool ok = true;
    if (started) {
        long long discarded[6] = {};
        ok = checked(PAPI_stop(eventSet, discarded), "cleanup counter stop");
        started = false;
    }
    if (eventSet != PAPI_NULL) {
        if (!checked(PAPI_cleanup_eventset(eventSet), "event-set cleanup")) {
            ok = false;
        }
        if (!checked(PAPI_destroy_eventset(&eventSet), "event-set destruction")) {
            ok = false;
        }
    }
    if (initialized) {
        PAPI_shutdown();
        initialized = false;
    }
    return ok;
}
