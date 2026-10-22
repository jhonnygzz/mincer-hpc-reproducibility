#ifndef MINCER_HIP_PAPI_METRICS_H
#define MINCER_HIP_PAPI_METRICS_H

#include <papi.h>
#include <hip/hip_runtime.h>
#include <rocm_smi/rocm_smi.h>
#include <cstdio>
#include <cstdint>
#include <initializer_list>
#include <string>

class PAPIMetrics {
    int counters = PAPI_NULL;
    int sensors = PAPI_NULL;
    long long counts[5] = {};
    long long samples[3] = {};
    bool initialized = false;
    bool countersRunning = false;
    bool sensorsRunning = false;
    bool collected = false;
    std::string counterNames[5];
    std::string sensorNames[3];

    static bool check(int result, const char *operation) {
        if (result == PAPI_OK) return true;
        std::fprintf(stderr, "ERROR: %s: %s (%d)\n", operation,
                     PAPI_strerror(result), result);
        return false;
    }

    static bool component(const char *name) {
        int index = PAPI_get_component_index(name);
        const auto *info = index < 0 ? nullptr : PAPI_get_component_info(index);
        if (!info || (info->disabled != PAPI_OK && info->disabled != PAPI_EDELAY_INIT)) {
            std::fprintf(stderr, "ERROR: Required PAPI component %s unavailable: %s\n",
                         name, info ? info->disabled_reason : "not compiled in");
            return false;
        }
        return true;
    }

public:
    bool initialize() {
        int version = PAPI_library_init(PAPI_VER_CURRENT);
        if (version != PAPI_VER_CURRENT) {
            std::fprintf(stderr, "ERROR: PAPI initialization returned %d.\n", version);
            if (version > 0) PAPI_shutdown();
            return false;
        }
        initialized = true;
        if (!component("rocm") || !component("rocm_smi")) return false;
        if (!check(PAPI_query_named_event("rocm:::SQ_INSTS_SALU:device=0"),
                   "initialize legacy ROCm native events before HIP")) return false;

        int devices = 0;
        char busId[32] = {};
        if (hipGetDeviceCount(&devices) != hipSuccess || devices != 1 ||
            hipDeviceGetPCIBusId(busId, sizeof(busId), 0) != hipSuccess) {
            std::fprintf(stderr, "ERROR: Expose exactly one HIP GPU with ROCR_VISIBLE_DEVICES.\n");
            return false;
        }
        unsigned domain = 0, bus = 0, device = 0, function = 0;
        if (std::sscanf(busId, "%x:%x:%x.%x", &domain, &bus, &device, &function) != 4) {
            std::fprintf(stderr, "ERROR: Invalid HIP PCI bus identifier: %s.\n", busId);
            return false;
        }
        uint64_t pci = (uint64_t(domain) << 32) | (bus << 8) | (device << 3) | function;
        if (rsmi_init(0) != RSMI_STATUS_SUCCESS) {
            std::fprintf(stderr, "ERROR: ROCm SMI initialization failed.\n");
            return false;
        }
        uint32_t count = 0;
        int selected = -1;
        bool smiOK = rsmi_num_monitor_devices(&count) == RSMI_STATUS_SUCCESS;
        for (uint32_t i = 0; smiOK && i < count; ++i) {
            uint64_t id = 0;
            smiOK = rsmi_dev_pci_id_get(i, &id) == RSMI_STATUS_SUCCESS;
            if (smiOK && id == pci) selected = static_cast<int>(i);
        }
        if (rsmi_shut_down() != RSMI_STATUS_SUCCESS) smiOK = false;
        if (!smiOK || selected < 0) {
            std::fprintf(stderr, "ERROR: Cannot match HIP GPU %s to ROCm SMI device.\n", busId);
            return false;
        }
        std::printf("Measurement GPU: HIP device 0, PCI %s, SMI device %d\n", busId, selected);
        const char *metrics[] = {"SQ_INSTS_SALU", "SQ_INSTS_VALU", "SQ_WAVES",
                                 "TCC_HIT_sum", "TCC_MISS_sum"};
        const char *monitoring[] = {"busy_percent", "power_average", "temp_current"};
        if (!check(PAPI_create_eventset(&counters), "create ROCm event set") ||
            !check(PAPI_create_eventset(&sensors), "create SMI event set")) return false;
        for (int i = 0; i < 5; ++i) {
            counterNames[i] = std::string("rocm:::") + metrics[i] + ":device=0";
            if (!check(PAPI_query_named_event(counterNames[i].c_str()), counterNames[i].c_str()) ||
                !check(PAPI_add_named_event(counters, counterNames[i].c_str()),
                       counterNames[i].c_str())) return false;
        }
        for (int i = 0; i < 3; ++i) {
            sensorNames[i] = std::string("rocm_smi:::") + monitoring[i] +
                             ":device=" + std::to_string(selected) +
                             (i == 0 ? "" : ":sensor=0");
            if (!check(PAPI_query_named_event(sensorNames[i].c_str()), sensorNames[i].c_str()) ||
                !check(PAPI_add_named_event(sensors, sensorNames[i].c_str()),
                       sensorNames[i].c_str())) return false;
        }
        std::printf("Required PAPI events available: 5 ROCm counters, 3 ROCm SMI sensors.\n");
        return true;
    }

    bool start() {
        countersRunning = check(PAPI_start(counters), "start ROCm counters");
        if (!countersRunning) return false;
        sensorsRunning = check(PAPI_start(sensors), "start ROCm SMI sensors");
        return sensorsRunning;
    }

    bool stop() {
        bool ok = true;
        if (countersRunning) {
            ok = check(PAPI_stop(counters, counts), "stop ROCm counters");
            countersRunning = false;
        } else ok = false;
        if (sensorsRunning) {
            if (!check(PAPI_stop(sensors, samples), "stop ROCm SMI sensors")) ok = false;
            sensorsRunning = false;
        } else ok = false;
        collected = ok;
        return ok;
    }

    bool printResults() const {
        if (!collected) {
            std::fprintf(stderr, "ERROR: Complete required PAPI measurements were not collected.\n");
            return false;
        }
        for (int i = 0; i < 5; ++i)
            if (counts[i] < 0) {
                std::fprintf(stderr, "ERROR: Negative GPU counter: %s.\n", counterNames[i].c_str());
                return false;
            }
        if (samples[0] < 0 || samples[0] > 100 || samples[1] < 0 || samples[2] < 0) {
            std::fprintf(stderr, "ERROR: Invalid ROCm SMI sensor values.\n");
            return false;
        }
        const char *units[] = {"%", "uW", "mC"};
        for (int i = 0; i < 5; ++i)
            std::printf("%s: %lld\n", counterNames[i].c_str(), counts[i]);
        for (int i = 0; i < 3; ++i)
            std::printf("%s: %lld %s\n", sensorNames[i].c_str(), samples[i], units[i]);
        double accesses = double(counts[3]) + double(counts[4]);
        if (accesses > 0)
            std::printf("TCC hit fraction: %.2f%%\n", 100.0 * double(counts[3]) / accesses);
        std::printf("SMI readings are endpoint samples, not whole-run averages or energy.\n");
        std::printf("PAPI measurement: PASS\n");
        return true;
    }

    bool cleanup() {
        bool ok = true;
        if (countersRunning || sensorsRunning) {
            if (!stop()) ok = false;
        }
        for (int *set : {&counters, &sensors}) {
            if (*set == PAPI_NULL) continue;
            if (!check(PAPI_cleanup_eventset(*set), "cleanup event set")) ok = false;
            if (!check(PAPI_destroy_eventset(set), "destroy event set")) ok = false;
        }
        if (initialized) PAPI_shutdown();
        initialized = false;
        return ok;
    }
};

#endif
