# Browser build

`tools/build_web.sh` produces `build/site/` for the Pages workflow in
`.github/workflows/pages.yml`. Run it on Linux x86-64 with the bundled Sloppy
0.6.0 executable, Node 22+ and Python 3. It performs CPU preparation, compiles
wasm, traces real asset reads under Node, compresses the selected files and
replaces only the generated page's boot path. No renderer or npm installation
is part of the CI build.

```sh
tools/build_web.sh
python3 -m http.server 8000 --directory build/site
```

Open http://localhost:8000/. The publishing coordinator deploys this directory to
https://david-andrew.github.io/slop-of-the-wild/; this branch does not push or
publish it.

## Loading and prepared data

The generated page loads seven gzip archives before starting Sloppy. A plain
progress bar covers downloading, decompression, CPU initialization and shader
compilation. Archive extraction streams directly into individual `Uint8Array`
files; it does not allocate a second uncompressed archive. HTTPS/localhost
loads verify SHA-256. Content-addressed archive and manifest names keep a page
and its data together. All paths retain the exact `assets/...` names the game
reads, including the referenced nature textures.

The builder traces successful reads through startup and the first frame, so it
includes animations and place-name metadata as well as models, audio, grids and
nature files. With the selected packs, 193 files are shipped (including all 90 piano WAVs). Source PNGs are
replaced by their prepared RGBA records. Unused source downloads, normal maps,
reference footage and unreferenced models are excluded.

Selected packs are world (15.86 MB gzip), water (1.22 MB), farland (1.96 MB),
chime (0.22 MB) and textures (25.10 MB). The world pack avoids the first collision/
heightfield preparation, which measured about eight seconds in the loaded baseline. Water/farland avoid roughly 2.6 seconds of CPU work for
about 3.2 MB. RGBA textures replace 21.25 MB of compressed PNG inputs, adding
about 3.9 MB overall while reducing the texture stage from roughly 4–5 seconds
to 0.8 seconds in the CPU wasm trace. Other geometry and SFX samples are generated during startup. The same Sloppy piano
generator runs in a dedicated wasm worker alongside world/graphics initialization.
The worker transfers its exact compact pack to the main thread; all dynamics and
registers are validated and ready before gameplay starts. Foley directory entries
and source stamps participate in the shared audio fingerprint without copying
Foley sample data into the worker.

The world pack costs 15.86 MB for about three seconds saved; terrain costs
14.47 MB for about two seconds; structures cost 34.92 MB for about two seconds.
Prepared piano/SFX together cost 274.42 MB versus the much smaller source WAVs,
for roughly six seconds saved. These packs are omitted. The extended compact piano pack is 154.19 MB locally; the default package continues to use mono PCM16 WAVs and regenerate the bank. The packager verifies complete piano-manifest coverage so a stale trace cannot omit the added octaves. The Round 69 build ships 111.49 MB of compressed assets across seven archives;
the complete site is about 121.20 MB including the game and 0.46 MB piano worker.
It adds the world pack while retaining the compact mono WAV downloads, rather
than downloading the 101.82 MB compressed stereo piano pack.
`tools/web_piano_worker_check.py` compares all 154,190,108 generated pack bytes,
including the source-validation key, against native preparation. Timings vary with
other work on the host; the original complete generated CPU trace was 20.9 s,
and selected-pack traces ranged around 16–26 s.

The browser asset stream copies each prepared record directly into its final
wasm array. The manifest carries the exact dependency stamps used by CPU baking,
so the existing pack header/key/length validation works without browser stat
syscalls. The compressed archive hashes bind the manifest to the payloads.
Consumed packs and source files are released after initialization/first frame.

## Browser behavior

Game-owned page adapters supply the GL uniform, blit, polygon-offset and memcmp
imports missing from Sloppy's web runtime. Float color buffers are enabled;
anisotropy is optional. Shadow draws bind an independent white sample texture
instead of their active depth attachment, avoiding WebGL's feedback-loop error.
With `KHR_parallel_shader_compile`, compilation and uniform lookup are deferred
and all startup links are validated before frames begin. Browsers without that
extension compile synchronously.

Only wasm uses 1024-pixel shadow cascades, scene scale 0.8/0.65 and opening-only
warmup. Native scene settings retain their production policy. Native cold warmup compiles
exact shader/state recipes through a bounded pthread helper; warm caches use the
release runtime directly. Clicking the
canvas unlocks Web Audio and pointer lock. Fullscreen uses an explicit button.

Progress and preferences use Sloppy `save_data`/`load_data`, with separate
`plateau-progress` and `plateau-options` records. Autosaves retain the native
milestone/three-minute rules. Page hide/background saves immediately; Start over
clears progress and reloads while retaining options. Clearing browser storage
clears these records. Native saves and options keep their existing paths.

## Verification

The optional real-browser tool owns a temporary HTTP server and isolated browser
profile. CI does not call it:

```sh
flock /tmp/botw-render.lock env CHROMIUM=/path/to/chromium node tools/web_smoke.cjs
# Startup-only measurement, without the reload/title checks:
flock /tmp/botw-render.lock env WEB_SMOKE_MEASURE_ONLY=1 CHROMIUM=/path/to/chromium node tools/web_smoke.cjs
# CPU logic/asset trace; no real GL context or browser:
BOTW_LOADTIME=1 WEB_PACKS=world,water,farland,chime,textures \
  node tools/web_trace.cjs build/web/raw.html
```

Evidence is retained under `build/web-evidence/`, including `wake-chamber.png`,
`title-shot.png`, `browser-final.json`, `browser-final-console.json`,
`chromium-final.log`, `cold-measure.json`, build/trace logs and native check logs.
The browser captures a normal wake-up, then separately starts near the overlook
with `BOTW_TITLE=1` and walks into the real title trigger. The native opening
check verifies the complete uninterrupted wake/slate/doors/passage/title route.

Chromium 154 with ANGLE/OpenGL on a GTX 1070 rendered both scenes without game,
shader or WebGL feedback-loop errors. Audio was running after a click; pointer
lock, fullscreen, saved progress and resume across reloads passed. One missing
optional `foley-windup-heavy-1.wav` intentionally uses the game's synthesis
fallback, as it does natively. SwiftShader rendered the chamber too, but only
around 0.3 FPS and is unsuitable for playing this scene.

An isolated fresh-profile run measured **33.7 s from loader initialization to the
first rendered callback**, including **2.7 s** to fetch/unpack data over local
HTTP. Both chamber and title measured about **60 FPS** from recent
`requestAnimationFrame` intervals at 1280×720 with the web defaults. These are
headless callback intervals, not display scanout measurements. OS and driver
caches were not flushed. The same build took 64.6 s while CPU baking competed
with browser startup; other simultaneous work also affects frame rates.

Wasm allocated **979 MiB** in the chamber and **987 MiB** at the title. The
isolated run's peak renderer RSS was **1.25 GiB**; summed browser-process PSS
peaked at **3.29 GiB**, including the GPU process/compiler. This remains a large
desktop game: long-session browser memory and physical gamepad mapping have not
been measured. Browsers lacking parallel shader compilation may start slower;
public-network download time remains bandwidth-dependent.

The final site totals about 94.9 MB (86.2 MB of compressed game data); every
archive is below the 100 MB Pages limit and the site is well below 1 GB.
A clean copy of tracked repository inputs rebuilt identical compressed archives,
without prepared caches or the former nature-source symlink.

Native `tools/opening_check.sh`, `tools/prepared_assets_check.sh`,
`tools/save_check.sh` and `sloppy/bin/sloppy tools/input_check.jo` passed. Input
reported 2386/2386 assertions; preparation compared complete generated/prepared
world, mesh, physics, roof, audio and RGBA bytes. Native render checks owned their
single `flock /tmp/botw-render.lock` lock.
