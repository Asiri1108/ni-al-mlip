#!/usr/bin/env bash
set -euo pipefail

ROOT=/workspace/ni_al
SRC=$ROOT/tools/qe_gpu/sources/q-e-qe-7.6
BUILD=$ROOT/tools/qe_gpu/builds/sm_89
INSTALL=$ROOT/tools/qe_gpu/install/sm_89
NVROOT=$ROOT/tools/qe_gpu/nvhpc/Linux_x86_64/26.5
LOG=$ROOT/logs/qe_gpu_build

export PATH="$NVROOT/compilers/bin:$PATH"
export LD_LIBRARY_PATH="$NVROOT/compilers/lib:$NVROOT/cuda/12.9/lib64:${LD_LIBRARY_PATH:-}"
mkdir -p "$BUILD" "$INSTALL" "$LOG"

{
  date -u +%Y-%m-%dT%H:%M:%SZ
  nvfortran --version
  nvc --version
  nvidia-smi --query-gpu=name,driver_version,compute_cap --format=csv
  cmake -S "$SRC" -B "$BUILD" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$INSTALL" \
    -DCMAKE_Fortran_COMPILER="$NVROOT/compilers/bin/nvfortran" \
    -DCMAKE_C_COMPILER="$NVROOT/compilers/bin/nvc" \
    -DQE_GPU='openacc;cuda' \
    -DQE_GPU_ARCHS=sm_89 \
    -DQE_ENABLE_MPI=OFF \
    -DQE_ENABLE_OPENMP=ON \
    -DQE_ENABLE_SCALAPACK=OFF
} 2>&1 | tee "$LOG/configure_sm89.log"

cmake --build "$BUILD" --target pw -j24 2>&1 | tee "$LOG/build_pw_sm89.log"
cmake --install "$BUILD" 2>&1 | tee "$LOG/install_sm89.log"

PW="$BUILD/bin/pw.x"
test -x "$PW"
"$PW" --version 2>&1 | tee "$LOG/pw_version_sm89.log"
sha256sum "$PW" | tee "$LOG/pw_sha256_sm89.log"
