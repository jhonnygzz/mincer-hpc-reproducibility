KOKKOS_PATH ?= /workspace/build/kokkos
KOKKOS_DEVICES = HIP,OpenMP
KOKKOS_ARCH = AMD_GFX908
CXX = hipcc
CXXFLAGS = -O3 -DUSE_OMP=1 -DUSE_MPI=0 -DRAJA_USE_GETTIME -I./includes -I./ -I/usr/local/include
SRC = $(wildcard *.cc)
OBJ = $(SRC:.cc=.o)
EXE = lulesh.kk

default: $(EXE)

include $(KOKKOS_PATH)/Makefile.kokkos

$(EXE): $(OBJ) $(KOKKOS_LINK_DEPENDS)
	$(CXX) $(KOKKOS_LDFLAGS) $(OBJ) $(KOKKOS_LIBS) -L/usr/local/lib -lpapi -lrocm_smi64 -o $@

%.o: %.cc $(KOKKOS_CPP_DEPENDS) lulesh.h lulesh_tuple.h papi_metrics.h validate_result.h
	$(CXX) $(KOKKOS_CPPFLAGS) $(KOKKOS_CXXFLAGS) $(CXXFLAGS) -c $< -o $@

clean: kokkos-clean
	rm -f $(OBJ) $(EXE)

.PHONY: default clean
