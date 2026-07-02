const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');

const CHROME =
  process.env.CHROME_PATH ||
  [
    '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
    '/usr/bin/google-chrome',
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  ].find(p => { try { return fs.existsSync(p); } catch { return false; } });

const HTML_FILE = path.resolve(__dirname, '13-stories-nuevo-mes.html');
const OUTPUT_DIR = __dirname;

const NAMES = [
  '13-story-01-gancho',
  '13-story-02-problema',
  '13-story-03-servicios',
  '13-story-04-diferenciador',
  '13-story-05-cta',
];

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  const page = await browser.newPage();
  // .story is 360×640; deviceScaleFactor 3 -> full 1080×1920 (9:16) PNG.
  await page.setViewport({ width: 420, height: 720, deviceScaleFactor: 3 });
  await page.goto(`file://${HTML_FILE}`, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 2000));

  const stories = await page.$$('.story');
  console.log(`Found ${stories.length} stories`);

  for (let i = 0; i < stories.length; i++) {
    const name = NAMES[i] || `13-story-${String(i).padStart(2, '0')}`;
    const outPath = path.join(OUTPUT_DIR, `${name}.png`);
    await stories[i].screenshot({ path: outPath });
    console.log(`✓ ${name}.png`);
  }

  await browser.close();
  console.log('\nDone! All story PNGs saved.');
})();
