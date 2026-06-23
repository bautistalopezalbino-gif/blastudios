const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');

// Use a system/Playwright chromium if Chrome isn't installed (e.g. on Linux / CI).
const CHROME =
  process.env.CHROME_PATH ||
  [
    '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
    '/usr/bin/google-chrome',
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  ].find(p => { try { return fs.existsSync(p); } catch { return false; } });

const HTML_FILE = path.resolve(__dirname, '12-pagina-web.html');
const OUTPUT_DIR = __dirname;

const SLIDE_NAMES = [
  '12-00-portada',
  '12-01-mas-clientes',
  '12-02-mas-visibilidad',
  '12-03-mas-ventas',
  '12-04-que-incluye',
  '12-05-cta-cierre',
];

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  const page = await browser.newPage();
  // 2x device scale -> exports each 540×675 preview as full 1080×1350 PNG.
  await page.setViewport({ width: 600, height: 800, deviceScaleFactor: 2 });
  await page.goto(`file://${HTML_FILE}`, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 2000)); // let Google Fonts settle

  const slides = await page.$$('.slide');
  console.log(`Found ${slides.length} slides`);

  for (let i = 0; i < slides.length; i++) {
    const name = SLIDE_NAMES[i] || `12-slide-${String(i).padStart(2, '0')}`;
    const outPath = path.join(OUTPUT_DIR, `${name}.png`);
    await slides[i].screenshot({ path: outPath });
    console.log(`✓ ${name}.png`);
  }

  await browser.close();
  console.log('\nDone! All PNGs saved.');
})();
