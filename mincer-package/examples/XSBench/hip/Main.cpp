#include "XSbench_header.h"

static int cleanup_papi(int *event_set)
{
	int failed = 0;

	if (*event_set != PAPI_NULL) {
		int retval = PAPI_cleanup_eventset(*event_set);
		if (retval != PAPI_OK) {
			fprintf(stderr, "ERROR: PAPI_cleanup_eventset failed: %s\n",
				PAPI_strerror(retval));
			failed = 1;
		}

		retval = PAPI_destroy_eventset(event_set);
		if (retval != PAPI_OK) {
			fprintf(stderr, "ERROR: PAPI_destroy_eventset failed: %s\n",
				PAPI_strerror(retval));
			failed = 1;
		}
	}

	PAPI_shutdown();
	return failed;
}

static int fail_papi(const char *operation, int retval, int *event_set)
{
	fprintf(stderr, "ERROR: %s failed: %s (PAPI code %d)\n",
		operation, PAPI_strerror(retval), retval);
	cleanup_papi(event_set);
	return EXIT_FAILURE;
}

int main( int argc, char* argv[] )
{
	// =====================================================================
	// Initialization & Command Line Read-In
	// =====================================================================
	int version = 20;
	int mype = 0;
	double omp_start, omp_end;
	int nprocs = 1;
	unsigned long long verification;
	Inputs in = read_CLI(argc, argv);

	int retval = PAPI_library_init(PAPI_VER_CURRENT);
	if (retval != PAPI_VER_CURRENT) {
		if (retval > 0) {
			fprintf(stderr, "ERROR: PAPI version mismatch: expected %d, got %d\n",
				PAPI_VER_CURRENT, retval);
			PAPI_shutdown();
		} else {
			fprintf(stderr, "ERROR: PAPI_library_init failed: %s (PAPI code %d)\n",
				PAPI_strerror(retval), retval);
		}
		return EXIT_FAILURE;
	}

	int EventSet = PAPI_NULL;
	long long gpu_counter_values[XSBENCH_GPU_EVENT_COUNT];
	if ((retval = PAPI_create_eventset(&EventSet)) != PAPI_OK) {
		return fail_papi("PAPI_create_eventset", retval, &EventSet);
	}
	for (int i = 0; i < XSBENCH_GPU_EVENT_COUNT; i++) {
		retval = PAPI_add_named_event(EventSet, XSBenchGpuEvents[i]);
		if (retval != PAPI_OK) {
			fprintf(stderr, "ERROR: Required event %s is unavailable\n",
				XSBenchGpuEvents[i]);
			return fail_papi("PAPI_add_named_event", retval, &EventSet);
		}
	}

	// Print-out of Input Summary
	if( mype == 0 )
		print_inputs( in, nprocs, version );

	// =====================================================================
	// Prepare Nuclide Energy Grids, Unionized Energy Grid, & Material Data
	// This is not reflective of a real Monte Carlo simulation workload,
	// therefore, do not profile this region!
	// =====================================================================

	SimulationData SD;

	// If read from file mode is selected, skip initialization and load
	// all simulation data structures from file instead
	if( in.binary_mode == READ )
		SD = binary_read(in);
	else
		SD = grid_init_do_not_profile( in, mype );

	// If writing from file mode is selected, write all simulation data
	// structures to file
	if( in.binary_mode == WRITE && mype == 0 )
		binary_write(in, SD);

	// Move data to GPU
	SimulationData GSD = move_simulation_data_to_device( in, mype, SD );

	// =====================================================================
	// Cross Section (XS) Parallel Lookup Simulation
	// This is the section that should be profiled, as it reflects a
	// realistic continuous energy Monte Carlo macroscopic cross section
	// lookup kernel.
	// =====================================================================
	if( mype == 0 )
	{
		printf("\n");
		border_print();
		center_print("SIMULATION", 79);
		border_print();
	}

	// Start Simulation Timer
	hipError_t hip_status = hipDeviceSynchronize();
	if (hip_status != hipSuccess) {
		fprintf(stderr, "ERROR: HIP synchronization before measurement failed: %s\n",
			hipGetErrorString(hip_status));
		cleanup_papi(&EventSet);
		return EXIT_FAILURE;
	}
	omp_start = get_time();

	// Start GPU performance measurement
	if ((retval = PAPI_start(EventSet)) != PAPI_OK) {
		return fail_papi("PAPI_start", retval, &EventSet);
	}

	// Run simulation
	if( in.simulation_method == EVENT_BASED )
	{
		if( in.kernel_id == 0 )
			verification = run_event_based_simulation_baseline(in, GSD, mype);
/*
		else if( in.kernel_id == 1 )
			verification = run_event_based_simulation_optimization_1(in, GSD, mype);
		else if( in.kernel_id == 2 )
			verification = run_event_based_simulation_optimization_2(in, GSD, mype);
		else if( in.kernel_id == 3 )
			verification = run_event_based_simulation_optimization_3(in, GSD, mype);
		else if( in.kernel_id == 4 )
			verification = run_event_based_simulation_optimization_4(in, GSD, mype);
		else if( in.kernel_id == 5 )
			verification = run_event_based_simulation_optimization_5(in, GSD, mype);
		else if( in.kernel_id == 6 )
			verification = run_event_based_simulation_optimization_6(in, GSD, mype);
*/
		else
		{
			fprintf(stderr, "ERROR: No kernel ID %d found\n", in.kernel_id);
			long long discarded[XSBENCH_GPU_EVENT_COUNT];
			retval = PAPI_stop(EventSet, discarded);
			if (retval != PAPI_OK)
				fprintf(stderr, "ERROR: PAPI_stop during cleanup failed: %s\n",
					PAPI_strerror(retval));
			cleanup_papi(&EventSet);
			return EXIT_FAILURE;
		}
	}
	else
	{
		fprintf(stderr, "ERROR: HIP XSBench supports the event-based method; use -m event\n");
		long long discarded[XSBENCH_GPU_EVENT_COUNT];
		retval = PAPI_stop(EventSet, discarded);
		if (retval != PAPI_OK)
			fprintf(stderr, "ERROR: PAPI_stop during cleanup failed: %s\n",
				PAPI_strerror(retval));
		cleanup_papi(&EventSet);
		return EXIT_FAILURE;
	}

	hip_status = hipDeviceSynchronize();
	if (hip_status != hipSuccess) {
		fprintf(stderr, "ERROR: HIP synchronization after measurement failed: %s\n",
			hipGetErrorString(hip_status));
		long long discarded[XSBENCH_GPU_EVENT_COUNT];
		retval = PAPI_stop(EventSet, discarded);
		if (retval != PAPI_OK)
			fprintf(stderr, "ERROR: PAPI_stop during cleanup failed: %s\n",
				PAPI_strerror(retval));
		cleanup_papi(&EventSet);
		return EXIT_FAILURE;
	}

	// End Simulation Timer
	omp_end = get_time();

	// Stop GPU performance measurement
	if ((retval = PAPI_stop(EventSet, gpu_counter_values)) != PAPI_OK) {
		return fail_papi("PAPI_stop", retval, &EventSet);
	}

	if (cleanup_papi(&EventSet) != 0)
		return EXIT_FAILURE;

	if( mype == 0)
	{
		printf("\n" );
		printf("Simulation complete.\n" );
	}

	// Final Hash Step
	verification = verification % 999983;

	// Print / Save Results and Exit
	int is_invalid_result = print_results(
		in, mype, omp_end - omp_start, nprocs, verification, gpu_counter_values);

	return is_invalid_result;
}