#include "matrix_kernels.h"

#include <papi.h>

#include <stdio.h>

typedef void (*matrix_kernel)(MatrixData *);

typedef struct {
    long long instructions;
    long long cycles;
    int collected;
} Measurement;

static int measurement_errors;

static void report_papi_error(const char *operation, int status)
{
    const char *message = PAPI_strerror(status);
    fprintf(stderr, "ERROR: PAPI %s failed: %s (status %d)\n",
            operation, message ? message : "unknown PAPI error", status);
    ++measurement_errors;
}

static int query_required_events(void)
{
    int instructions_status = PAPI_query_named_event("PAPI_TOT_INS");
    int cycles_status = PAPI_query_named_event("PAPI_TOT_CYC");

    if (instructions_status != PAPI_OK) {
        report_papi_error("event availability check for PAPI_TOT_INS",
                          instructions_status);
    }
    if (cycles_status != PAPI_OK) {
        report_papi_error("event availability check for PAPI_TOT_CYC",
                          cycles_status);
    }
    return instructions_status == PAPI_OK && cycles_status == PAPI_OK;
}

static Measurement measure_kernel(const char *name,
                                  matrix_kernel kernel,
                                  MatrixData *matrices,
                                  int events_available)
{
    Measurement measurement = {0, 0, 0};
    int event_set = PAPI_NULL;
    int created = 0;
    int can_start = 1;
    int started = 0;

    int status = PAPI_create_eventset(&event_set);
    if (status != PAPI_OK) {
        report_papi_error("PAPI_create_eventset", status);
        can_start = 0;
    } else {
        created = 1;
    }

    if (created) {
        int instructions_status =
            PAPI_add_named_event(event_set, "PAPI_TOT_INS");
        int cycles_status = PAPI_add_named_event(event_set, "PAPI_TOT_CYC");
        if (instructions_status != PAPI_OK) {
            report_papi_error("event addition for PAPI_TOT_INS",
                              instructions_status);
            can_start = 0;
        }
        if (cycles_status != PAPI_OK) {
            report_papi_error("event addition for PAPI_TOT_CYC", cycles_status);
            can_start = 0;
        }
    }

    if (!events_available) {
        can_start = 0;
    }

    if (can_start) {
        int status = PAPI_start(event_set);
        if (status != PAPI_OK) {
            report_papi_error("PAPI_start", status);
        } else {
            started = 1;
        }
    }

    kernel(matrices);

    if (started) {
        long long values[2] = {0, 0};
        int status = PAPI_stop(event_set, values);
        if (status != PAPI_OK) {
            report_papi_error("PAPI_stop", status);
        } else if (values[0] <= 0 || values[1] <= 0) {
            fprintf(stderr,
                    "ERROR: PAPI returned non-positive required counters for %s; "
                    "no measurement will be reported.\n",
                    name);
            ++measurement_errors;
        } else {
            measurement.instructions = values[0];
            measurement.cycles = values[1];
            measurement.collected = 1;
        }
    }

    if (created) {
        int status = PAPI_cleanup_eventset(event_set);
        if (status != PAPI_OK) {
            report_papi_error("PAPI_cleanup_eventset", status);
        }
        status = PAPI_destroy_eventset(&event_set);
        if (status != PAPI_OK) {
            report_papi_error("PAPI_destroy_eventset", status);
        }
    }

    return measurement;
}

static int report_correctness(const char *name, int matches_reference)
{
    printf("%s numerical correctness: %s\n", name,
           matches_reference ? "PASS" : "FAIL");
    return matches_reference;
}

static void report_measurement(const char *name, Measurement measurement)
{
    if (!measurement.collected) {
        printf("%s PAPI measurement: FAILED; no counter values reported\n", name);
        return;
    }

    printf("%s PAPI measurement: PASS\n", name);
    printf("  PAPI_TOT_INS: %lld\n", measurement.instructions);
    printf("  PAPI_TOT_CYC: %lld\n", measurement.cycles);
    printf("  IPC (instructions/cycles): %.6f\n",
           (double)measurement.instructions / (double)measurement.cycles);
}

int main(void)
{
    static MatrixData matrices;
    Measurement row_measurement = {0, 0, 0};
    Measurement column_measurement = {0, 0, 0};
    int papi_initialized = 0;
    int events_available = 0;

    initialize_matrices(&matrices);

    int version = PAPI_library_init(PAPI_VER_CURRENT);
    if (version != PAPI_VER_CURRENT) {
        if (version < PAPI_OK) {
            report_papi_error("PAPI_library_init", version);
        } else {
            fprintf(stderr,
                    "ERROR: PAPI version mismatch: expected 0x%x, received 0x%x\n",
                    PAPI_VER_CURRENT, version);
            ++measurement_errors;
        }
    } else {
        papi_initialized = 1;
        events_available = query_required_events();
    }

    if (papi_initialized) {
        row_measurement = measure_kernel(
            "Row-major", multiply_row_major, &matrices, events_available);
        column_measurement = measure_kernel(
            "Column-major", multiply_column_major, &matrices, events_available);
        PAPI_shutdown();
    } else {
        multiply_row_major(&matrices);
        multiply_column_major(&matrices);
    }

    int row_correct = row_major_matches_reference(&matrices);
    int column_correct = column_major_matches_reference(&matrices);
    int layouts_match = matrix_results_match(&matrices);

    report_correctness("Row-major", row_correct);
    report_correctness("Column-major", column_correct);
    printf("Row-major and column-major outputs match: %s\n",
           layouts_match ? "PASS" : "FAIL");
    report_measurement("Row-major", row_measurement);
    report_measurement("Column-major", column_measurement);

    int correctness_passed = row_correct && column_correct && layouts_match;
    if (!correctness_passed || measurement_errors != 0 ||
        !row_measurement.collected || !column_measurement.collected) {
        fprintf(stderr,
                "ERROR: Matrix multiplication failed correctness or required "
                "PAPI measurement checks.\n");
        return 1;
    }

    puts("Matrix multiplication completed: correctness and PAPI measurements passed.");
    return 0;
}
