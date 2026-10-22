#include "matrix_kernels.h"

#include <math.h>
#include <stddef.h>

static size_t row_index(int row, int column)
{
    return (size_t)row * MATRIX_SIZE + (size_t)column;
}

static size_t column_index(int row, int column)
{
    return (size_t)column * MATRIX_SIZE + (size_t)row;
}

void initialize_matrices(MatrixData *matrices)
{
    for (int row = 0; row < MATRIX_SIZE; ++row) {
        for (int column = 0; column < MATRIX_SIZE; ++column) {
            size_t row_major = row_index(row, column);
            size_t column_major = column_index(row, column);
            matrices->row_a[row_major] = (double)(row + column);
            matrices->row_b[row_major] = (double)(row - column);
            matrices->column_a[column_major] = (double)(row + column);
            matrices->column_b[column_major] = (double)(row - column);
        }
    }
}

void multiply_row_major(MatrixData *matrices)
{
    for (int row = 0; row < MATRIX_SIZE; ++row) {
        for (int column = 0; column < MATRIX_SIZE; ++column) {
            double sum = 0.0;
            for (int inner = 0; inner < MATRIX_SIZE; ++inner) {
                sum += matrices->row_a[row_index(row, inner)] *
                       matrices->row_b[row_index(inner, column)];
            }
            matrices->row_c[row_index(row, column)] = sum;
        }
    }
}

void multiply_column_major(MatrixData *matrices)
{
    for (int column = 0; column < MATRIX_SIZE; ++column) {
        for (int row = 0; row < MATRIX_SIZE; ++row) {
            double sum = 0.0;
            for (int inner = 0; inner < MATRIX_SIZE; ++inner) {
                sum += matrices->column_a[column_index(row, inner)] *
                       matrices->column_b[column_index(inner, column)];
            }
            matrices->column_c[column_index(row, column)] = sum;
        }
    }
}

static double expected_value(int row, int column)
{
    const long long n = MATRIX_SIZE;
    const long long sum_indices = n * (n - 1) / 2;
    const long long sum_squares = n * (n - 1) * (2 * n - 1) / 6;
    const long long expected =
        (long long)row * sum_indices -
        (long long)row * column * n +
        sum_squares -
        (long long)column * sum_indices;

    return (double)expected;
}

int row_major_matches_reference(const MatrixData *matrices)
{
    for (int row = 0; row < MATRIX_SIZE; ++row) {
        for (int column = 0; column < MATRIX_SIZE; ++column) {
            double actual = matrices->row_c[row_index(row, column)];
            if (!isfinite(actual) || actual != expected_value(row, column)) {
                return 0;
            }
        }
    }
    return 1;
}

int column_major_matches_reference(const MatrixData *matrices)
{
    for (int row = 0; row < MATRIX_SIZE; ++row) {
        for (int column = 0; column < MATRIX_SIZE; ++column) {
            double actual = matrices->column_c[column_index(row, column)];
            if (!isfinite(actual) || actual != expected_value(row, column)) {
                return 0;
            }
        }
    }
    return 1;
}

int matrix_results_match(const MatrixData *matrices)
{
    for (int row = 0; row < MATRIX_SIZE; ++row) {
        for (int column = 0; column < MATRIX_SIZE; ++column) {
            if (matrices->row_c[row_index(row, column)] !=
                matrices->column_c[column_index(row, column)]) {
                return 0;
            }
        }
    }
    return 1;
}
