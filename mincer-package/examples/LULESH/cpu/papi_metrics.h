#ifndef MINCER_PAPI_METRICS_H
#define MINCER_PAPI_METRICS_H

#include <papi.h>

// Retains the handoff monitor's main-thread measurement scope.
class PAPIMetrics {
public:
    bool initialize();
    bool start();
    bool stop();
    bool printResults() const;
    bool cleanup();

private:
    int eventSet = PAPI_NULL;
    bool initialized = false;
    bool ready = false;
    bool started = false;
    bool collected = false;
    long long values[6] = {};
};

#endif
