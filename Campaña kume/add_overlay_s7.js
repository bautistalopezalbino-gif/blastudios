// Añade el overlay de texto de la historia 7 al video original
const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const FFMPEG = 'C:\\Users\\EMILIANO JAVIER LOPE\\AppData\\Local\\Microsoft\\WinGet\\Packages\\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\\ffmpeg-8.1.1-full_build\\bin\\ffmpeg.exe';
const PORT = 9230;
const OUT  = __dirname;

// HTML con exactamente los mismos elementos visuales que la historia 7
const OVERLAY_HTML = `<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }
  body { width:390px; height:693px; overflow:hidden; background:transparent; position:relative; }
  .overlay {
    position:absolute; inset:0;
    background:linear-gradient(to bottom,
      rgba(0,0,0,0.22) 0%,
      transparent 45%,
      rgba(0,0,0,0.82) 100%);
  }
  .brand {
    position:absolute; top:52px; left:32px;
    font-family:'Space Grotesk',sans-serif;
    font-size:13px; font-weight:700;
    letter-spacing:0.08em; text-transform:uppercase;
    color:rgba(255,255,255,0.85);
  }
  .brand em { color:#2563EB; font-style:normal; }
  .content { position:absolute; bottom:52px; left:32px; right:32px; }
  .caption {
    font-family:'Inter',sans-serif; font-size:15px;
    color:rgba(255,255,255,0.85); margin-bottom:8px; line-height:1.4;
  }
  .sub {
    font-family:'Space Grotesk',sans-serif; font-size:10px;
    letter-spacing:0.12em; text-transform:uppercase;
    color:rgba(255,255,255,0.3);
  }
</style>
</head><body>
  <div class="overlay"></div>
  <div class="brand">bla<em>studios</em></div>
  <div class="content">
    <p class="caption">Así quedó todo en funcionamiento. 🍰</p>
    <p class="sub">blastudios · diseño + tecnología</p>
  </div>
</body></html>`;

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
    }, 25000);
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
          catch(e) { if (++n < 15) setTimeout(try_, 400); else reject(e); }
        });
      }).on('error', () => { if (++n < 15) setTimeout(try_, 400); else reject(new Error('Chrome no responde')); });
    };
    try_();
  });
}

function ffmpegRun(args) {
  return new Promise((resolve, reject) => {
    const p = spawn(FFMPEG, args, { stdio: ['ignore', 'ignore', 'pipe'] });
    let err = '';
    p.stderr.on('data', d => err += d.toString());
    p.on('close', code => code === 0 ? resolve() : reject(new Error(`FFmpeg (${code}): ${err.slice(-500)}`)));
  });
}

async function main() {
  console.log('🎬 Añadiendo overlay de texto a historia 7...\n');

  // Guardar HTML temporal
  const htmlTmp = path.join(OUT, '_overlay_s7_tmp.html');
  fs.writeFileSync(htmlTmp, OVERLAY_HTML);

  // Iniciar Chrome
  const chrome = spawn(CHROME, [
    `--remote-debugging-port=${PORT}`,
    '--headless=new', '--disable-gpu', '--no-sandbox',
    '--window-size=400,700',
    'about:blank'
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
  ws.onerror = () => {};
  await new Promise((res, rej) => { ws.onopen = res; setTimeout(() => rej(new Error('WS timeout')), 5000); });

  await send(ws, 'Page.enable');
  await send(ws, 'Runtime.enable');

  const fileUrl = `file:///${htmlTmp.replace(/\\/g, '/')}`;
  await send(ws, 'Page.navigate', { url: fileUrl });
  await sleep(3000); // esperar fuentes Google

  // Capturar PNG transparente a resolución 1080×1919
  const scale = 1080 / 390;
  const shot = await send(ws, 'Page.captureScreenshot', {
    format: 'png',
    omitBackground: true,
    clip: { x: 0, y: 0, width: 390, height: 693, scale }
  });

  const overlayPng = path.join(OUT, '_overlay_s7.png');
  fs.writeFileSync(overlayPng, Buffer.from(shot.data, 'base64'));
  console.log(`✓ Overlay PNG: ${Math.round(fs.statSync(overlayPng).size / 1024)}KB\n`);

  ws.close();
  chrome.kill();
  fs.unlinkSync(htmlTmp);

  // Compositar overlay sobre el video original
  const videoSrc = path.join(__dirname, 'WhatsApp Video 2026-06-03 at 01.15.37.mp4');
  const videoDst = path.join(OUT, 'historia_07_video_local.mp4');

  console.log('🔄 Componiendo video + overlay...');
  await ffmpegRun([
    '-y',
    '-i', videoSrc,
    '-i', overlayPng,
    '-filter_complex',
      '[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30[v];' +
      '[v][1:v]overlay=0:0[out]',
    '-map', '[out]',
    '-map', '0:a?',          // audio si existe
    '-c:v', 'libx264', '-preset', 'slow',
    '-b:v', '3500k', '-minrate', '3500k', '-maxrate', '3500k', '-bufsize', '3500k',
    '-c:a', 'aac', '-b:a', '128k',
    '-pix_fmt', 'yuv420p',
    '-movflags', '+faststart',
    '-t', '15',
    videoDst
  ]);

  fs.unlinkSync(overlayPng);
  const kb = Math.round(fs.statSync(videoDst).size / 1024);
  console.log(`✅ historia_07_video_local.mp4  (${kb}KB)`);
  process.exit(0);
}

main().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
