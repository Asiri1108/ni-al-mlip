#!/usr/bin/env bash
# Build LAMMPS from source with ML-IAP Python support, targeting the
# existing mace-py312-cu128 venv. Run under tmux session ni_al_lammps_build,
# logs to logs/lammps_build.log. Writes configs/LAMMPS_MLIAP_BUILD_STATUS.txt
# on completion (success or failure) recording commit hash and build flags
# for reproducibility, same convention as tools/qe_gpu's build record-keeping.
set -euo pipefail

ROOT=/workspace/ni_al
VENV_PY="$ROOT/envs/mace-py312-cu128/bin/python"
SRC="$ROOT/tools/lammps/sources/lammps"
BUILD_DIR="$ROOT/tools/lammps/builds/mliap_python"
INSTALL_DIR="$ROOT/tools/lammps/install/mliap_python"
STATUS_FILE="$ROOT/configs/LAMMPS_MLIAP_BUILD_STATUS.txt"
LAMMPS_REPO="https://github.com/lammps/lammps.git"
LAMMPS_BRANCH="stable"

echo "=== LAMMPS ML-IAP build starting: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

echo "--- ensuring Cython present in target venv (required for MLIAP_ENABLE_PYTHON) ---"
"$VENV_PY" -m pip install --quiet "cython>=0.29"
CYTHON_VERSION="$("$VENV_PY" -c 'import Cython; print(Cython.__version__)')"
echo "Cython version: $CYTHON_VERSION"

if [ ! -d "$SRC/.git" ]; then
    echo "--- cloning LAMMPS ($LAMMPS_BRANCH branch, shallow) ---"
    git clone --branch "$LAMMPS_BRANCH" --single-branch --depth 1 "$LAMMPS_REPO" "$SRC"
else
    echo "--- source already present at $SRC, skipping clone ---"
fi

cd "$SRC"
COMMIT_HASH="$(git rev-parse HEAD)"
COMMIT_DESCRIBE="$(git describe --tags --always 2>/dev/null || echo unknown)"
echo "LAMMPS commit: $COMMIT_HASH ($COMMIT_DESCRIBE, branch=$LAMMPS_BRANCH)"

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
)
echo "--- cmake configure ---"
echo "Flags: ${CMAKE_ARGS[*]}"
echo "Note: BUILD_MPI=OFF added beyond the requested flag set -- no MPI toolchain"
echo "(mpicc/mpirun) is present in this environment; serial build is correct for"
echo "single-workstation validation MD, not a cluster deployment."
cmake "${CMAKE_ARGS[@]}" "$SRC/cmake"

NPROC="$(nproc)"
echo "--- building (parallel jobs: $NPROC) ---"
cmake --build . -j "$NPROC"

echo "--- installing to $INSTALL_DIR ---"
cmake --install .

echo "--- verifying artifacts ---"
LMP_BIN="$INSTALL_DIR/bin/lmp"
LMP_SHA256="MISSING"
LMP_VERSION="MISSING"
if [ -x "$LMP_BIN" ]; then
    LMP_SHA256="$(sha256sum "$LMP_BIN" | awk '{print $1}')"
    LMP_VERSION="$("$LMP_BIN" -h 2>&1 | head -1 || true)"
fi

PY_IMPORT_OK="NO"
PY_IMPORT_DETAIL=""
if PY_IMPORT_DETAIL="$("$VENV_PY" -c 'import lammps; print(lammps.__file__)' 2>&1)"; then
    PY_IMPORT_OK="YES"
fi

MLIAP_UNIFIED_OK="NO"
MLIAP_DETAIL=""
if MLIAP_DETAIL="$("$VENV_PY" -c 'from lammps.mliap.mliap_unified_abc import MLIAPUnified; print("OK")' 2>&1)"; then
    MLIAP_UNIFIED_OK="YES"
fi

BUILD_END="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

{
  echo "LAMMPS ML-IAP BUILD STATUS"
  echo ""
  echo "Completed UTC: $BUILD_END"
  echo ""
  echo "SOURCE"
  echo "  Repo: $LAMMPS_REPO"
  echo "  Branch: $LAMMPS_BRANCH"
  echo "  Commit: $COMMIT_HASH"
  echo "  Describe: $COMMIT_DESCRIBE"
  echo "  Checkout: $SRC"
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
  echo "  Cython: $CYTHON_VERSION"
  echo "  nproc used: $NPROC"
  echo ""
  echo "INSTALL"
  echo "  Prefix: $INSTALL_DIR"
  echo "  lmp binary: $LMP_BIN"
  echo "  lmp sha256: $LMP_SHA256"
  echo "  lmp -h (first line): $LMP_VERSION"
  echo ""
  echo "VERIFICATION"
  echo "  python -c 'import lammps': $PY_IMPORT_OK ($PY_IMPORT_DETAIL)"
  echo "  MLIAPUnified importable: $MLIAP_UNIFIED_OK ($MLIAP_DETAIL)"
  echo ""
  echo "STATUS"
  if [ "$PY_IMPORT_OK" = "YES" ] && [ "$MLIAP_UNIFIED_OK" = "YES" ] && [ -x "$LMP_BIN" ]; then
      echo "BUILD COMPLETE, ML-IAP PYTHON PATH VERIFIED USABLE"
  else
      echo "BUILD FINISHED BUT VERIFICATION INCOMPLETE -- see VERIFICATION section above"
  fi
} > "$STATUS_FILE"

cat "$STATUS_FILE"
echo "=== LAMMPS ML-IAP build finished: $BUILD_END ==="
