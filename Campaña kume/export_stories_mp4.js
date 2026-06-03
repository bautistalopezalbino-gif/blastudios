// Exporta las 9 historias como MP4 1080×1920px listos para Instagram Stories
const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const FFMPEG = 'C:\\Users\\EMILIANO JAVIER LOPE\\AppData\\Local\\Microsoft\\WinGet\\Packages\\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\\ffmpeg-8.1.1-full_build\\bin\\ffmpeg.exe';
const PORT   = 9229;
const HTML   = path.join(__dirname, 'stories_kume.html').replace(/\\/g, '/');
const OUT    = __dirname;
const TMP    = path.join(__dirname, '_frames_tmp');

// Duración de cada historia en segundos
const STORIES = [
  { i: 1, name: '01_hook',              dur: 5  },
  { i: 2, name: '02_presentacion_kume', dur: 6  },
  { i: 3, name: '03_el_reto',           dur: 6  },
  { i: 4, name: '04_pagina_web',        dur: 10 }, // animación scroll 9s
  { i: 5, name: '05_banner_exterior',   dur: 6  },
  { i: 6, name: '06_menu_digital',      dur: 7  },
  // Historia 7 = video original, se procesa aparte
  { i: 8, name: '08_resultados',        dur: 6  },
  { i: 9, name: '09_cta_hablemos',      dur: 8  },
];

const FPS = 10; // CDP puede capturar ~8-12fps reales

const sleep  = ms => new Promise(r => setTimeout(r, ms));
const pending = new Map();
let msgId = 1;

function send(ws, method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = msgId++;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
    setTimeout(() => {
      if (pending.has(id)) { pending.delete(id); reject(new Error(`Timeout: ${method}`)); }
    }, 30000);
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
    p.on('close', code => code === 0 ? resolve() : reject(new Error(`FFmpeg error (${code}): ${err.slice(-300)}`)));
  });
}

async function main() {
  console.log('🎬 Exportando historias como MP4...\n');

  // Limpiar carpeta temporal
  if (fs.existsSync(TMP)) fs.rmSync(TMP, { recursive: true });
  fs.mkdirSync(TMP);

  // Iniciar Chrome headless
  const chrome = spawn(CHROME, [
    `--remote-debugging-port=${PORT}`,
    '--headless=new', '--disable-gpu', '--no-sandbox',
    '--disable-web-security', '--allow-file-access-from-files',
    '--window-size=1200,900',
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

  console.log('📂 Cargando stories_kume.html...');
  await send(ws, 'Page.navigate', { url: `file:///${HTML}` });
  await sleep(2500);

  // Ocultar elementos de navegación
  await send(ws, 'Runtime.evaluate', {
    expression: `
      document.querySelector('.page-header') && (document.querySelector('.page-header').style.display='none');
      document.querySelector('.story-counter') && (document.querySelector('.story-counter').style.display='none');
      document.querySelector('.instructions') && (document.querySelector('.instructions').style.display='none');
      document.querySelector('.progress-bar') && (document.querySelector('.progress-bar').style.display='none');
      document.querySelectorAll('.nav-btn').forEach(b => b.style.display='none');
      document.body.style.padding = '0';
      document.body.style.gap = '0';
      document.body.style.background = '#000';
      document.body.style.justifyContent = 'flex-start';
    `
  });
  await sleep(300);

  // Dimensiones del viewer
  const rectResult = await send(ws, 'Runtime.evaluate', {
    expression: `JSON.stringify(document.getElementById('viewer').getBoundingClientRect())`,
    returnByValue: true
  });
  const rect = JSON.parse(rectResult.result.value);
  const scale = 1080 / rect.width;
  console.log(`📐 Viewer: ${Math.round(rect.width)}×${Math.round(rect.height)}px · escala: ${scale.toFixed(3)}\n`);

  const frameInterval = Math.round(1000 / FPS);

  for (const story of STORIES) {
    const { i, name, dur } = story;

    // Navegar a la historia
    await send(ws, 'Runtime.evaluate', { expression: `cur = ${i}; updateUI(); void 0;` });
    await sleep(700); // esperar carga inicial de animaciones

    const storyDir = path.join(TMP, `s${i}`);
    fs.mkdirSync(storyDir);

    const frameCount = Math.ceil(dur * FPS);
    console.log(`🎞  Historia ${i} · ${name}  (${dur}s · ~${frameCount} frames)`);

    const t0 = Date.now();
    for (let f = 0; f < frameCount; f++) {
      const shot = await send(ws, 'Page.captureScreenshot', {
        format: 'jpeg',
        quality: 90,
        clip: { x: rect.x, y: rect.y, width: rect.width, height: rect.height, scale }
      });
      fs.writeFileSync(
        path.join(storyDir, `f${String(f).padStart(5, '0')}.jpg`),
        Buffer.from(shot.data, 'base64')
      );

      // Sincronizar al FPS objetivo (si la captura fue rápida, esperar el resto)
      const elapsed = Date.now() - t0;
      const target  = (f + 1) * frameInterval;
      if (target - elapsed > 5) await sleep(target - elapsed);
    }

    const realDur   = (Date.now() - t0) / 1000;
    const realFps   = frameCount / realDur;
    console.log(`   ✓ ${frameCount} frames en ${realDur.toFixed(1)}s (${realFps.toFixed(1)}fps reales)`);

    // Convertir frames → MP4 con FFmpeg
    const outFile = path.join(OUT, `historia_${name}.mp4`);
    process.stdout.write('   🔄 Convirtiendo a MP4...');

    await ffmpegRun([
      '-y',
      '-framerate', String(realFps.toFixed(3)),
      '-i', path.join(storyDir, 'f%05d.jpg'),
      '-vf', [
        `scale=1080:1920:force_original_aspect_ratio=decrease`,
        `pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black`,
        'fps=30'                              // salida suave a 30fps
      ].join(','),
      '-c:v', 'libx264',
      '-preset', 'fast',
      '-crf', '20',
      '-pix_fmt', 'yuv420p',
      '-movflags', '+faststart',
      outFile
    ]);

    const kb = Math.round(fs.statSync(outFile).size / 1024);
    console.log(` ✅ historia_${name}.mp4 (${kb}KB)\n`);
  }

  ws.close();
  chrome.kill();

  // ── Historia 7: procesar el video original ──────────────────────────────────
  console.log('🎬 Historia 7 — formateando video original a 1080×1920...');
  const videoSrc = path.join(__dirname, 'WhatsApp Video 2026-06-03 at 01.15.37.mp4');
  const videoDst = path.join(OUT, 'historia_07_video_local.mp4');

  if (fs.existsSync(videoSrc)) {
    await ffmpegRun([
      '-y',
      '-i', videoSrc,
      '-vf', [
        'scale=1080:1920:force_original_aspect_ratio=increase',
        'crop=1080:1920',
        'fps=30'
      ].join(','),
      '-c:v', 'libx264',
      '-preset', 'fast',
      '-crf', '20',
      '-c:a', 'aac', '-b:a', '128k',
      '-pix_fmt', 'yuv420p',
      '-movflags', '+faststart',
      '-t', '15',   // máx 15s para Instagram Stories
      videoDst
    ]);
    const kb = Math.round(fs.statSync(videoDst).size / 1024);
    console.log(`✅ historia_07_video_local.mp4 (${kb}KB)\n`);
  } else {
    console.log(`⚠️  No encontrado: ${path.basename(videoSrc)}`);
    console.log(`   Colócalo en la carpeta "Campaña kume/" y vuelve a ejecutar.\n`);
  }

  // Limpiar frames temporales
  fs.rmSync(TMP, { recursive: true });

  console.log('🎉 ¡Exportación completa! Archivos MP4 en: Campaña kume/');
  console.log('\n📋 Para subir a Instagram Stories:');
  console.log('   historia_01_hook.mp4 → historia_06_menu_digital.mp4  (en orden)');
  console.log('   historia_07_video_local.mp4                           (video del local)');
  console.log('   historia_08_resultados.mp4 → historia_09_cta_hablemos.mp4');
  process.exit(0);
}

main().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
