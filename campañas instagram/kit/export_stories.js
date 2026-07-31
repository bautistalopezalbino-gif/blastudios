// Exporta las 5 stories del kit a PNG 1080x1920
// Uso: node "campañas instagram/kit/export_stories.js"
const p = require('puppeteer-core');
const path = require('path');
const dir = __dirname;
(async () => {
  const b = await p.launch({
    executablePath: process.env.CHROME_PATH || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });
  const pg = await b.newPage();
  await pg.setViewport({ width: 1240, height: 2000 });
  await pg.goto('file://' + path.join(dir, 'stories_kit.html'), { waitUntil: 'networkidle0' });
  await pg.evaluate(() => document.fonts.ready);
  const names = ['01-gancho', '02-producto', '03-calendario', '04-prompts', '05-precio'];
  for (let i = 0; i < names.length; i++) {
    const el = await pg.$('#s' + (i + 1));
    await el.screenshot({ path: path.join(dir, names[i] + '.png') });
    console.log('->', names[i] + '.png');
  }
  await b.close();
})();
