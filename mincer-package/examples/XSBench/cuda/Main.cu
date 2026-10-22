#include "XSbench_header.cuh"
#include <papi.h>
#include <stdio.h>
#include <unistd.h>

static void check_papi(int result, const char *operation)
{
	if (result != PAPI_OK) {
		fprintf(stderr, "ERROR: %s: %s (%d)\n", operation, PAPI_strerror(result), result);
		fprintf(stderr, "No valid monitoring result was produced. Check PAPI components, event support, and NVIDIA profiling permissions.\n");
		exit(EXIT_FAILURE);
	}
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

	// PAPI initialization
	int retval = PAPI_library_init(PAPI_VER_CURRENT);
	if (retval != PAPI_VER_CURRENT) {
		fprintf(stderr, "PAPI library init error: %d\n", retval);
		return 1;
	}

	int EventSet = PAPI_NULL;
	int NVMLEventSet = PAPI_NULL;  // Separate event set for NVML
	long long values[4];  // Array for CUDA events (FP, DRAM, L1, L2)
	long long nvml_values[2];  // Array for NVML events (power, temp)
	check_papi(PAPI_create_eventset(&EventSet), "create CUDA event set");
	check_papi(PAPI_create_eventset(&NVMLEventSet), "create NVML event set");

	// Add FP64 floating-point operations event
	retval = PAPI_add_named_event(EventSet, "cuda:::sm__inst_executed_pipe_fp64");
	if (retval != PAPI_OK) {
		printf("Error adding CUDA FP64 event! Trying FP32...\n");
		retval = PAPI_add_named_event(EventSet, "cuda:::sm__inst_executed_pipe_fp32");
		if (retval != PAPI_OK) {
			check_papi(retval, "add CUDA FP32 event after FP64 was unavailable");
		}
		printf("Using CUDA FP32 instructions executed\n");
	} else {
		printf("Using CUDA FP64 instructions executed\n");
	}

	// Add memory bandwidth event
	retval = PAPI_add_named_event(EventSet, "cuda:::dram__bytes");
	if (retval != PAPI_OK) {
		check_papi(retval, "add CUDA DRAM bytes event");
	} else {
		printf("Also measuring CUDA DRAM bytes transferred\n");
	}

	// Add cache statistics
	retval = PAPI_add_named_event(EventSet, "cuda:::l1tex__t_bytes");
	if (retval != PAPI_OK) {
		check_papi(retval, "add CUDA L1 texture cache event");
	} else {
		printf("Also measuring L1 texture cache bytes\n");
	}

	retval = PAPI_add_named_event(EventSet, "cuda:::lts__t_bytes");
	if (retval != PAPI_OK) {
		check_papi(retval, "add CUDA L2 cache event");
	} else {
		printf("Also measuring L2 cache bytes\n");
	}

	// Add NVML events for power and temperature monitoring
	cudaDeviceProp device;
	int device_id;
	gpuErrchk(cudaGetDevice(&device_id));
	gpuErrchk(cudaGetDeviceProperties(&device, device_id));
	for (char *character = device.name; *character; ++character) {
		if (*character == ' ') *character = '_';
	}
	char event_name[512];
	snprintf(event_name, sizeof(event_name), "nvml:::%s:device_%d:power", device.name, device_id);
	retval = PAPI_add_named_event(NVMLEventSet, event_name);
	if (retval != PAPI_OK) {
		check_papi(retval, event_name);
	} else {
		printf("Also measuring GPU power consumption\n");
	}

	snprintf(event_name, sizeof(event_name), "nvml:::%s:device_%d:temperature", device.name, device_id);
	retval = PAPI_add_named_event(NVMLEventSet, event_name);
	if (retval != PAPI_OK) {
		check_papi(retval, event_name);
	} else {
		printf("Also measuring GPU temperature\n");
	}	// Process CLI Fields -- store in "Inputs" structure
	Inputs in = read_CLI( argc, argv );

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
	omp_start = get_time();

	// Start counting FLOPs and NVML monitoring
	check_papi(PAPI_start(EventSet), "start CUDA counters");
	if (PAPI_num_events(NVMLEventSet) > 0) {
		check_papi(PAPI_start(NVMLEventSet), "start NVML monitoring");
	}	// Run simulation
	if( in.simulation_method == EVENT_BASED )
	{
		if( in.kernel_id == 0 )
			verification = run_event_based_simulation_baseline(in, GSD, mype);
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
		else
		{
			printf("Error: No kernel ID %d found!\n", in.kernel_id);
			exit(1);
		}
	}
	else
	{
		printf("History-based simulation not implemented in CUDA code. Instead,\nuse the event-based method with \"-m event\" argument.\n");
		exit(1);
	}

	if( mype == 0)
	{
		printf("\n" );
		printf("Simulation complete.\n" );
	}

	// End Simulation Timer
	omp_end = get_time();

    // Stop counting and print results
    check_papi(PAPI_stop(EventSet, values), "stop CUDA counters");
    if (PAPI_num_events(NVMLEventSet) > 0) {
        check_papi(PAPI_stop(NVMLEventSet, nvml_values), "stop NVML monitoring");
    }

    // Get number of events added to determine output
    int num_events = PAPI_num_events(EventSet);
    int num_nvml_events = PAPI_num_events(NVMLEventSet);

    printf("=== PAPI CUDA Performance Metrics ===\n");
    printf("CUDA FP64/FP32 instructions executed: %lld\n", values[0]);

    if (num_events >= 2) {
        printf("CUDA DRAM bytes transferred: %lld (%.2f GB)\n", values[1], (double)values[1] / (1024*1024*1024));
        printf("Memory bandwidth (MB/s): %.2f\n", (double)values[1] / (omp_end - omp_start) / (1024*1024));
    }

    if (num_events >= 3) {
        printf("L1 texture cache bytes: %lld (%.2f GB)\n", values[2], (double)values[2] / (1024*1024*1024));
        if (values[1] > 0)
            printf("L1/DRAM traffic ratio: %.2f%%\n", 100.0 * (double)values[2] / values[1]);
    }

    if (num_events >= 4) {
        printf("L2 cache bytes: %lld (%.2f GB)\n", values[3], (double)values[3] / (1024*1024*1024));
        if (values[1] > 0)
            printf("L2/DRAM traffic ratio: %.2f%%\n", 100.0 * (double)values[3] / values[1]);

        // Calculate cache efficiency metrics
        if (values[0] > 0) {
            double l1_efficiency = (double)values[2] / values[0];
            double dram_efficiency = (double)values[1] / values[0];
            printf("Bytes/FP instruction: %.2f (L1), %.2f (DRAM)\n", l1_efficiency, dram_efficiency);
        }
    }

    // Print NVML results
    if (num_nvml_events > 0) {
        printf("\n=== NVML GPU Monitoring Metrics ===\n");
        if (num_nvml_events >= 1) {
            // Power might be in milliwatts, convert to watts
            double power_watts = (double)nvml_values[0] / 1000.0;
            if (power_watts > 500) {
                // If still unreasonably high, it might be in different units
                printf("GPU power consumption: %lld mW (%.2f W)\n", nvml_values[0], power_watts);
            } else {
                printf("GPU power consumption: %.2f watts\n", power_watts);
            }
        }
        if (num_nvml_events >= 2) {
            printf("GPU temperature: %lld°C\n", nvml_values[1]);
        }
    }

    printf("========================================\n");	// Release device memory
	release_device_memory(GSD);

	// Final Hash Step
	verification = verification % 999983;

	// Print / Save Results and Exit
	int is_invalid_result = print_results( in, mype, omp_end-omp_start, nprocs, verification );

	check_papi(PAPI_cleanup_eventset(EventSet), "clean CUDA event set");
	check_papi(PAPI_destroy_eventset(&EventSet), "destroy CUDA event set");
	check_papi(PAPI_cleanup_eventset(NVMLEventSet), "clean NVML event set");
	check_papi(PAPI_destroy_eventset(&NVMLEventSet), "destroy NVML event set");
	PAPI_shutdown();
	return is_invalid_result;
}

	/*
	To list available CUDA events inside your container, run:
		papi_component_avail
		papi_event_chooser CUDA
	This will show all supported CUDA events for your system and PAPI build.
	*/
