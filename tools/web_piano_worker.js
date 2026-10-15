// Appended to the generated CPU worker runtime by web_package.py.
// Production DSP runs alongside world/graphics initialization. Transfer the
// exact compact pack once; frames begin only after its validated load succeeds.
let workerMemory, workerExports;
self.onmessage = ({data}) => {
  try {
    const began = performance.now();
    Object.assign(sloppy.files, data.files);
    // The shared audio fingerprint includes Foley stamps too. Their samples
    // stay on the main thread; retain just directory entries in this worker.
    for(const path of data.paths || []) if(!sloppy.files[path]) sloppy.files[path]=new Uint8Array(0);
    sloppy.extra.length = 0;
    const binary = Uint8Array.from(atob(SLOPPY_WASM), c => c.charCodeAt(0));
    sloppy.extra.push({imports(getMem, getExports) {
      workerMemory = getMem; workerExports = getExports;
      const decoder = new TextDecoder();
      const text = (p,n) => decoder.decode(new Uint8Array(getMem().buffer,Number(p),Number(n)));
      const imports = {};
      for (const {name} of WebAssembly.Module.imports(new WebAssembly.Module(binary))) {
        if (name.startsWith('gl') || name.startsWith('__web_')) imports[name] = () => 0;
      }
      imports.__web_piano_deferred = () => 0n;
      imports.__web_asset_open = () => -1n;
      imports.__web_asset_stamp = (p,n,out,cap) => {
        const bytes = new TextEncoder().encode(data.stamps[text(p,n)] || 'missing');
        new Uint8Array(getMem().buffer).set(bytes.subarray(0,Number(cap)),Number(out));
        return BigInt(bytes.length);
      };
      return imports;
    }});
    sloppy.run(binary);
    if (process.exitCode) throw new Error("Piano worker initialization failed: " + process.exitCode);
    const ex=workerExports(), count=Number(ex.__piano_count()), records=[];
    let size=16;
    for(let bank=0;bank<7;bank++) {
      size+=8;
      for(let slot=0;slot<count;slot++) {
        const n=Number(ex.__piano_length(BigInt(bank),BigInt(slot)));
        records.push({bank,slot,n}); size+=12+n*2;
      }
    }
    for(let cue=0;cue<4;cue++) size+=8+Number(ex.__piano_cue_length(BigInt(cue)))*4;
    const pack=new Uint8Array(size), view=new DataView(pack.buffer);let at=0;
    const int = n => {view.setBigUint64(at,BigInt.asUintN(64,BigInt(n)),true);at+=8;};
    const copy = (p,n) => {pack.set(new Uint8Array(workerMemory().buffer,Number(p),n),at);at+=n;};
    int(0x42575049414E4F32n);int(ex.__piano_key());
    for(let bank=0;bank<7;bank++) {
      int(count);
      for(const record of records.filter(r=>r.bank===bank)) {
        const slot=BigInt(record.slot);int(record.n);
        view.setFloat32(at,ex.__piano_scale(BigInt(bank),slot),true);at+=4;
        copy(ex.__piano_data(BigInt(bank),slot),record.n*2);
      }
    }
    for(let cue=0;cue<4;cue++) {
      const n=Number(ex.__piano_cue_length(BigInt(cue)));int(n);
      copy(ex.__piano_cue_data(BigInt(cue)),n*4);
    }
    if(at!==size) throw new Error('Piano pack length mismatch');
    self.postMessage({pack,ms:performance.now()-began},[pack.buffer]);
  } catch(error) {self.postMessage({error:String(error.stack||error)});}
};
