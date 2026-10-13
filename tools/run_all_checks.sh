#!/bin/bash
# Current standalone regressions. Self-locking tools run directly; caller-lock
# tools take one flock each. Do not wrap this runner in another render flock.
set -euo pipefail
cd "$(dirname "$0")/.."

# Preserve display/driver settings, but exclude inherited gameplay/test presets.
for name in $(compgen -e); do
    case "$name" in
        BOTW_*|SLOPPY_*|ROUND*|TRAVERSAL_*|TALUS_*|SHRINE_VISUAL_*|COMBAT_*|FAUNA_*|TREE_*|PUZZLE_*|VISUAL_*|JOURNEY_*|OCCLUDER_BUILD_ONLY) unset "$name" ;;
    esac
done
# Fixed-frame regression captures request uncapped production rendering.
# Vulkan reads its public option before window initialization; BOTW_NOVSYNC is GLES-only.
export SLOPPY_PLATFORM=x11
export SLOPPY_VSYNC=0
# Imported tool modules must not leave __pycache__ beside tracked sources.
export PYTHONDONTWRITEBYTECODE=1
mkdir -p build/all-checks
list=false
only=${2:-}
resume=false
case "${1:-}" in
    '') ;;
    --list) list=true ;;
    --only) [[ -n $only ]] || { echo 'Usage: tools/run_all_checks.sh [--list | --only NAME]' >&2; exit 2; } ;;
    --resume) resume=true; only= ;;
    *) echo 'Usage: tools/run_all_checks.sh [--list | --only NAME | --resume RUN_DIR]' >&2; exit 2 ;;
esac
declare -A retained=()
if $resume; then
    out=$(realpath "${2:?Usage: tools/run_all_checks.sh --resume build/all-checks/run-DIRECTORY}")
    [[ $out == "$PWD/build/all-checks/run-"* && -f $out/commit && -f $out/results.tsv ]]
    [[ $(cat "$out/commit") == "$(git rev-parse HEAD)" ]] || { echo 'Resume requires the original HEAD' >&2; exit 2; }
    # A documentation-only edit or a runner recovery fix cannot change test
    # inputs. All game, asset, compiler and other tool sources must be unchanged.
    changed=$(git diff --name-only "$(cat "$out/commit")" -- game assets sloppy tools docs/ref | sed '/^tools\/run_all_checks.sh$/d')
    [[ -z $changed ]] || { printf 'Test inputs changed; start a fresh run:\n%s\n' "$changed" >&2; exit 2; }
    while IFS=$'\t' read -r name result status; do
        if [[ $result == PASS ]]; then retained[$name]=1; else unset "retained[$name]"; fi
    done < "$out/results.tsv"
    stamp=$(date +%s)
    cp "$out/results.tsv" "$out/results-before-resume-$stamp.tsv"
    cp "$out/summary.txt" "$out/summary-before-resume-$stamp.txt"
    date -Iseconds >> "$out/resumes.txt"
else
    out=$(mktemp -d "$PWD/build/all-checks/run-XXXXXXXX")
    git rev-parse HEAD > "$out/commit"
    git status --short > "$out/worktree.txt"
    date -Iseconds > "$out/date"
fi
mkdir -p "$out/tmp" "$out/bin"
export TMPDIR="$out/tmp"
passed=0
failed=0
selected=0
start=$(date -d "$(cat "$out/date")" +%s)
if ! $resume; then : > "$out/results.tsv"; fi
: > "$out/summary.txt"

check() {
    local mode=$1 name=$2 status=0
    shift 2
    if $list; then printf '%-8s %s\n' "$mode" "$name"; return; fi
    [[ -z $only || $name == "$only" ]] || return 0
    selected=$((selected + 1))
    if [[ ${retained[$name]:-0} == 1 ]]; then
        passed=$((passed + 1))
        printf 'PASS %s (retained)\n' "$name" | tee -a "$out/summary.txt"
        return 0
    fi
    # There is deliberately no timeout around flock: queue wait is unlimited.
    # The individual render tools bound their actual game processes.
    if [[ $mode == render ]]; then
        flock /tmp/botw-render.lock "$@" > "$out/$name.log" 2>&1 || status=$?
    else
        "$@" > "$out/$name.log" 2>&1 || status=$?
    fi
    # Some older tests print FAIL but still exit zero. Ignore explicit zero-fail
    # counts, such as feel_test's reference summary, while detecting real failures.
    if (( status == 0 )) && sed -E 's/\b0 FAIL\b//g' "$out/$name.log" | grep -E '\bFAIL\b|panic:|Traceback \(most recent call last\)' > /dev/null; then status=1; fi
    if (( status == 0 )); then
        passed=$((passed + 1))
        printf 'PASS %s\n' "$name" | tee -a "$out/summary.txt"
        printf '%s\tPASS\t0\n' "$name" >> "$out/results.tsv"
    else
        failed=$((failed + 1))
        printf 'FAIL %s (exit %s; %s)\n' "$name" "$status" "$out/$name.log" | tee -a "$out/summary.txt"
        printf '%s\tFAIL\t%s\n' "$name" "$status" >> "$out/results.tsv"
    fi
}

jo() {
    local name=$1
    if [[ $name == shrine_obstruction_check ]]; then
        tools/shrine_obstruction_check.sh
        return
    fi
    sloppy/bin/sloppy build "tools/$name.jo" -o "$out/bin/$name" || return
    "$out/bin/$name" "${@:2}"
}

# Headless tests; helper-only *_checks.jo files are exercised by their entry
# points (fauna includes spacing, Stalkoblin, wildlife voices and Talus).
cpu_checks=(
    architecture_test
    art_shade_test
    camera_check
    camp_role_check
    cliff_climb_check
    cliff_mesh_check
    clutter_check
    collision_query_check
    combat_check
    combat_music_check
    music_transition_check
    combat_reach_check
    contact_check
    cooking_check
    element_check
    element_test
    enemy_spacing_test
    fauna_test
    feel_test
    fire_query_check
    fire_scan_check
    fire_test
    input_check
    integration_test
    journey_controller_check
    landscape_check
    temple_roof_check
    map_water_check
    mesh_pack_test
    opening_test
    passage_mesh_check
    piano_test
    music_harmony_check
    presentation_check
    save_test
    shrine_arrival_check
    shrine_ceremony_check
    shrine_discovery_check
    shrine_enclosure_check
    shrine_obstruction_check
    shrine_lighting_check
    shrine_paint_check
    shrine_shaft_check
    shrine_sightline_check
    soundscape_check
    story_approach_check
    stride_check
    talus_mesh_check
    talus_skin_check
    talus_test
    title_handoff_check
    tower_activation_check
    tower_base_climb_check
    round91_fire_check
    round91_weather_check
    round92_lightning_check
    title_panorama_check
    tree_test
    vegetation_reach_check
    vegetation_tail_check
    fir_bough_check
    wake_contact_check
    wading_check
    water_coverage_check
    waterfall_shape_check
    weather_fx_test
    vapor_shape_check
    weather_shading_check
    round78_weather_check
    round79_fx_check
    round80_fire_check
    round77_pose_check
    round78_camp_check
    round78_shrine_check
    round80_art_check
    round81_art_check
    round82_character_check
    round88_material_check
    camp_alert_check
    wildlife_observation_check
    wildlife_path_check
)
for name in "${cpu_checks[@]}"; do
    check cpu "$name" jo "$name"
done

# Fresh-process and production-controller wrappers also exercise their fixtures.
for name in save_check status_save_check encounter_weather_save_check \
    talus_save_element_check element_journey_check journey_check late_story_check \
    shrine_route_check shrine_gap_check prepared_assets_check; do
    check cpu "$name" "tools/$name.sh"
done
check cpu journey_keyboard_check tools/journey_check.sh --keyboard
for name in defect_hunt_check enemy_model_check hero_model_check wildlife_mesh_check \
    weather_silhouette_test environment_visuals_check round70_heat_check round92_lightning_target_check; do
    check cpu "$name" python3 "tools/$name.py"
done
check cpu movement_source_audit python3 docs/ref/verify_movement_response_sources.py
check cpu performance_window_check python3 tools/performance_window_check.py
check cpu listening_clips python3 tools/listen.py

# Small GPU equivalence tests never self-lock. Compile while holding their sole
# lock too, so even a compiler-run window cannot overlap another renderer.
for name in combat_geometry_check draw_cache_check skin_row_check fir_surface_check hero_surface_check material_paint_check post_edge_check \
    shader_load_check shader_adapter_check slot_check terrain_noise_check noise_seam_check climb_occluder_check; do
    # flock launches a fresh shell; export this function and its binary directory.
    export out
    export -f jo
    check render "$name" bash -c 'jo "$1"' -- "$name"
done

# Every rendered frame of the full tower-base circuit checks its HDR body crop.
check render tower_base_climb_capture env BOTW_SKIP=1 BOTW_TOWER=1 BOTW_HOUR=11 BOTW_WEATHER=clear BOTW_SCALE=1 SLOPPY_WINDOW=1280x720 SLOPPY_FRAMES=2600 SLOPPY_SCREENSHOT="$out/tower-base.png" timeout 240 sloppy/bin/sloppy tools/tower_base_climb_capture.jo

# The runner owns no lock when invoking these tools; they lock their own renders.
for name in production_loop_check menu_pause_check opening_check title_rise_visual_check daylight_check \
    weather_transition_check inventory_check passage_visual_check cliff_visual_check \
    shrine_exit_check combat_visual_check; do
    check self "$name" "tools/$name.sh"
done
# A real placed-camp approach; keep it explicit so --only can reproduce a miss.
check self camp_sword_visual_check env COMBAT_SCENES=camp_sword tools/combat_visual_check.sh "$out/camp-sword"
check self prepared_frame_check python3 tools/prepared_frame_check.py
check self element_input_check python3 tools/element_input_check.py
check self renderer_structure_check python3 tools/renderer_structure_check.py
check self weather_silhouette_check python3 tools/weather_silhouette_check.py
check self sky_camera_check python3 tools/sky_camera_check.py
check self traversal_check tools/traversal_check
check self live_audio_check python3 tools/live_audio_check.py
check cpu live_audio_analysis python3 tools/analyze_live_audio.py build/live-audio --check
check cpu mix_loudness_check python3 tools/mix_loudness_check.py --check
check cpu weapon_icon_check python3 tools/weapon_icon_check.py
check self startup_copy_check python3 tools/startup_copy_check.py --ref HEAD --repeats 6 --binary-repeats 6

# These wrappers explicitly require the caller to own the lock.
for name in passage_check cooking_visual_check \
    element_puzzle_visual_check fauna_visual_check machinery_visual_check \
    occluder_check stalkoblin_visual_check tree_visual_check talus_visual_check; do
    check render "$name" "tools/$name.sh"
done

if $list; then exit 0; fi
if (( selected == 0 )); then echo "Unknown check: $only" >&2; exit 2; fi
# Keep one final row per check after retries of failed/interrupted groups.
awk -F '\t' '!seen[$1]++ {order[++n]=$1} {row[$1]=$0} END {for(i=1;i<=n;i++) print row[order[i]]}' \
    "$out/results.tsv" > "$out/results-dedup.tsv"
mv "$out/results-dedup.tsv" "$out/results.tsv"
printf 'SUMMARY: %s PASS, %s FAIL, %s total; %ss elapsed; commit %s\n' \
    "$passed" "$failed" "$selected" "$(($(date +%s) - start))" "$(cat "$out/commit")" | tee -a "$out/summary.txt"
printf 'Evidence: %s\n' "$out" | tee -a "$out/summary.txt"
(( failed == 0 ))
