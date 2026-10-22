#include "rocp_sdk_events.h"

#include <papi.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>

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

int main()
{
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

	int component = PAPI_get_component_index("rocp_sdk");
	if (component < 0) {
		fprintf(stderr, "ERROR: PAPI rocp_sdk component is unavailable\n");
		PAPI_shutdown();
		return EXIT_FAILURE;
	}
	const PAPI_component_info_t *component_info =
		PAPI_get_component_info(component);
	if (component_info == NULL || component_info->disabled) {
		fprintf(stderr, "ERROR: PAPI rocp_sdk component is disabled: %s\n",
			component_info == NULL ? "component information unavailable" :
			component_info->disabled_reason);
		PAPI_shutdown();
		return EXIT_FAILURE;
	}
	printf("PAPI rocp_sdk component enabled; %d required events:\n",
		XSBENCH_GPU_EVENT_COUNT);

	int EventSet = PAPI_NULL;
	retval = PAPI_create_eventset(&EventSet);
	if (retval != PAPI_OK)
		return fail_papi("PAPI_create_eventset", retval, &EventSet);

	for (int i = 0; i < XSBENCH_GPU_EVENT_COUNT; i++) {
		char event_name[256];
		snprintf(event_name, sizeof(event_name), "%s", XSBenchGpuEvents[i]);
		int event_code = 0;
		retval = PAPI_event_name_to_code(event_name, &event_code);
		if (retval != PAPI_OK) {
			fprintf(stderr, "ERROR: Required event %s is unavailable\n",
				XSBenchGpuEvents[i]);
			return fail_papi("PAPI_event_name_to_code", retval, &EventSet);
		}

		PAPI_event_info_t event_info;
		retval = PAPI_get_event_info(event_code, &event_info);
		if (retval != PAPI_OK) {
			fprintf(stderr, "ERROR: Cannot inspect required event %s\n",
				XSBenchGpuEvents[i]);
			return fail_papi("PAPI_get_event_info", retval, &EventSet);
		}

		snprintf(event_name, sizeof(event_name), "%s", XSBenchGpuEvents[i]);
		retval = PAPI_add_named_event(EventSet, event_name);
		if (retval != PAPI_OK) {
			fprintf(stderr, "ERROR: Cannot add required event %s\n",
				XSBenchGpuEvents[i]);
			return fail_papi("PAPI_add_named_event", retval, &EventSet);
		}
		printf("  %s: available and added\n", XSBenchGpuEvents[i]);
	}

	if (cleanup_papi(&EventSet) != 0)
		return EXIT_FAILURE;
	printf("All required rocp_sdk events are available and addable together.\n");
	return EXIT_SUCCESS;
}
