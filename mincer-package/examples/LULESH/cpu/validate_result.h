#ifndef MINCER_VALIDATE_RESULT_H
#define MINCER_VALIDATE_RESULT_H

#include <algorithm>
#include <cmath>
#include <cstdio>

inline bool validateResult(const double *energy, int size, int cycles) {
    if (size != 96 || cycles != 10) {
        std::fprintf(stderr, "ERROR: Numerical reference requires size 96 and exactly 10 iterations.\n");
        std::printf("LULESH numerical correctness: FAILED\n");
        return false;
    }
    bool valid = true;
    const int count = size * size * size;
    for (int i = 0; i < count; ++i) {
        if (!std::isfinite(energy[i]) || energy[i] < 0.0) {
            std::fprintf(stderr, "ERROR: Non-finite or negative energy at element %d.\n", i);
            valid = false;
            break;
        }
    }
    // The PDF gives six decimals in scientific notation; allow rounding and FP variation.
    const double expectedOrigin = 3.833852e8;
    if (!std::isfinite(energy[0]) ||
        std::abs(energy[0] - expectedOrigin) > expectedOrigin * 1.0e-6) {
        std::fprintf(stderr, "ERROR: Origin energy %.12e differs from reference %.6e.\n",
                     energy[0], expectedOrigin);
        valid = false;
    }
    for (int j = 0; j < size; ++j) {
        for (int k = j + 1; k < size; ++k) {
            const double a = energy[j * size + k];
            const double b = energy[k * size + j];
            if (std::abs(a - b) > 1.0e-10 * std::max(1.0, std::max(std::abs(a), std::abs(b)))) {
                std::fprintf(stderr, "ERROR: Plane-zero energy symmetry failed at (%d, %d).\n", j, k);
                valid = false;
                j = size;
                break;
            }
        }
    }
    std::printf("LULESH numerical correctness: %s\n", valid ? "PASS" : "FAILED");
    return valid;
}

#endif
