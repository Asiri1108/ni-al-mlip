#!/usr/bin/env bash

P=/workspace/ni_al/data/al3ni_remediation_v1/production_dft

declare -A ROLE
ROLE[101]=TRAIN
ROLE[102]=TRAIN
ROLE[103]=TRAIN
ROLE[104]=TRAIN
ROLE[105]=TRAIN
ROLE[106]=TRAIN
ROLE[107]=VALIDATION
ROLE[108]=VALIDATION
ROLE[109]=CONFIRMATION
ROLE[110]=CONFIRMATION

printf "Al3Ni REMEDIATION DFT | %s\n" "$(date '+%H:%M:%S')"
echo "---------------------------------------------------------"
printf "%-7s %-14s %-12s %-10s\n" "CONFIG" "ROLE" "STATE" "ELAPSED"
echo "---------------------------------------------------------"

TOTAL_DONE=0

for N in {101..110}; do
    D=$(find "$P" -maxdepth 1 -type d -name "cfg${N}_*" | head -1)

    if [ -z "$D" ]; then
        printf "%-7s %-14s %-12s %-10s\n" "cfg$N" "${ROLE[$N]}" "NOT STARTED" "-"
        continue
    fi

    if find "$D" -type f -name config_complete.env -print -quit 2>/dev/null | grep -q .; then
        STATE="COMPLETE"
        ELAPSED="-"
        TOTAL_DONE=$((TOTAL_DONE+1))

    elif find "$D" -type f -name active.env -print -quit 2>/dev/null | grep -q .; then
        STATE="ACTIVE"

        A=$(find "$D" -type f -name active.env -printf '%T@ %p\n' 2>/dev/null \
            | sort -nr | head -1 | cut -d' ' -f2-)

        START=$(stat -c %Y "$A" 2>/dev/null)
        NOW=$(date +%s)
        SEC=$((NOW-START))

        ELAPSED=$(printf "%02d:%02d:%02d" \
            $((SEC/3600)) $(((SEC%3600)/60)) $((SEC%60)))
    else
        STATE="PENDING"
        ELAPSED="-"
    fi

    printf "%-7s %-14s %-12s %-10s\n" \
        "cfg$N" "${ROLE[$N]}" "$STATE" "$ELAPSED"
done

echo "---------------------------------------------------------"
echo "TOTAL: $TOTAL_DONE / 10   REMAINING: $((10-TOTAL_DONE))"

echo
echo "LOCAL QE:"
ps -eo pid,etime,%cpu,cmd | grep "[p]w.x" || echo "NO pw.x"

echo
echo "GPU:"
nvidia-smi --query-gpu=utilization.gpu,memory.used,power.draw \
--format=csv,noheader
