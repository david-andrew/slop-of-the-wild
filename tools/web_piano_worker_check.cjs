// CPU-only verification: worker output uses the exact native compact-pack layout.
const fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync('build/web/piano-worker.html','utf8');
let runtime=html.match(/<script>([\s\S]*)<\/script>/)[1].split('// start the program once all runtime modules')[0];
const files=Object.fromEntries(fs.readdirSync('assets/audio').filter(p=>/^piano-(pp|mf|ff)-\d+\.wav$/.test(p)).map(p=>['assets/audio/'+p,new Uint8Array(fs.readFileSync('assets/audio/'+p))]));
let result;
const context={console,process:{env:{},stdout:{write:s=>process.stdout.write(s)},stderr:{write:s=>process.stderr.write(s)}},performance,WebAssembly,TextEncoder,TextDecoder,Uint8Array,DataView,atob,self:{postMessage:data=>result=data}};
vm.createContext(context);vm.runInContext(runtime+'\n'+fs.readFileSync('tools/web_piano_worker.js','utf8'),context);
const stamps={};
// Match native dependency stamps directly; this test does not require a site build.
for(const dir of ['game','sloppy/lib/game','sloppy/lib/core','assets/audio']) {
 for(const name of fs.readdirSync(dir)) {
  const path=dir+'/'+name,st=fs.statSync(path,{bigint:true});
  if(st.isFile())stamps[path]=`${st.size}:${st.mtimeNs/1000000000n}:${st.mtimeNs%1000000000n}`;
 }
}
const paths=fs.readdirSync('assets/audio').filter(p=>p.endsWith('.wav')).map(p=>'assets/audio/'+p);
context.self.onmessage({data:{files,paths,stamps}});
if(result.error) throw new Error(result.error);
const native=fs.readFileSync(process.argv[2]||'assets/prepared/piano-compact.bin'), actual=Buffer.from(result.pack);
fs.mkdirSync('build/task69-sol',{recursive:true});fs.writeFileSync('build/task69-sol/worker-piano.bin',actual);
if(!actual.equals(native)) {
 let differences=0,first=-1;
 for(let i=0;i<Math.max(native.length,actual.length);i++) if(native[i]!==actual[i]){differences++;if(first<0)first=i;}
 throw new Error(`Worker/native payload differs: ${differences} bytes, first ${first}; lengths ${actual.length}/${native.length}`);
}
fs.writeFileSync('build/task69-sol/worker-piano-summary.json',JSON.stringify({bytes:actual.length,ms:result.ms,payloadMatchesNative:true},null,2));
console.log('PASS browser piano worker: exact native sample/cue bytes, '+actual.length+' bytes, '+result.ms.toFixed(1)+' ms');
