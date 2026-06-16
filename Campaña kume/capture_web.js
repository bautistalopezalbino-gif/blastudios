const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const outDir = __dirname;
  const browser = await chromium.launch();
  const page = await browser.newPage();

  await page.setViewportSize({ width: 1440, height: 900 });
  console.log('Navegando a kumepasteleria.com...');
  await page.goto('https://kumepasteleria.com', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2000);

  // Full-page screenshot
  const fullPath = path.join(outDir, 'kume_fullpage.png');
  await page.screenshot({ path: fullPath, fullPage: true });
  console.log('Screenshot completo guardado:', fullPath);

  await browser.close();
  console.log('Listo. Ahora ejecuta split_chunks.py para dividirlo en 3 chunks.');
})();
