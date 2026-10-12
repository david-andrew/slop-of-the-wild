#!/bin/bash
# Hold the shared render lock for the entire repeat suite, including load measurements.
# BENCH_REPEATS=3 tools/bench.sh > docs/PERFORMANCE.md
# BENCH_VIEW="burning tent" BENCH_MODES="paced gpu cpu" tools/bench.sh
set -euo pipefail
cd "$(dirname "$0")/.."
# Rebuild a report from complete captured runs without rendering again.
if [[ ${1:-} == --report ]]; then
  exec python3 tools/bench_report.py "${2:?log directory required}" "${BENCH_REPEATS:-3}" "${BENCH_FRAMES:-960}" "${BENCH_JSON:-docs/benchmarks.json}"
fi
if [[ ${1:-} != --locked ]]; then
  exec flock /tmp/botw-render.lock "$0" --locked "$@"
fi
shift
repeats=${BENCH_REPEATS:-3}
frames=${BENCH_FRAMES:-960}
if (( repeats < 1 || frames < 360 || frames % 120 != 0 )); then
  echo "BENCH_REPEATS must be positive; BENCH_FRAMES must be >=360 and a multiple of 120" >&2
  exit 2
fi
logs=${BENCH_LOG_DIR:-/tmp/botw-sol-bench-$(date +%Y%m%d-%H%M%S)}
mkdir -p "$logs"
views=(
  "open ground|BOTW_SKIP=1 BOTW_AT=-1030,1805,1.57"
  "Forest of Sprites|BOTW_SKIP=1 BOTW_AT=-1000,1620,3.14"
  "Hopper Pond|BOTW_SKIP=1 BOTW_AT=-1190,1665,-0.9"
  "camp (fight)|BOTW_SKIP=1 BOTW_AT=-1439,1614,0"
  "grass fire|BOTW_SKIP=1 BOTW_FIRE=1"
  "snow|BOTW_SKIP=1 BOTW_AT=-1060,2230,2.0"
  "storm in the forest|BOTW_SKIP=1 BOTW_AT=-1000,1620,3.14 BOTW_WEATHER=storm"
  "a shrine|BOTW_SKIP=1 BOTW_TOWER=1 BOTW_SHRINE=1"
  "sprinting through the forest|BOTW_SKIP=1 BOTW_AT=-1000,1620,3.14 SLOPPY_INPUT=5:w+,5:shift+"
  "sprinting across the open|BOTW_SKIP=1 BOTW_AT=-1030,1805,1.57 SLOPPY_INPUT=5:w+,5:shift+"
  "burning tent|BOTW_SKIP=1 BOTW_TENTFIRE=5 BOTW_AT=-955,1964,0"
)
modes=${BENCH_MODES:-paced gpu}
for mode in $modes; do
  if [[ $mode != paced && $mode != gpu && $mode != cpu ]]; then
    echo "BENCH_MODES accepts paced, gpu, cpu (space separated)" >&2; exit 2
  fi
done
printf '%s\n' "$modes" > "$logs/modes"
: > "$logs/cases.tsv"
for i in "${!views[@]}"; do
  name=${views[$i]%%|*}
  if [[ -n ${BENCH_VIEW:-} && $name != "$BENCH_VIEW" ]]; then continue; fi
  if [[ $name == "burning tent" ]] && (( frames < 960 )); then
    echo "burning tent needs BENCH_FRAMES>=960 to capture intervals 241-900" >&2; exit 2
  fi
  printf '%s\t%s\n' "$i" "$name" >> "$logs/cases.tsv"
done
if [[ ! -s $logs/cases.tsv ]]; then echo "BENCH_VIEW did not match a scenario" >&2; exit 2; fi
printf '%s\n' "$(date -Iseconds)" > "$logs/date"
nvidia-smi --query-gpu=name --format=csv,noheader > "$logs/gpu" 2>/dev/null || echo unknown > "$logs/gpu"
for r in $(seq 1 "$repeats"); do
  for i in "${!views[@]}"; do
    v=${views[$i]}; name=${v%%|*}; read -ra envs <<< "${v#*|}"
    if [[ -n ${BENCH_VIEW:-} && $name != "$BENCH_VIEW" ]]; then continue; fi
    for mode in $modes; do
      prefix="$logs/$r-$i-$mode"
      cat /proc/loadavg > "$prefix.load-start"
      ps -eo comm,pcpu --sort=-pcpu | head -12 > "$prefix.processes" || true
      extra=()
      if [[ $mode == gpu || $mode == cpu ]]; then extra=(BOTW_NOVSYNC=1 SLOPPY_PLATFORM=x11 SLOPPY_WINDOW=2133x1200); fi
      if [[ $mode == gpu ]]; then extra+=(BOTW_GPU=1); fi
      if [[ $mode == cpu ]]; then extra+=(BOTW_CPU=1); fi
      scale=0.8
      if [[ $name == "burning tent" ]]; then scale=0.72; fi
      echo "bench $r/$repeats $name $mode: $(cat /proc/loadavg)" >&2
      env "${envs[@]}" "${extra[@]}" BOTW_SCALE="$scale" BOTW_FRAME_LOG=1 BOTW_LOADTIME=1 SLOPPY_STATS=log SLOPPY_FRAME_STATS=1 SLOPPY_SCREENSHOT="$prefix.png" SLOPPY_FRAMES="$frames" timeout 300 sloppy/bin/sloppy game/main.jo > "$prefix.log" 2>&1
      cat /proc/loadavg > "$prefix.load-end"
    done
  done
done
python3 tools/bench_report.py "$logs" "$repeats" "$frames" "${BENCH_JSON:-docs/benchmarks.json}"
