#!/usr/bin/env bash

ROOT=/workspace/ni_al
PROD="$ROOT/data/expansion_026_100/production_gpu"
STALE=180
NOW=$(date +%s)

fmt_time() {
    local s=$1
    (( s < 0 )) && s=0
    printf "%02dh:%02dm:%02ds" $((s/3600)) $(((s%3600)/60)) $((s%60))
}

chunk_expected() {
    case "$1" in
        01|02|03) echo 6 ;;
        04|05)    echo 8 ;;
        06|07)    echo 7 ;;
        08|09|10) echo 9 ;;
    esac
}

pod_chunks() {
    case "$1" in
        01) echo "06 01" ;;
        02) echo "07 02" ;;
        03) echo "04 08" ;;
        04) echo "05 09" ;;
        05) echo "10 03" ;;
    esac
}

pod_total() {
    case "$1" in
        01|02) echo 13 ;;
        03|04) echo 17 ;;
        05)    echo 15 ;;
    esac
}

GLOBAL_DONE=$(find "$PROD" -type f -name config_complete.env 2>/dev/null | wc -l)

clear
echo "Ni-Al Dataset-100  |  $(date '+%H:%M:%S')  |  COMPLETE: ${GLOBAL_DONE}/75"
printf "%-4s %-20s %-7s %-30s %-8s %-10s\n" \
       "POD" "STATE" "CHUNK" "CONFIG" "DONE" "ELAPSED"
printf '%*s\n' 92 '' | tr ' ' '-'

for POD in 01 02 03 04 05; do

    CHUNKS=$(pod_chunks "$POD")
    TOTAL=$(pod_total "$POD")
    DONE=0
    ACTIVE=""
    NEXT_CHUNK="--"

    for C in $CHUNKS; do
        DIR="$PROD/chunk_$C"

        C_DONE=$(find "$DIR" -type f -name config_complete.env 2>/dev/null | wc -l)
        DONE=$((DONE + C_DONE))

        EXPECT=$(chunk_expected "$C")

        if [ "$NEXT_CHUNK" = "--" ] && [ "$C_DONE" -lt "$EXPECT" ]; then
            NEXT_CHUNK="$C"
        fi

        if [ -z "$ACTIVE" ]; then
            while IFS= read -r A; do
                [ -n "$A" ] || continue

                CFG=$(echo "$A" | sed -n \
                    's#.*production_gpu/chunk_[0-9][0-9]/\([^/]*\)/.*#\1#p')

                CFGROOT="$DIR/$CFG"

                if ! find "$CFGROOT" -type f -name config_complete.env \
                    -print -quit 2>/dev/null | grep -q .; then
                    ACTIVE="$A"
                    break
                fi
            done < <(
                find "$DIR" -type f -name active.env \
                -printf '%T@ %p\n' 2>/dev/null |
                sort -nr |
                cut -d' ' -f2-
            )
        fi
    done

    STATE=""
    CHUNK="$NEXT_CHUNK"
    CONFIG="-"
    ELAPSED="-"

    if [ "$DONE" -ge "$TOTAL" ]; then

        STATE="FINISHED"
        CHUNK="--"

    elif [ -n "$ACTIVE" ]; then

        CHUNK=$(echo "$ACTIVE" | sed -n \
            's#.*production_gpu/chunk_\([0-9][0-9]\)/.*#\1#p')

        CONFIG=$(echo "$ACTIVE" | sed -n \
            's#.*production_gpu/chunk_[0-9][0-9]/\([^/]*\)/.*#\1#p')

        START=$(stat -c %Y "$ACTIVE" 2>/dev/null || echo "$NOW")
        ELAPSED=$(fmt_time $((NOW-START)))

        CFGROOT="$PROD/chunk_$CHUNK/$CONFIG"

        NEWEST=$(find "$CFGROOT" -type f -printf '%T@\n' 2>/dev/null |
                 sort -nr | head -1 | cut -d. -f1)

        [ -z "$NEWEST" ] && NEWEST=$START

        AGE=$((NOW-NEWEST))

        if [ "$AGE" -le "$STALE" ]; then
            STATE="ACTIVE"
        else
            STATE="STOPPED/UNCONNECTED"
        fi

    else

        STATUS="$ROOT/configs/production_chunks/pod_${POD}_status.txt"

        if [ -f "$STATUS" ]; then
            MTIME=$(stat -c %Y "$STATUS")
            AGE=$((NOW-MTIME))

            if [ "$AGE" -le "$STALE" ]; then
                STATE="STARTING/TRANSITION"
            else
                STATE="STOPPED/UNCONNECTED"
            fi
        else
            STATE="STOPPED/UNCONNECTED"
        fi
    fi

    CONFIG="${CONFIG:0:30}"

    printf "%-4s %-20s %-7s %-30s %3d/%-4d %-10s\n" \
           "$POD" "$STATE" "$CHUNK" "$CONFIG" "$DONE" "$TOTAL" "$ELAPSED"
done

echo
df -h /workspace | awk 'NR==2 {
    print "Network Volume: "$3" used / "$2"  ("$5")"
}'
