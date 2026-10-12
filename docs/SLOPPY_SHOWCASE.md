# What this tree shows about Sloppy

One language drives world generation, Vulkan/SPIR-V and OpenGL/GLSL rendering,
physics, element reactions, animation and software audio. Production functions
also power headless tests and deterministic captures. The pinned toolchain is
the **unmodified official Sloppy 0.6.0 release**, `7c8d133`; every adapter belongs
to the game.

Prepared packs retain world, mesh, collision, roof, audio and texture bytes and
named-mesh draw order. Fresh-export startup separates compilation, in-game load,
first-callback CPU and whole process. The Linux package includes the source
files and materialized texture dependencies that its pack keys require.
[Current measurements, protocols and evidence](PERFORMANCE.md).

The migration keeps actor mutation in place while releasing references before
camp alarms, and preserves the old CPU pine-width seed explicitly. Game-owned
20 ms score envelopes smooth gain changes without patching the live mixer.
[Audio levels and transition verification](MUSIC.md).

Vulkan adapters supply signed derivatives, static mip pyramids, R32F textures,
shadow bias, snapshots and typed readback. Upload batches fit Pascal's small
host-visible device-memory aperture. OpenGL remains available with
`SLOPPY_VULKAN=0`; Vulkan retains some shading/filtering differences, including
absence of the OpenGL path's 8× anisotropy.

Presentation probes measure producer returns and CPU, not scanout or delivered
frames. GLES per-pass timer queries apply only to OpenGL. The launchers select
`SLOPPY_VSYNC=0` after lower measured p99 in forest, fire and overlook; direct
release launches default to FIFO. The performance report retains every outlier
and counts complete windows over 20 and 17.5 ms.

[Runtime adapters and historical language findings](SLOPPY_NOTES.md),
[movement reference gaps](MOVEMENT_REFERENCE.md),
[pre-0.6 performance history](rounds/PERFORMANCE_PRE_060.md).
