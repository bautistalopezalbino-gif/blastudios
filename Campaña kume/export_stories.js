// Exporta las 9 historias del HTML como PNG 1080×1920px listos para Instagram
const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const PORT = 9226;
const HTML = path.join(__dirname, 'stories_kume.html').replace(/\\/g, '/');
const OUT = __dirname;

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
          catch(e) { if(++n<15) setTimeout(try_,400); else reject(e); }
        });
      }).on('error', () => { if(++n<15) setTimeout(try_,400); else reject(new Error('Chrome no responde')); });
    };
    try_();
  });
}

async function main() {
  console.log('🚀 Iniciando exportación de historias...\n');

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
  await new Promise((res, rej) => { ws.onopen = res; setTimeout(()=>rej(new Error('WS timeout')),5000); });

  await send(ws, 'Page.enable');
  await send(ws, 'Runtime.enable');

  // Abrir el HTML de las stories
  console.log('📂 Cargando stories_kume.html...');
  await send(ws, 'Page.navigate', { url: `file:///${HTML}` });
  await sleep(2500);

  // Ocultar elementos de UI (header, flechas, contador, instrucciones)
  await send(ws, 'Runtime.evaluate', {
    expression: `
      document.querySelector('.page-header') && (document.querySelector('.page-header').style.display='none');
      document.querySelector('.story-counter') && (document.querySelector('.story-counter').style.display='none');
      document.querySelector('.instructions') && (document.querySelector('.instructions').style.display='none');
      document.querySelectorAll('.nav-btn').forEach(b => b.style.display='none');
      document.body.style.padding = '0';
      document.body.style.gap = '0';
      document.body.style.background = '#000';
      document.body.style.justifyContent = 'flex-start';
    `
  });
  await sleep(300);

  // Obtener posición y dimensiones del viewer
  const rectResult = await send(ws, 'Runtime.evaluate', {
    expression: `JSON.stringify(document.getElementById('viewer').getBoundingClientRect())`,
    returnByValue: true
  });
  const rect = JSON.parse(rectResult.result.value);
  console.log(`📐 Viewer: ${Math.round(rect.width)}×${Math.round(rect.height)}px en (${Math.round(rect.x)}, ${Math.round(rect.y)})\n`);

  // Escala para llegar a 1080×1920px
  const scale = 1080 / rect.width;

  const names = [
    '01_hook',
    '02_presentacion_kume',
    '03_el_reto',
    '04_pagina_web',
    '05_banner_exterior',
    '06_menu_digital',
    '07_video_usa_mp4',   // Story de video → usar el .mp4 directamente
    '08_resultados',
    '09_cta_hablemos'
  ];

  for (let i = 1; i <= 9; i++) {
    // Cambiar a la story i
    await send(ws, 'Runtime.evaluate', {
      expression: `cur = ${i}; updateUI(); void 0;`
    });
    // Esperar renderizado (más tiempo para story 4 con animación y 7 con video)
    await sleep(i === 4 ? 800 : i === 7 ? 800 : 350);

    const fname = `historia_${names[i-1]}.png`;

    if (i === 7) {
      // Story 7 es video — la marcamos con borde pero avisamos
      console.log(`⏭  historia_07_video_usa_mp4.png → Capturando placeholder (sube el .mp4 directamente a Instagram)`);
    }

    const shot = await send(ws, 'Page.captureScreenshot', {
      format: 'png',
      clip: {
        x: rect.x,
        y: rect.y,
        width: rect.width,
        height: rect.height,
        scale: scale
      }
    });

    const fpath = path.join(OUT, fname);
    fs.writeFileSync(fpath, Buffer.from(shot.data, 'base64'));
    const kb = Math.round(fs.statSync(fpath).size / 1024);

    if (i === 7) {
      console.log(`   ↳ Guardado placeholder: ${fname} (${kb}KB)`);
    } else {
      console.log(`✅ ${fname}  (${kb}KB  1080×${Math.round(rect.height * scale)}px)`);
    }
  }

  ws.close();
  chrome.kill();

  console.log('\n🎉 ¡Exportación completa!');
  console.log('📁 Archivos guardados en: Campaña kume/');
  console.log('\n📋 Para subir a Instagram Stories:');
  console.log('   Historias 1-6 y 8-9 → sube los PNG directamente');
  console.log('   Historia 7         → sube el archivo .mp4: "WhatsApp Video 2026-06-03 at 01.15.37.mp4"');
  process.exit(0);
}

main().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
