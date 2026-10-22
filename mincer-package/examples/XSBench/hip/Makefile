HIPCC ?= hipcc
GPU_ARCH ?= gfx908
PAPI_ROOT ?= /usr/local

PROGRAM := XSBench
SOURCES := Main.cpp io.cpp Simulation.cpp GridInit.cpp XSutils.cpp Materials.cpp rocp_sdk_events.cpp
OBJECTS := $(SOURCES:.cpp=.o)
EVENT_CHECK := build/check_rocp_sdk_events
HIPFLAGS ?= -O3 -Wall -std=c++14
HIPFLAGS += --offload-arch=$(GPU_ARCH) -I$(PAPI_ROOT)/include
LDFLAGS += -L$(PAPI_ROOT)/lib -Wl,-rpath,$(PAPI_ROOT)/lib
LDLIBS += -lpapi -lm

.PHONY: all clean check-rocp-sdk-events

all: $(PROGRAM)

$(PROGRAM): $(OBJECTS) Makefile XSbench_header.h
	$(HIPCC) $(HIPFLAGS) $(LDFLAGS) $(OBJECTS) -o $@ $(LDLIBS)

%.o: %.cpp Makefile XSbench_header.h
	$(HIPCC) $(HIPFLAGS) -c $< -o $@

$(EVENT_CHECK): check_rocp_sdk_events.cpp rocp_sdk_events.cpp rocp_sdk_events.h
	mkdir -p build
	$(HIPCC) $(HIPFLAGS) $(LDFLAGS) check_rocp_sdk_events.cpp rocp_sdk_events.cpp -o $@ $(LDLIBS)

check-rocp-sdk-events: $(EVENT_CHECK)
	./$(EVENT_CHECK)

clean:
	rm -f $(PROGRAM) $(OBJECTS)
	rm -f $(EVENT_CHECK)
