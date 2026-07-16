const puppeteer = require('/home/user/blastudios/carruceles instagram/node_modules/puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
    headless: 'new',
    args: ['--no-sandbox','--disable-setuid-sandbox']
  });
  const page = await browser.newPage();
  const url = 'file:///home/user/blastudios/marketing/reels_pdf/reels_blastudios.html';
  try {
    await page.goto(url, { waitUntil: 'networkidle0', timeout: 45000 });
  } catch (e) {
    await page.goto(url, { waitUntil: 'load', timeout: 45000 });
  }
  await new Promise(r => setTimeout(r, 1500));
  await page.pdf({
    path: '/home/user/blastudios/marketing/Reels_Blastudios_ideas_y_prompt.pdf',
    format: 'A4', printBackground: true,
    margin: { top: '0', right: '0', bottom: '0', left: '0' }
  });
  await browser.close();
  console.log('PDF OK');
})().catch(e => { console.error(e); process.exit(1); });
