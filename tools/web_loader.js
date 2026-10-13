// Game-owned adapter for the unmodified Sloppy 0.6.0 web runtime.
const botwWeb = {
  startedAt: performance.now(), filesRead: new Set(), missingFiles: new Set(),
  frames: 0, frameTimes: [], shaders: [], programs: [], peakWasmBytes: 0, errors: [], state: 'loading',
};
if (typeof window !== 'undefined') window.botwWeb = botwWeb;
let botwManifest = null;
sloppy.extra.push({
  imports(getMem, getExports) {
    const dec = new TextDecoder(), enc = new TextEncoder(), streams = new Map();
    let next = 0;
    const text = (p, n) => dec.decode(new Uint8Array(getMem().buffer, Number(p), Number(n)));
    const gl = () => document.getElementById('sloppy-canvas').getContext('webgl2');
    const imports = {
      __web_asset_open(p, n) {
        const path = text(p, n);
        let bytes = sloppy.files[path];
        if (typeof window === 'undefined' && typeof sloppyFs !== 'undefined') {
          const allowed = (process.env.WEB_PACKS || '').split(',');
          if (!allowed.includes(path.split('/').pop().replace('.bin', ''))) return -1n;
          try { bytes = new Uint8Array(sloppyFs.readFileSync(path)); } catch (_) {}
        }
        botwWeb.filesRead.add(path);
        if (!bytes) return -1n;
        const id = next++;
        streams.set(id, {bytes, at: 0, path});
        return BigInt(id);
      },
      __web_asset_size(id) { return BigInt(streams.get(Number(id)).bytes.length); },
      __web_asset_read(id, p, n) {
        const s = streams.get(Number(id)), size = Number(n);
        if (!s || size < 0 || s.at + size > s.bytes.length) return -1n;
        new Uint8Array(getMem().buffer).set(s.bytes.subarray(s.at, s.at + size), Number(p));
        s.at += size;
        return n;
      },
      __web_asset_close(id) {
        const s = streams.get(Number(id));
        if (s) delete sloppy.files[s.path];
        streams.delete(Number(id));
      },
      __web_asset_stamp(p, n, out, cap) {
        const path = text(p, n);
        let stamp = botwManifest?.stamps[path] || 'missing';
        if (typeof window === 'undefined' && typeof sloppyFs !== 'undefined') {
          try {
            const st = sloppyFs.statSync(path, {bigint:true});
            stamp = `${st.size}:${st.mtimeNs / 1000000000n}:${st.mtimeNs % 1000000000n}`;
          } catch (_) {}
        }
        const bytes = enc.encode(stamp);
        new Uint8Array(getMem().buffer).set(bytes.subarray(0, Number(cap)), Number(out));
        return BigInt(bytes.length);
      },
      __draw_memcmp(a, b, n) {
        const bytes = new Uint8Array(getMem().buffer);
        for (let i = 0; i < Number(n); i++) if (bytes[Number(a) + i] !== bytes[Number(b) + i]) return 1;
        return 0;
      },
      glBlitFramebuffer: (...args) => gl().blitFramebuffer(...args),
      glPolygonOffset: (factor, units) => gl().polygonOffset(factor, units),
      glTexParameterf(target, name, value) {
        // Anisotropy is optional in WebGL 2.
        if (name !== 0x84fe || gl().getExtension('EXT_texture_filter_anisotropic')) gl().texParameterf(target, name, value);
      },
      __web_restart: () => location.reload(),
    };
    imports.memcmp = imports.__draw_memcmp;
    // EGL timing/vsync has no browser equivalent (requestAnimationFrame paces frames).
    imports.eglGetCurrentDisplay = imports.eglGetProcAddress = () => 0;
    imports.eglSwapInterval = () => 0;
    botwWeb.memory = getMem;
    botwWeb.exports = getExports;
    return imports;
  },
  start(ex) {
    if (typeof window === 'undefined') return;
    // Keep progress on tab close/background, including between autosave ticks.
    const save = () => ex.__web_save && ex.__web_save();
    window.addEventListener('pagehide', save);
    document.addEventListener('visibilitychange', () => { if (document.hidden) save(); });

  },
});

// Extend the registered graphics adapter, preserving its own integer GL handles.
for (const module of sloppy.extra) {
  if (module === sloppy.extra[sloppy.extra.length - 1]) continue;
  const originalImports = module.imports;
  module.imports = function (...args) {
    const imports = originalImports.apply(this, args);
    if (imports.glBindFramebuffer) imports.gl_bind_fb_target = imports.glBindFramebuffer;
    if (imports.glCreateProgramFrom && typeof window !== 'undefined') {
      const programs = new Map(), locations = new Map();
      const gl = () => document.getElementById('sloppy-canvas').getContext('webgl2');
      const create = imports.glCreateProgramFrom;
      imports.glCreateProgramFrom = (...a) => {
        const context = gl(), original = context.createProgram, shaderSource = context.shaderSource;
        const began = performance.now(); let sourceBytes = 0;
        const parallel = context.getExtension('KHR_parallel_shader_compile');
        const shaderParameter = context.getShaderParameter, programParameter = context.getProgramParameter;
        // Querying COMPILE_STATUS here serializes the driver's compiler. With
        // KHR_parallel_shader_compile, validate links after all startup work.
        if (parallel && botwWeb.state === 'starting') {
          context.getShaderParameter = function(shader, name) {
            return name === this.COMPILE_STATUS ? true : shaderParameter.call(this, shader, name);
          };
          context.getProgramParameter = function(program, name) {
            return name === this.LINK_STATUS ? true : programParameter.call(this, program, name);
          };
        }
        context.shaderSource = function(shader, source) {
          sourceBytes += source.length;
          shaderSource.call(this, shader, source);
        };
        let program;
        context.createProgram = function () { program = original.call(this); return program; };
        try {
          const id = create(...a); programs.set(id, program);
          if (parallel && botwWeb.state === 'starting') botwWeb.programs.push({program, parallel});
          return id;
        } finally {
          context.createProgram = original; context.shaderSource = shaderSource;
          context.getShaderParameter = shaderParameter; context.getProgramParameter = programParameter;
          botwWeb.shaders.push({ms: performance.now() - began, bytes: sourceBytes});
        }
      };
      let nextLocation = 0;
      const locationFor = id => {
        if (id < 0) return null;
        const entry = locations.get(id);
        if (!entry) return null;
        if (!entry.resolved) {
          entry.location = gl().getUniformLocation(programs.get(entry.program), entry.name);
          entry.resolved = true;
        }
        return entry.location;
      };
      imports.glGetUniformLocationStr = (program, p, n) => {
        const name = new TextDecoder().decode(new Uint8Array(args[0]().buffer, Number(p), Number(n)));
        const id = nextLocation++;
        locations.set(id, {program, name, resolved:false});
        return id;
      };
      // Defer uniform lookup too: it otherwise waits for a pending shader link.
      for (const name of ['uniform1i','uniform1f','uniform2f','uniform3f','uniform4f','uniform4i'])
        imports['gl' + name[0].toUpperCase() + name.slice(1)] = (id, ...values) => gl()[name](locationFor(id), ...values);
      for (const [name, type, width] of [['uniform1iv', Int32Array, 1], ['uniform2iv', Int32Array, 2],
          ['uniform1fv', Float32Array, 1], ['uniform2fv', Float32Array, 2],
          ['uniform3fv', Float32Array, 3], ['uniform4fv', Float32Array, 4]])
        imports['gl' + name[0].toUpperCase() + name.slice(1)] = (id, n, p) =>
          gl()[name](locationFor(id), new type(args[0]().buffer, Number(p), Number(n) * width));
      imports.glUniformMatrix4fv = (id, n, transpose, p) => gl().uniformMatrix4fv(locationFor(id), !!transpose,
        new Float32Array(args[0]().buffer, Number(p), Number(n) * 16));
    }
    if (imports.__web_canvas_open && typeof window !== 'undefined') {
      const open = imports.__web_canvas_open;
      imports.__web_canvas_open = (...a) => {
        open(...a);
        const gl = document.getElementById('sloppy-canvas').getContext('webgl2');
        if (!gl.getExtension('EXT_color_buffer_float')) throw new Error('This game requires EXT_color_buffer_float');
        gl.getExtension('OES_texture_float_linear');
        botwWeb.renderer = gl.getParameter(gl.RENDERER);
      };
    }
    return imports;
  };
  if (module.start) {
    const start = module.start;
    module.start = ex => {
      const begin = () => start(new Proxy({...ex}, {get(target, key) {
      if (key !== '__frame') return target[key];
      return t => {
        const before = performance.now();
        try { target.__frame(t); } catch (e) { botwFail(e); throw e; }
        const after = performance.now();
        botwWeb.frames++;
        botwWeb.peakWasmBytes = Math.max(botwWeb.peakWasmBytes, target.memory.buffer.byteLength);
        if (botwWeb.lastFrame) {
          botwWeb.frameTimes.push({interval: after - botwWeb.lastFrame, cpu: after - before});
          if (botwWeb.frameTimes.length > 600) botwWeb.frameTimes.shift();
        }
        botwWeb.lastFrame = after;
        if (botwWeb.frames === 1) {
          for (const path of Object.keys(sloppy.files)) if (path.startsWith('assets/')) delete sloppy.files[path];
          botwWeb.state = 'playing';
          botwWeb.readyMs = after - botwWeb.startedAt;
          document.getElementById('botw-loading').hidden = true;
          document.getElementById('botw-fullscreen').hidden = false;
          console.log('WEB_READY', JSON.stringify({startupMs: botwWeb.readyMs, wasmBytes: botwWeb.peakWasmBytes}));
        }
      };
      }}));
      if (typeof window !== 'undefined' && botwWeb.state === 'starting') botwWeb.beginFrames = begin;
      else begin();
    };
  }
}
// Track successful and missing ordinary reads (including paths probed before allocation).
{
  const read = sloppy.env.__wasm_read_file;
  sloppy.env.__wasm_read_file = (p, n, out, cap) => {
    const path = new TextDecoder().decode(new Uint8Array(botwWeb.memory().buffer, Number(p), Number(n)));
    const result = read(p, n, out, cap);
    if (path.startsWith('assets/')) {
      botwWeb.filesRead.add(path);
      if (result < 0n) botwWeb.missingFiles.add(path);
    }
    return result;
  };
}
function botwFail(error) {
  botwWeb.state = 'error';
  botwWeb.errors.push(String(error.stack || error));
  const loading = document.getElementById('botw-loading');
  loading.hidden = false;
  document.getElementById('botw-status').textContent = 'Could not load: ' + error.message;
  document.getElementById('botw-progress').hidden = true;
  console.error(error);
}
async function botwBoot(bin) {
  try {
    if (typeof DecompressionStream === 'undefined') throw new Error('This browser needs gzip DecompressionStream support');
    const response = await fetch('manifest.json');
    if (!response.ok) throw new Error('manifest.json: HTTP ' + response.status);
    botwManifest = await response.json();
    let downloaded = 0;
    const total = botwManifest.archives.reduce((sum, a) => sum + a.bytes, 0);
    const progress = () => {
      const percent = Math.min(99, Math.floor(downloaded / total * 99));
      document.getElementById('botw-status').textContent = 'Loading ' + percent + '%';
      document.getElementById('botw-progress').value = percent;
    };
    for (const archive of botwManifest.archives) {
      const response = await fetch(archive.url);
      if (!response.ok) throw new Error(archive.url + ': HTTP ' + response.status);
      const reader = response.body.getReader(), chunks = [];
      let length = 0;
      for (;;) {
        const {done, value} = await reader.read();
        if (done) break;
        chunks.push(value); length += value.length; downloaded += value.length; progress();
      }
      if (length !== archive.bytes) throw new Error('Truncated archive: ' + archive.url);
      const compressed = new Blob(chunks);
      if (crypto.subtle) {
        const digest = await crypto.subtle.digest('SHA-256', await compressed.arrayBuffer());
        const hash = Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, '0')).join('');
        if (hash !== archive.sha256) throw new Error('Archive checksum mismatch: ' + archive.url);
      }
      chunks.length = 0;
      const unpack = compressed.stream().pipeThrough(new DecompressionStream('gzip')).getReader();
      let fileIndex = 0, at = 0, file = archive.files[0];
      let bytes = new Uint8Array(file.bytes);
      for (;;) {
        const {done, value} = await unpack.read();
        if (done) break;
        let offset = 0;
        while (offset < value.length) {
          if (!file) throw new Error('Oversized archive: ' + archive.url);
          const n = Math.min(bytes.length - at, value.length - offset);
          bytes.set(value.subarray(offset, offset + n), at); at += n; offset += n;
          if (at === bytes.length) {
            sloppy.files[file.path] = bytes;
            file = archive.files[++fileIndex]; at = 0;
            bytes = file ? new Uint8Array(file.bytes) : null;
          }
        }
      }
      if (file) throw new Error('Incomplete archive: ' + archive.url);
    }
    botwWeb.downloadBytes = total;
    botwWeb.assetLoadMs = performance.now() - botwWeb.startedAt;
    botwWeb.state = 'starting';
    // Give the progress UI a paint before synchronous wasm initialization.
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    sloppy.run(bin);
    const gl = document.getElementById('sloppy-canvas').getContext('webgl2');
    const deadline = performance.now() + 180000;
    while (botwWeb.programs.some(({program, parallel}) => !gl.getProgramParameter(program, parallel.COMPLETION_STATUS_KHR))) {
      if (performance.now() > deadline) throw new Error('Shader compilation exceeded 180 seconds');
      await new Promise(resolve => setTimeout(resolve, 25));
    }
    for (const {program} of botwWeb.programs) {
      if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error('Shader link: ' + gl.getProgramInfoLog(program));
    }
    botwWeb.programs.length = 0;
    botwWeb.beginFrames();
    botwWeb.peakWasmBytes = botwWeb.memory().buffer.byteLength;
  } catch (e) { botwFail(e); }
}
