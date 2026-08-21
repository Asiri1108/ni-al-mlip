#!/usr/bin/env bash
# Build LAMMPS with PKG_KOKKOS (CUDA, sm_89/ADA89) + ML-IAP Python support,
# into a SEPARATE install prefix from the existing mliap_python build (that
# build stays intact as fallback/record -- it lacks forward_exchange/
# reverse_exchange on its MLIAPDataPy class, which mace 0.3.16's ML-IAP
# ghost-atom feature exchange requires unconditionally; those methods only
# exist in LAMMPS's KOKKOS ML-IAP Python coupling
# (src/KOKKOS/mliap_unified_couple_kokkos.pyx), confirmed by grepping the
# LAMMPS source tree -- hence this rebuild.
#
# Run under tmux session ni_al_lammps_kokkos_build, logs to
# logs/lammps_kokkos_build.log. Writes
# configs/LAMMPS_MLIAP_KOKKOS_BUILD_STATUS.txt on completion recording
# commit hash, full cmake flag list, toolchain versions, and lmp sha256 --
# same reproducibility record convention as tools/qe_gpu.
set -euo pipefail

ROOT=/workspace/ni_al
VENV_PY="$ROOT/envs/mace-py312-cu128/bin/python"
SRC="$ROOT/tools/lammps/sources/lammps"   # reused: same checkout as the mliap_python build
BUILD_DIR="$ROOT/tools/lammps/builds/mliap_kokkos"
INSTALL_DIR="$ROOT/tools/lammps/install/mliap_kokkos"
STATUS_FILE="$ROOT/configs/LAMMPS_MLIAP_KOKKOS_BUILD_STATUS.txt"
NVCC_WRAPPER="$SRC/lib/kokkos/bin/nvcc_wrapper"

echo "=== LAMMPS Kokkos(CUDA/ADA89)+ML-IAP build starting: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

if [ ! -d "$SRC/.git" ]; then
    echo "FATAL: expected existing source checkout at $SRC (from the mliap_python build), not found." >&2
    exit 1
fi
cd "$SRC"
COMMIT_HASH="$(git rev-parse HEAD)"
COMMIT_DESCRIBE="$(git describe --tags --always 2>/dev/null || echo unknown)"
DIRTY="$(git status --porcelain | head -1)"
echo "LAMMPS source (reused checkout): commit=$COMMIT_HASH describe=$COMMIT_DESCRIBE"
if [ -n "$DIRTY" ]; then
    echo "WARNING: source checkout has local modifications:"
    git status --porcelain
fi

if [ ! -x "$NVCC_WRAPPER" ]; then
    echo "FATAL: nvcc_wrapper not found at $NVCC_WRAPPER (expected vendored under lib/kokkos)" >&2
    exit 1
fi

NVCC_VERSION="$(nvcc --version | tail -1)"
GCC_VERSION="$(gcc --version | head -1)"
CMAKE_VERSION="$(cmake --version | head -1)"
echo "Toolchain: nvcc: $NVCC_VERSION"
echo "Toolchain: gcc: $GCC_VERSION"
echo "Toolchain: cmake: $CMAKE_VERSION"

mkdir -p "$BUILD_DIR" "$INSTALL_DIR"
cd "$BUILD_DIR"

CMAKE_ARGS=(
  -D PKG_PYTHON=ON
  -D "PKG_ML-IAP=ON"
  -D MLIAP_ENABLE_PYTHON=ON
  -D BUILD_SHARED_LIBS=ON
  -D Python_EXECUTABLE="$VENV_PY"
  -D BUILD_MPI=OFF
  -D CMAKE_BUILD_TYPE=Release
  -D CMAKE_INSTALL_PREFIX="$INSTALL_DIR"
  -D PKG_KOKKOS=ON
  -D Kokkos_ENABLE_CUDA=ON
  -D Kokkos_ARCH_ADA89=ON
  -D CMAKE_CXX_COMPILER="$NVCC_WRAPPER"
)
echo "--- cmake configure ---"
echo "Flags: ${CMAKE_ARGS[*]}"
cmake "${CMAKE_ARGS[@]}" "$SRC/cmake"

NPROC="$(nproc)"
echo "--- building (parallel jobs: $NPROC) -- Kokkos+CUDA template compiles are heavy, expect this to take a while ---"
cmake --build . -j "$NPROC"

echo "--- installing to $INSTALL_DIR ---"
cmake --install .

echo "--- building + installing python module in isolation (NOT global site-packages) ---"
LIBLAMMPS_BUILD="$BUILD_DIR/liblammps.so"
mkdir -p "$INSTALL_DIR/pyinstall"
"$VENV_PY" "$SRC/python/install.py" \
  -p "$SRC/python/lammps" \
  -l "$LIBLAMMPS_BUILD" \
  -w "$BUILD_DIR" \
  -v "$SRC/src/version.h" \
  -n
WHEEL="$(ls "$BUILD_DIR"/lammps-*.whl | head -1)"
"$VENV_PY" -m pip install --no-deps --force-reinstall --target "$INSTALL_DIR/pyinstall" "$WHEEL"

echo "--- verifying artifacts ---"
LMP_BIN="$INSTALL_DIR/bin/lmp"
LMP_SHA256="MISSING"
LMP_RUN_OK="NO"
LMP_RUN_DETAIL=""
if [ -x "$LMP_BIN" ]; then
    LMP_SHA256="$(sha256sum "$LMP_BIN" | awk '{print $1}')"
    if LMP_RUN_DETAIL="$(LD_LIBRARY_PATH="$INSTALL_DIR/lib:${LD_LIBRARY_PATH:-}" "$LMP_BIN" -h 2>&1 | head -1)"; then
        LMP_RUN_OK="YES"
    fi
fi

PY_IMPORT_OK="NO"
PY_IMPORT_DETAIL=""
if PY_IMPORT_DETAIL="$(PYTHONPATH="$INSTALL_DIR/pyinstall" LD_LIBRARY_PATH="$INSTALL_DIR/lib:${LD_LIBRARY_PATH:-}" "$VENV_PY" -c 'import lammps; print(lammps.__file__)' 2>&1)"; then
    PY_IMPORT_OK="YES"
fi

MLIAP_UNIFIED_OK="NO"
MLIAP_DETAIL=""
if MLIAP_DETAIL="$(PYTHONPATH="$INSTALL_DIR/pyinstall" LD_LIBRARY_PATH="$INSTALL_DIR/lib:${LD_LIBRARY_PATH:-}" "$VENV_PY" -c 'from lammps.mliap.mliap_unified_abc import MLIAPUnified; print("OK")' 2>&1)"; then
    MLIAP_UNIFIED_OK="YES"
fi

KOKKOS_PYX_BUILT="NO"
if find "$BUILD_DIR" -iname "mliap_unified_couple_kokkos*" | grep -q .; then
    KOKKOS_PYX_BUILT="YES"
fi

BUILD_END="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

{
  echo "LAMMPS ML-IAP KOKKOS(CUDA/ADA89) BUILD STATUS"
  echo ""
  echo "Completed UTC: $BUILD_END"
  echo ""
  echo "REASON FOR THIS BUILD"
  echo "  Existing tools/lammps/install/mliap_python build lacks Kokkos, so its"
  echo "  MLIAPDataPy class has no forward_exchange/reverse_exchange methods --"
  echo "  mace 0.3.16's ML-IAP ghost-atom feature exchange calls these"
  echo "  unconditionally (even single-process, periodic ghost atoms always"
  echo "  exist). Stage A single-point check failed with:"
  echo "    AttributeError: 'mliap_unified_couple.MLIAPDataPy' object has no"
  echo "    attribute 'forward_exchange'"
  echo "  Kept the mliap_python build intact as fallback/record -- did NOT"
  echo "  modify or delete it."
  echo ""
  echo "SOURCE"
  echo "  Checkout (reused from mliap_python build): $SRC"
  echo "  Commit: $COMMIT_HASH"
  echo "  Describe: $COMMIT_DESCRIBE"
  echo "  Local modifications at build time: ${DIRTY:-none}"
  echo ""
  echo "BUILD FLAGS (cmake)"
  for a in "${CMAKE_ARGS[@]}"; do
      [ "$a" = "-D" ] && continue
      echo "  $a"
  done
  echo "  (source dir: $SRC/cmake)"
  echo ""
  echo "TOOLCHAIN"
  echo "  Python (target venv): $VENV_PY"
  echo "  nvcc: $NVCC_VERSION"
  echo "  gcc: $GCC_VERSION"
  echo "  cmake: $CMAKE_VERSION"
  echo "  nvcc_wrapper: $NVCC_WRAPPER"
  echo "  nproc used: $NPROC"
  echo ""
  echo "INSTALL"
  echo "  Prefix: $INSTALL_DIR"
  echo "  lmp binary: $LMP_BIN"
  echo "  lmp sha256: $LMP_SHA256"
  echo "  lmp runs (with LD_LIBRARY_PATH set): $LMP_RUN_OK ($LMP_RUN_DETAIL)"
  echo "  Python module: isolated install at $INSTALL_DIR/pyinstall (NOT global"
  echo "    site-packages -- selected via PYTHONPATH, see tools/lammps/setup_lammps_env.sh,"
  echo "    so it coexists with the mliap_python build's isolated install)"
  echo ""
  echo "VERIFICATION"
  echo "  python -c 'import lammps' (PYTHONPATH-isolated): $PY_IMPORT_OK ($PY_IMPORT_DETAIL)"
  echo "  MLIAPUnified importable: $MLIAP_UNIFIED_OK ($MLIAP_DETAIL)"
  echo "  Kokkos ML-IAP python coupling module built (mliap_unified_couple_kokkos*): $KOKKOS_PYX_BUILT"
  echo "  NOTE: this does NOT yet confirm forward_exchange/reverse_exchange actually"
  echo "  resolve the Stage A AttributeError end-to-end -- that requires re-running"
  echo "  Stage A against this build, not done automatically by this script."
  echo ""
  echo "STATUS"
  if [ "$PY_IMPORT_OK" = "YES" ] && [ "$MLIAP_UNIFIED_OK" = "YES" ] && [ "$KOKKOS_PYX_BUILT" = "YES" ] && [ -x "$LMP_BIN" ]; then
      echo "BUILD COMPLETE, ARTIFACTS PRESENT -- STAGE A RE-VERIFICATION STILL REQUIRED"
  else
      echo "BUILD FINISHED BUT VERIFICATION INCOMPLETE -- see VERIFICATION section above"
  fi
} > "$STATUS_FILE"

cat "$STATUS_FILE"
echo "=== LAMMPS Kokkos build finished: $BUILD_END ==="
