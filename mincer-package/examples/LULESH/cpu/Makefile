KOKKOS_PATH ?= /workspace/build/kokkos
KOKKOS_DEVICES = OpenMP
SRC = $(wildcard *.cc) papi_metrics.cpp
OBJ = $(SRC:.cc=.o)
OBJ := $(OBJ:.cpp=.o)
CXX = g++
CXXFLAGS = -O3 -DUSE_OMP=1 -DUSE_MPI=0 -DRAJA_USE_GETTIME -I./includes -I./
EXE = lulesh.kk

default: $(EXE)

include $(KOKKOS_PATH)/Makefile.kokkos

$(EXE): $(OBJ) $(KOKKOS_LINK_DEPENDS)
	$(CXX) $(KOKKOS_LDFLAGS) $(OBJ) $(KOKKOS_LIBS) -lpapi -o $@

%.o: %.cc $(KOKKOS_CPP_DEPENDS) lulesh.h lulesh_tuple.h papi_metrics.h validate_result.h
	$(CXX) $(KOKKOS_CPPFLAGS) $(KOKKOS_CXXFLAGS) $(CXXFLAGS) -c $< -o $@

%.o: %.cpp papi_metrics.h
	$(CXX) $(KOKKOS_CPPFLAGS) $(KOKKOS_CXXFLAGS) $(CXXFLAGS) -c $< -o $@

clean: kokkos-clean
	rm -f $(OBJ) $(EXE)

.PHONY: default clean
