KOKKOS_PATH ?= /workspace/build/kokkos
KOKKOS_DEVICES = Cuda
KOKKOS_ARCH ?= Turing75
KOKKOS_CUDA_OPTIONS = enable_lambda
PAPI_ROOT ?= /usr/local/papi
SRC = $(wildcard *.cc)
OBJ = $(SRC:.cc=.o)
CXX = $(KOKKOS_PATH)/bin/nvcc_wrapper
CXXFLAGS = -O3 -DUSE_OMP=0 -DUSE_MPI=0 -DRAJA_USE_GETTIME -I./includes -I./ -I$(PAPI_ROOT)/include
EXE = lulesh.kk

default: $(EXE)

include $(KOKKOS_PATH)/Makefile.kokkos

$(EXE): $(OBJ) $(KOKKOS_LINK_DEPENDS)
	$(CXX) $(KOKKOS_LDFLAGS) $(OBJ) $(KOKKOS_LIBS) -L$(PAPI_ROOT)/lib -lpapi -o $@

%.o: %.cc $(KOKKOS_CPP_DEPENDS) lulesh.h lulesh_tuple.h
	$(CXX) $(KOKKOS_CPPFLAGS) $(KOKKOS_CXXFLAGS) $(CXXFLAGS) -c $< -o $@

clean: kokkos-clean
	rm -f $(OBJ) $(EXE)

.PHONY: default clean
