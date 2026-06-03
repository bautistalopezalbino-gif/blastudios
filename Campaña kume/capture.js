const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const OUT = __dirname;
const URL = 'https://kumepasteleria.com';
const PORT = 9224;

const sleep = ms => new Promise(r => setTimeout(r, ms));
const pending = new Map();
let msgId = 1;

function send(ws, method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = msgId++;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
    setTimeout(() => {
      if (pending.has(id)) { pending.delete(id); reject(new Error(`Timeout: ${method}`)); }
    }, 20000);
  });
}

function getWS() {
  return new Promise((resolve, reject) => {
    let n = 0;
    const try_ = () => {
      http.get(`http://127.0.0.1:${PORT}/json`, res => {
        let d = '';
        res.on('data', c => d += c);
        res.on('end', () => {
          try { resolve((JSON.parse(d).find(t => t.type === 'page') || JSON.parse(d)[0]).webSocketDebuggerUrl); }
          catch(e) { if(++n<15) setTimeout(try_,400); else reject(e); }
        });
      }).on('error', () => { if(++n<15) setTimeout(try_,400); else reject(new Error('Chrome no responde')); });
    };
    try_();
  });
}

async function main() {
  console.log('Iniciando Chrome...');
  const chrome = spawn(CHROME, [
    `--remote-debugging-port=${PORT}`, '--headless=new', '--disable-gpu',
    '--no-sandbox', '--window-size=1440,900', '--hide-scrollbars', 'about:blank'
  ]);
  chrome.stderr.on('data', () => {});

  await sleep(2000);
  const wsUrl = await getWS();
  const ws = new WebSocket(wsUrl);
  ws.onmessage = e => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) {
      const p = pending.get(m.id); pending.delete(m.id);
      m.error ? p.reject(new Error(m.error.message)) : p.resolve(m.result || {});
    }
  };
  ws.onerror = e => {};
  await new Promise((res,rej) => { ws.onopen = res; setTimeout(()=>rej(new Error('WS timeout')),5000); });

  await send(ws, 'Page.enable');
  await send(ws, 'Network.enable');
  await send(ws, 'Runtime.enable');

  console.log('Cargando página...');
  await send(ws, 'Page.navigate', { url: URL });
  await sleep(5000);

  // Scroll para activar lazy-load
  await send(ws, 'Runtime.evaluate', { expression: 'window.scrollTo(0, document.body.scrollHeight)' });
  await sleep(2000);
  await send(ws, 'Runtime.evaluate', { expression: 'window.scrollTo(0, 0)' });
  await sleep(1000);

  const r = await send(ws, 'Runtime.evaluate', {
    expression: `JSON.stringify({ h: document.documentElement.scrollHeight })`,
    returnByValue: true
  });
  const { h } = JSON.parse(r.result.value);
  console.log(`Altura total: ${h}px`);

  // Capturar sección por sección (bloques de 2500px)
  const CHUNK = 2500;
  const chunks = [];
  let y = 0;
  let chunkIdx = 0;

  while (y < Math.min(h, 7500)) {
    const chunkH = Math.min(CHUNK, h - y);
    console.log(`Capturando bloque ${chunkIdx+1}: y=${y}, h=${chunkH}px...`);

    // Ajustar viewport a la posición del bloque
    await send(ws, 'Emulation.setDeviceMetricsOverride', {
      width: 1440, height: chunkH, deviceScaleFactor: 1, mobile: false
    });
    await send(ws, 'Runtime.evaluate', { expression: `window.scrollTo(0, ${y})` });
    await sleep(500);

    const shot = await send(ws, 'Page.captureScreenshot', {
      format: 'png',
      captureBeyondViewport: true,
      clip: { x: 0, y: y, width: 1440, height: chunkH, scale: 1 }
    });

    const file = path.join(OUT, `kume_chunk_${chunkIdx}.png`);
    fs.writeFileSync(file, Buffer.from(shot.data, 'base64'));
    const kb = Math.round(fs.statSync(file).size / 1024);
    console.log(`  Guardado: kume_chunk_${chunkIdx}.png (${kb}KB)`);
    chunks.push(file);

    y += CHUNK;
    chunkIdx++;
  }

  ws.close();
  chrome.kill();

  console.log(`\n✅ ${chunks.length} bloques capturados:`);
  chunks.forEach((f, i) => console.log(`  ${i}: ${path.basename(f)}`));
  process.exit(0);
}

main().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
