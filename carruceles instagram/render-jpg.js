const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const path = require('path');

const HTML_FILE = path.resolve(__dirname, '10-skills-claude-code-webdev.html');
const OUTPUT_DIR = path.resolve(__dirname, 'jpg');

const SLIDE_NAMES = [
  '00-portada',
  '01-superpowers',
  '02-frontend-design',
  '03-karpathy-behavioural',
  '04-uiux-pro-max',
  '05-firecrawl',
  '06-vercel-guidelines',
  '07-spartan-toolkit',
  '08-artifacts-builder',
  '09-claude-md',
  '10-code-simplifier',
  '11-cta-cierre',
];

(async () => {
  const fs = require('fs');
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  const browser = await chromium.launch({ args: ['--no-sandbox', '--disable-setuid-sandbox'] });
  const page = await browser.newPage({ deviceScaleFactor: 2 });
  await page.setViewportSize({ width: 600, height: 800 });

  await page.goto('file://' + HTML_FILE, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500); // fonts

  const slides = await page.$$('.slide');
  console.log(`Found ${slides.length} slides`);

  for (let i = 0; i < slides.length; i++) {
    const name = SLIDE_NAMES[i] || `slide-${String(i).padStart(2, '0')}`;
    const outPath = path.join(OUTPUT_DIR, `${name}.jpg`);
    await slides[i].screenshot({ path: outPath, type: 'jpeg', quality: 92 });
    console.log(`OK ${name}.jpg`);
  }

  await browser.close();
  console.log('Done. JPGs in /jpg');
})();
