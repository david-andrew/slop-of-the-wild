// Optional real-browser smoke/measurements. Not used by the CPU-only site builder.
// CHROMIUM=/path/to/chromium node tools/web_smoke.cjs http://localhost:8765/
const fs = require('node:fs');
const {spawn} = require('node:child_process');
const {setTimeout: delay} = require('node:timers/promises');
let base = process.argv[2];
let server;
const binary = process.env.CHROMIUM || 'chromium';
const root = 'build/web-evidence'; fs.mkdirSync(root, {recursive:true});
const profile = fs.mkdtempSync(root + '/chrome-profile-');
const browser = spawn(binary, ['--headless', '--no-sandbox', '--disable-dev-shm-usage',
  '--enable-gpu', '--enable-precise-memory-info', '--ignore-gpu-blocklist', '--use-gl=angle', '--use-angle=gl',
  '--remote-debugging-port=0', '--user-data-dir=' + profile,
  '--window-size=1280,720', 'about:blank'], {stdio:['ignore','ignore','pipe']});
const log = fs.createWriteStream(root + '/chromium.log'); browser.stderr.pipe(log);
let debugUrl;
browser.stderr.on('data', chunk => { const match = String(chunk).match(/DevTools listening on (ws:\/\/\S+)/); if (match) debugUrl = match[1]; });
process.on('SIGTERM', () => { browser.kill('SIGTERM'); if (server) server.close(); process.exit(143); });
let peakRendererRss = 0, peakProcessPss = 0;
const sampleMemory = setInterval(() => {
  function visit(pid) {
    try {
      const status = fs.readFileSync(`/proc/${pid}/status`, 'utf8');
      const cmd = fs.readFileSync(`/proc/${pid}/cmdline`, 'utf8');
      if (cmd.includes('--type=renderer')) peakRendererRss = Math.max(peakRendererRss,
        Number(status.match(/VmRSS:\s+(\d+)/)?.[1] || 0) * 1024);
      let pss = Number(fs.readFileSync(`/proc/${pid}/smaps_rollup`, 'utf8').match(/\nPss:\s+(\d+)/)?.[1] || 0) * 1024;
      const children = fs.readFileSync(`/proc/${pid}/task/${pid}/children`, 'utf8').trim().split(/\s+/).filter(Boolean);
      for (const child of children) pss += visit(child);
      return pss;
    } catch (_) { return 0; }
  }
  peakProcessPss = Math.max(peakProcessPss, visit(browser.pid));
}, 250);
const pending = new Map(); let serial = 0, ws, session;
const events = [];
async function send(method, params={}, sessionId=session) {
  const id = ++serial;
  return new Promise((resolve,reject) => {
    const timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP timeout: '+method));}, 180000);
    pending.set(id, {resolve,reject,timer});
    ws.send(JSON.stringify({id,method,params,...(sessionId?{sessionId}:{})}));
  });
}
async function evaluate(expression) {
  const result = await send('Runtime.evaluate', {expression,returnByValue:true,awaitPromise:true});
  if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
  return result.result.value;
}
async function waitReady() {
  const deadline = Date.now() + 240000;
  while (Date.now()<deadline) {
    const status = await evaluate('window.botwWeb && ({state:botwWeb.state,frames:botwWeb.frames,errors:botwWeb.errors})');
    if (status?.state === 'error') throw new Error(JSON.stringify(status.errors));
    if (status?.state === 'playing') return;
    await delay(500);
  }
  throw new Error('No first frame within 240 seconds');
}
async function capture(name) {
  const {data}=await send('Page.captureScreenshot',{format:'png'});
  fs.writeFileSync(`${root}/${name}.png`,Buffer.from(data,'base64'));
}
const metrics = `(() => {
 const times=botwWeb.frameTimes.slice(-120), average=key=>times.reduce((s,x)=>s+x[key],0)/times.length;
 const gl=document.getElementById('sloppy-canvas').getContext('webgl2'), ext=gl.getExtension('WEBGL_debug_renderer_info');
 return {state:botwWeb.state,frames:botwWeb.frames,startupMs:botwWeb.readyMs,assetLoadMs:botwWeb.assetLoadMs,
   wasmBytes:botwWeb.peakWasmBytes,heapBytes:performance.memory?.usedJSHeapSize,
   fps:1000/average('interval'),cpuMs:average('cpu'),errors:botwWeb.errors,missing:[...botwWeb.missingFiles],
   shaders:botwWeb.shaders,renderer:ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER)};
})()`;
(async()=>{
  try {
    if (!base) {
      const path = require('node:path'), site = path.resolve('build/site');
      server = require('node:http').createServer((req, res) => {
        const relative = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
        const file = path.resolve(site, '.' + (relative === '/' ? '/index.html' : relative));
        if (!file.startsWith(site + '/')) { res.writeHead(403).end(); return; }
        try {
          const stat = fs.statSync(file);
          res.writeHead(200, {'Content-Length':stat.size,
            'Content-Type':file.endsWith('.html')?'text/html':file.endsWith('.json')?'application/json':'application/octet-stream'});
          fs.createReadStream(file).pipe(res);
        } catch (_) { res.writeHead(404).end(); }
      });
      await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
      base = `http://127.0.0.1:${server.address().port}/`;
    }
    let version;
    for(let i=0;i<60;i++) {
      if(browser.exitCode!==null) throw new Error('Chromium exited '+browser.exitCode+'; see chromium.log');
      try {if (debugUrl) {version=await (await fetch('http://'+new URL(debugUrl).host+'/json/version')).json();break;}} catch(_) {}
      await delay(250);
    }
    if(!version) throw new Error('No Chromium debug endpoint');
    ws=new WebSocket(version.webSocketDebuggerUrl);
    await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
    ws.onmessage=e=>{
      const msg=JSON.parse(e.data), p=pending.get(msg.id);
      if(p){pending.delete(msg.id);clearTimeout(p.timer);msg.error?p.reject(new Error(JSON.stringify(msg.error))):p.resolve(msg.result);}
      else if(msg.method==='Runtime.consoleAPICalled'||msg.method==='Runtime.exceptionThrown') { events.push(msg); fs.writeFileSync(root+'/browser-console.json',JSON.stringify(events,null,2)); }
    };
    const target=await send('Target.createTarget',{url:'about:blank'},null);
    session=(await send('Target.attachToTarget',{targetId:target.targetId,flatten:true},null)).sessionId;
    await send('Page.enable'); await send('Runtime.enable');
    await send('Emulation.setDeviceMetricsOverride',{width:1280,height:720,deviceScaleFactor:1,mobile:false});
    await send('Page.addScriptToEvaluateOnNewDocument',{source:`
      if(window.AudioContext) window.AudioContext=new Proxy(window.AudioContext,{construct(T,args){const c=new T(...args);window.webAudio=c;return c;}});
    `});
    await send('Page.navigate',{url:base}); await waitReady();
    await delay(4000); await capture('wake-chamber');
    const wake=await evaluate(metrics);
    console.log('WAKE',JSON.stringify(wake));
    if (process.env.WEB_SMOKE_MEASURE_ONLY === '1') {
      fs.writeFileSync(root+'/cold-measure.json', JSON.stringify({version:version.Browser,wake,peakRendererRss,peakProcessPss},null,2));
      return;
    }
    await send('Input.dispatchMouseEvent',{type:'mousePressed',x:640,y:360,button:'left',clickCount:1});
    await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:640,y:360,button:'left',clickCount:1});
    await delay(1000);
    const interaction=await evaluate(`({pointerLock:!!document.pointerLockElement,audio:window.webAudio?.state})`);
    await evaluate('botwWeb.exports().__web_save()');
    const saved=await evaluate(`Object.entries(localStorage).filter(([k])=>k.endsWith('/plateau-progress')).map(([key,value])=>({key,bytes:atob(value).length}))`);
    await send('Page.navigate',{url:base});await waitReady();
    const resumed=await evaluate(`document.getElementById('log').textContent.includes('Resumed plateau progress')`);
    await evaluate('document.exitPointerLock()');
    await send('Input.dispatchMouseEvent',{type:'mousePressed',x:1230,y:25,button:'left',clickCount:1});
    await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:1230,y:25,button:'left',clickCount:1});
    const fullscreen=await evaluate('!!document.fullscreenElement');
    const resume=await evaluate(metrics);
    await send('Page.navigate',{url:base+(base.includes('?')?'&':'?')+'BOTW_TITLE=1'});await waitReady();
    await send('Input.dispatchKeyEvent',{type:'keyDown',key:'w',code:'KeyW',windowsVirtualKeyCode:87});
    await delay(4500);
    await send('Input.dispatchKeyEvent',{type:'keyUp',key:'w',code:'KeyW',windowsVirtualKeyCode:87});
    await delay(8500);await capture('title-shot');
    const title=await evaluate(metrics);
    const result={version:version.Browser,wake,resume,title,interaction,saved,resumed,fullscreen,peakRendererRss,peakProcessPss};
    fs.writeFileSync(root+'/browser.json',JSON.stringify(result,null,2));
    fs.writeFileSync(root+'/browser-console.json',JSON.stringify(events,null,2));
    console.log(JSON.stringify(result,null,2));
    if(!saved.length||!resumed||!interaction.pointerLock||interaction.audio!=='running'||!fullscreen||wake.errors.length||title.errors.length) throw new Error('Browser smoke assertions failed');
  } finally {
    if(server) server.close(); clearInterval(sampleMemory); if(ws) ws.close(); browser.kill('SIGTERM'); log.end();
    if(browser.exitCode===null&&browser.signalCode===null) await new Promise(r=>browser.once('exit',r));
    fs.rmSync(profile,{recursive:true,force:true,maxRetries:5});
  }
})().catch(e=>{console.error(e);process.exitCode=1;});
