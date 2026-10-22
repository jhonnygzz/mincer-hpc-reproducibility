#include "matrix_kernels.h"

#include <stdio.h>

int main(void)
{
    static MatrixData matrices;

    initialize_matrices(&matrices);
    multiply_row_major(&matrices);
    multiply_column_major(&matrices);

    if (!row_major_matches_reference(&matrices)) {
        fputs("Row-major output did not match the analytical reference.\n", stderr);
        return 1;
    }
    if (!column_major_matches_reference(&matrices)) {
        fputs("Column-major output did not match the analytical reference.\n", stderr);
        return 1;
    }
    if (!matrix_results_match(&matrices)) {
        fputs("Row-major and column-major outputs differed.\n", stderr);
        return 1;
    }

    puts("Both matrix layouts match the analytical reference.");
    return 0;
}
