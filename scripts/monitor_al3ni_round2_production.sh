#!/usr/bin/env bash
# Read-only progress monitor for the round2 (cfg111-cfg115) production DFT
# batch. Mirrors scripts/monitor_al3ni_remediation.sh. Safe to run in a
# loop / under `watch` -- touches nothing.

P=/workspace/ni_al/data/al3ni_remediation_v1/round2_production_dft

CONFIGS=(
  cfg111_Al3Ni_iso_expansion
  cfg112_Al3Ni_volume_rattle_expansion
  cfg113_Al3Ni_iso_expansion
  cfg114_Al3Ni_volume_rattle_expansion
  cfg115_Al3Ni_iso_expansion
)

printf "Al3Ni ROUND2 PRODUCTION DFT | %s UTC\n" "$(date -u '+%Y-%m-%d %H:%M:%S')"
echo "-----------------------------------------------------------------------------------"
printf "%-40s %-10s %-9s %-8s %-10s\n" "CONFIG" "STATUS" "ELAPSED" "ITER" "SCF_ACC(Ry)"
echo "-----------------------------------------------------------------------------------"

DONE=0
for CID in "${CONFIGS[@]}"; do
  D="$P/$CID/attempt_001"
  META="$D/execution_metadata.env"
  OUT="$D/qe.out"

  if [[ -f "$D/DONE_MARKER.txt" ]]; then
    STATUS=$(cat "$D/DONE_MARKER.txt")
    START=$(awk -F= '$1=="START_TIMESTAMP"{print $2}' "$META" 2>/dev/null)
    END=$(awk -F= '$1=="END_TIMESTAMP"{print $2}' "$META" 2>/dev/null)
    if [[ -n "$START" && -n "$END" ]]; then
      S=$(date -u -d "$START" +%s 2>/dev/null)
      E=$(date -u -d "$END" +%s 2>/dev/null)
      SEC=$((E-S))
      ELAPSED=$(printf "%02d:%02d:%02d" $((SEC/3600)) $(((SEC%3600)/60)) $((SEC%60)))
    else
      ELAPSED="-"
    fi
    ITER=$(grep -c "iteration #" "$OUT" 2>/dev/null || echo "-")
    ACC=$(grep "estimated scf accuracy" "$OUT" 2>/dev/null | tail -1 | grep -oE '[0-9.]+E[+-][0-9]+|[0-9.]+' | tail -1)
    [[ "$STATUS" == PASS ]] && DONE=$((DONE+1))
    printf "%-40s %-10s %-9s %-8s %-10s\n" "$CID" "$STATUS" "$ELAPSED" "${ITER:--}" "${ACC:--}"
  elif [[ -f "$META" ]]; then
    START=$(awk -F= '$1=="START_TIMESTAMP"{print $2}' "$META" 2>/dev/null)
    if [[ -n "$START" ]]; then
      S=$(date -u -d "$START" +%s 2>/dev/null)
      NOW=$(date -u +%s)
      SEC=$((NOW-S))
      ELAPSED=$(printf "%02d:%02d:%02d" $((SEC/3600)) $(((SEC%3600)/60)) $((SEC%60)))
    else
      ELAPSED="-"
    fi
    ITER=$(grep -c "iteration #" "$OUT" 2>/dev/null || echo "0")
    ACC=$(grep "estimated scf accuracy" "$OUT" 2>/dev/null | tail -1 | grep -oE '[0-9.]+E[+-][0-9]+|[0-9.]+' | tail -1)
    printf "%-40s %-10s %-9s %-8s %-10s\n" "$CID" "RUNNING" "$ELAPSED" "${ITER:-0}" "${ACC:--}"
  else
    printf "%-40s %-10s %-9s %-8s %-10s\n" "$CID" "NOT STARTED" "-" "-" "-"
  fi
done

echo "-----------------------------------------------------------------------------------"
echo "COMPLETE: $DONE / 5   REMAINING: $((5-DONE))"

if [[ -f "$P/session.log" ]]; then
  echo
  echo "Last session.log line:"
  tail -1 "$P/session.log"
fi
