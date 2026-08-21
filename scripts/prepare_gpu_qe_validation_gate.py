#!/usr/bin/env python3
"""Prepare provenance for GPU-QE validation when pseudopotentials are gated."""
from pathlib import Path
from datetime import datetime, timezone
import csv, hashlib, re, socket, subprocess

R=Path('/workspace/ni_al'); B=R/'data/expansion_026_100/gpu_benchmark/cpu_gpu_equivalence'
B.mkdir(parents=True,exist_ok=True)
CASES=[('AlNi_iso_m02','AlNi'),('Al3Ni_iso_m02','Al3Ni'),('AlNi3_iso_m02','AlNi3')]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def parse(path):
 text=path.read_text(errors='replace')
 energies=re.findall(r'!\s+total energy\s+=\s+([-+0-9.Ee]+)\s+Ry',text)
 forces=re.findall(r'atom\s+\d+\s+type\s+\d+\s+force\s+=\s+([-+0-9.Ee]+)\s+([-+0-9.Ee]+)\s+([-+0-9.Ee]+)',text)
 stress=[]
 m=re.search(r'total\s+stress.*?\n\s*([-+0-9.Ee]+)\s+([-+0-9.Ee]+)\s+([-+0-9.Ee]+).*?\n\s*([-+0-9.Ee]+)\s+([-+0-9.Ee]+)\s+([-+0-9.Ee]+).*?\n\s*([-+0-9.Ee]+)\s+([-+0-9.Ee]+)\s+([-+0-9.Ee]+)',text,re.S)
 if m:
  a=list(map(float,m.groups())); stress=[a[0],a[4],a[8],a[5],a[2],a[1]]
 return float(energies[-1]),forces,stress,'JOB DONE.' in text

fields=['config_id','phase','cpu_input_path','cpu_output_path','cpu_input_sha256','cpu_output_sha256','cpu_energy_ry','cpu_force_summary','cpu_stress_summary','notes']
with (B/'reference_manifest.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
 for cid,phase in CASES:
  d=R/f'data/raw_dft/diverse_pilot_01/{phase}/iso_m02'; inp=d/f'{cid}.in'; out=d/f'{cid}.out'; e,forces,stress,done=parse(out)
  w.writerow({'config_id':cid,'phase':phase,'cpu_input_path':inp,'cpu_output_path':out,'cpu_input_sha256':sha(inp),'cpu_output_sha256':sha(out),'cpu_energy_ry':f'{e:.8f}','cpu_force_summary':f'{len(forces)} atoms; full array remains authoritative in hashed output','cpu_stress_summary':'QE printed xx yy zz yz xz xy Ry/bohr^3: '+' '.join(f'{x:.8f}' for x in stress),'notes':f'Historical output JOB DONE={done}; immutable raw_dft reference; QE/ASE sign conversion must be applied identically.'})

now=datetime.now(timezone.utc).isoformat()
compat=f"""GPU-QE BUILD COMPATIBILITY
Generated UTC: {now}
Machine ID: GPU-01
Hostname: {socket.gethostname()}
GPU model: NVIDIA GeForce RTX 4090
Compute capability: 8.9 (queried dynamically with nvidia-smi)
Target architecture: sm_89
Driver: 580.173.02
Driver-reported CUDA compatibility: 13.0
NVIDIA HPC SDK: 26.5 multi-CUDA selected; official installer partially staged, not installed; intended bundled CUDA 12.9 toolchain
Quantum ESPRESSO: exact release 7.6, official QEF GitLab tag qe-7.6 (commit 9f93ddec)
Source archive: /workspace/ni_al/tools/qe_gpu/source_archives/q-e-qe-7.6.tar.gz
Source archive SHA256: 945c8f16ab330c8f0b30f4de1a9a088b85038476fcd819394e641f4d2d8b7d51
Source tree: /workspace/ni_al/tools/qe_gpu/sources/q-e-qe-7.6
Build directory: /workspace/ni_al/tools/qe_gpu/builds/sm_89
QE binary: NOT BUILT (pseudopotential execution gate and compiler staging in progress)
QE binary SHA256: NOT AVAILABLE

Exact QE 7.6 CMake recipe (source-defined options):
cmake -S /workspace/ni_al/tools/qe_gpu/sources/q-e-qe-7.6 -B /workspace/ni_al/tools/qe_gpu/builds/sm_89 -DCMAKE_BUILD_TYPE=Release -DCMAKE_Fortran_COMPILER=<NVHPC_26.5_nvfortran> -DCMAKE_C_COMPILER=<NVHPC_26.5_nvc> -DQE_GPU='openacc;cuda' -DQE_GPU_ARCHS=sm_89 -DQE_ENABLE_MPI=OFF -DQE_ENABLE_OPENMP=ON -DQE_ENABLE_SCALAPACK=OFF
cmake --build /workspace/ni_al/tools/qe_gpu/builds/sm_89 --target pw -j24

Portability:
- GPU-02/03/04 may reuse this binary only when GPU architecture, driver/runtime compatibility, shared-library availability, and a local GPU sanity check are verified.
- For a different GPU architecture, use the identical QE 7.6 source and scientific settings but build for that architecture.
- Every distinct hardware/build combination must pass GPU activation and minimal equivalence verification before producing labels.
- Scientific methodology and exact pseudopotential bytes must remain identical.
- No production jobs are assigned by this document.
"""
(R/'data/expansion_026_100/team_assignments/GPU_QE_BUILD_COMPATIBILITY.txt').write_text(compat)

status=f"""GPU-QE VALIDATION STATUS
Timestamp UTC: {now}
Hostname: {socket.gethostname()}
GPU: NVIDIA GeForce RTX 4090
GPU compute capability: 8.9 (dynamic nvidia-smi query)
Driver: 580.173.02
Driver-reported CUDA compatibility: 13.0
NVIDIA HPC SDK: 26.5 multi-CUDA selected; official 15,800,624,693-byte installer is only partially staged and was stopped safely; nvfortran not installed
Quantum ESPRESSO version: 7.6 exact source staged; executable not built
QE source identity: official QEF GitLab qe-7.6 tag, commit 9f93ddec
QE source archive: /workspace/ni_al/tools/qe_gpu/source_archives/q-e-qe-7.6.tar.gz
QE source archive SHA256: 945c8f16ab330c8f0b30f4de1a9a088b85038476fcd819394e641f4d2d8b7d51
QE binary path: NOT AVAILABLE
QE binary SHA256: NOT AVAILABLE

PSEUDOPOTENTIAL GATE
Expected Al: Al.pbe-n-kjpaw_psl.1.0.0.UPF
Expected Ni: ni_pbe_v1.4.uspp.F.UPF
Required staging directory: /workspace/ni_al/tools/qe_pseudos
Search scope: /workspace/ni_al and /workspace
Exact source files found: NO
Staged pseudopotentials: NONE
No replacements or same-element substitutes were downloaded.

AUTHORITATIVE EQUIVALENCE CONFIGURATIONS
1. AlNi_iso_m02 (AlNi small phase)
2. Al3Ni_iso_m02 (Al3Ni heavy phase)
3. AlNi3_iso_m02 (AlNi3 spin-relevant phase)
Historical CPU identities and hashes: data/expansion_026_100/gpu_benchmark/cpu_gpu_equivalence/reference_manifest.csv

CALCULATION STATUS
GPU sanity calculation: NOT RUN (exact pseudopotentials absent)
GPU acceleration verified: NO
AlNi_iso_m02 equivalence: NOT RUN
Al3Ni_iso_m02 equivalence: NOT RUN
AlNi3_iso_m02 equivalence: NOT RUN
Energy/force/stress comparisons: NOT AVAILABLE
Five timing benchmarks run: 0/5
Production configurations run: 0/75
MACE training launched: NO
LAMMPS launched: NO

DECISION
CPU-GPU equivalence: NOT TESTED
GPU production approved: NO
Blocking issue: the exact established pseudopotential files are absent under /workspace. Their scientific identity cannot be inferred from filenames alone, so execution is forbidden until exact historical files are supplied and source/staged hashes match.
Safest next action: stage the two exact historical UPF files in /workspace/ni_al/tools/qe_pseudos, record source provenance and SHA256, then finish/build QE 7.6 and run only the three planned equivalence tests.
"""
(R/'configs/GPU_QE_VALIDATION_STATUS.txt').write_text(status)
print('REFERENCE_MANIFEST_AND_GATE_REPORTS_WRITTEN')
