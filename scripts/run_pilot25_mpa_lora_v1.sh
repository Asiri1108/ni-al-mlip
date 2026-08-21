#!/usr/bin/env bash
# PROPOSED ONLY. Do not execute without explicit approval.
set -euo pipefail

source /workspace/ni_al/envs/mace-py312-cu128/bin/activate
mace_run_train --config=/workspace/ni_al/configs/pilot25_mpa_lora_v1.yaml

