#include "papi_metrics.h"

int main() {
    PAPIMetrics metrics;
    bool ready = metrics.initialize();
    bool cleaned = metrics.cleanup();
    return ready && cleaned ? 0 : 1;
}
