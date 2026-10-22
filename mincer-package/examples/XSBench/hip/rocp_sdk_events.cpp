#include "rocp_sdk_events.h"

const char *const XSBenchGpuEvents[XSBENCH_GPU_EVENT_COUNT] = {
	"rocp_sdk:::SQ_INSTS_SALU",
	"rocp_sdk:::SQ_INSTS_VALU",
	"rocp_sdk:::TCC_HIT",
	"rocp_sdk:::TCC_MISS",
	"rocp_sdk:::TCC_EA_RDREQ_32B",
	"rocp_sdk:::TCC_EA_WRREQ_64B",
	"rocp_sdk:::SQ_INSTS_VMEM_RD",
	"rocp_sdk:::SQ_INSTS_VMEM_WR"
};
