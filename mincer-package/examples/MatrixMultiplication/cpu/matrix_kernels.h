#ifndef MINCER_MATRIX_KERNELS_H
#define MINCER_MATRIX_KERNELS_H

#define MATRIX_SIZE 256

typedef struct {
    double row_a[MATRIX_SIZE * MATRIX_SIZE];
    double row_b[MATRIX_SIZE * MATRIX_SIZE];
    double row_c[MATRIX_SIZE * MATRIX_SIZE];
    double column_a[MATRIX_SIZE * MATRIX_SIZE];
    double column_b[MATRIX_SIZE * MATRIX_SIZE];
    double column_c[MATRIX_SIZE * MATRIX_SIZE];
} MatrixData;

void initialize_matrices(MatrixData *matrices);
void multiply_row_major(MatrixData *matrices);
void multiply_column_major(MatrixData *matrices);
int row_major_matches_reference(const MatrixData *matrices);
int column_major_matches_reference(const MatrixData *matrices);
int matrix_results_match(const MatrixData *matrices);

#endif
