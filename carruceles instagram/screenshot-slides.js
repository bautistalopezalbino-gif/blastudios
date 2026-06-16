const puppeteer = require('puppeteer-core');
const path = require('path');

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const HTML_FILE = path.resolve(__dirname, '10-skills-claude-design.html');
const OUTPUT_DIR = __dirname;

const SLIDE_NAMES = [
  '00-portada',
  '01-skill-contexto-visual',
  '02-skill-referencias',
  '03-skill-colores-hex',
  '04-skill-tipografia',
  '05-skill-dimensiones',
  '06-skill-iteracion',
  '07-skill-roleplay',
  '08-skill-feedback',
  '09-skill-variaciones',
  '10-skill-codigo',
  '11-cta-cierre',
];

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  const page = await browser.newPage();

  // Viewport: slide preview width + some body padding, at 2x for full 1080×1350 output
  await page.setViewport({ width: 600, height: 800, deviceScaleFactor: 2 });

  await page.goto(`file:///${HTML_FILE.replace(/\\/g, '/')}`, { waitUntil: 'networkidle0' });

  // Wait for Google Fonts to load
  await new Promise(r => setTimeout(r, 2000));

  const slides = await page.$$('.slide');
  console.log(`Found ${slides.length} slides`);

  for (let i = 0; i < slides.length; i++) {
    const name = SLIDE_NAMES[i] || `slide-${String(i).padStart(2, '0')}`;
    const outPath = path.join(OUTPUT_DIR, `${name}.png`);
    await slides[i].screenshot({ path: outPath });
    console.log(`✓ ${name}.png`);
  }

  await browser.close();
  console.log('\nDone! All PNGs saved.');
})();
