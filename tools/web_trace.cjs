// CPU-only wasm startup trace. Real files; GL/audio calls are inert, no frame loop.
const fs = require('node:fs');
const vm = require('node:vm');
const {performance} = require('node:perf_hooks');
const page = process.argv[2] || 'build/web/raw.html';
const trace = new Set();
const tracedFs = new Proxy(fs, {get(target, key) {
  if (key === 'readFileSync') return (path, ...args) => {
    const result = target.readFileSync(path, ...args);
    if (String(path).startsWith('assets/')) trace.add(String(path));
    return result;
  };
  return target[key];
}});
const ctx = {console, process, Buffer, TextDecoder, TextEncoder, WebAssembly, performance,
  Proxy, Error, Uint8Array, Object, setTimeout, sloppyFs: tracedFs, sloppyArgs: ['plateau']};
vm.createContext(ctx);
let script = fs.readFileSync(page, 'utf8').match(/<script>([\s\S]*)<\/script>/)[1];
script = script.slice(0, script.indexOf('// start the program once all runtime modules'));
vm.runInContext(script, ctx);
vm.runInContext(`
sloppy.extra.length = 0;
sloppy.extra.push({imports(getMem, getExports) {
  globalThis.webMemory = getMem; globalThis.webExports = getExports;
  const imports = {};
  const bin = Buffer.from(SLOPPY_WASM, 'base64');
  for (const {name} of WebAssembly.Module.imports(new WebAssembly.Module(bin))) {
    if (name.startsWith('gl') || name.startsWith('__web_')) imports[name] = () => 0;
  }
  imports.__web_canvas_size = p => { new Int32Array(getMem().buffer, Number(p), 2).set([1280,720]); };
  imports.glCreateProgramFrom = () => 1;
  return imports;
}});
`, ctx);
vm.runInContext(fs.readFileSync('tools/web_loader.js', 'utf8'), ctx);
vm.runInContext(`
sloppy.extra.push({imports() { return {glTexParameterf:()=>0,glPolygonOffset:()=>0,glBlitFramebuffer:()=>0}; }});
sloppy.run(Buffer.from(SLOPPY_WASM, 'base64'));
if (!process.exitCode) webExports().__frame(performance.now());
`, ctx);
if (process.exitCode) process.exit(process.exitCode);
fs.mkdirSync('build/web-evidence', {recursive:true});
fs.writeFileSync('build/web-evidence/reads.json', JSON.stringify([...trace].sort(), null, 2));
console.log('WEB_TRACE', JSON.stringify({files:trace.size, seconds:performance.now()/1000,
  wasmBytes:ctx.webMemory().buffer.byteLength, rss:process.memoryUsage().rss}));
