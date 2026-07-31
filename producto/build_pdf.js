// Genera el PDF del producto a partir de kit_30dias.html
// Uso: node producto/build_pdf.js
const puppeteer = require('puppeteer-core');
const path = require('path');

const SRC = path.join(__dirname, 'kit_30dias.html');
const OUT = path.join(__dirname, 'kit-blastudios-30dias.pdf');

(async () => {
  const browser = await puppeteer.launch({
    executablePath: process.env.CHROME_PATH || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });
  const page = await browser.newPage();
  await page.goto('file://' + SRC, { waitUntil: 'networkidle0' });
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({
    path: OUT,
    format: 'A4',
    printBackground: true,
    margin: { top: 0, right: 0, bottom: 0, left: 0 },
  });
  await browser.close();
  console.log('PDF generado:', OUT);
})();
