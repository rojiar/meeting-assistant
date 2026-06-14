import { pathToFileURL, fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const DOCS = '/home/arvinzaheri/project/docs';

const { chromium } = await import(
  pathToFileURL(join(DOCS, 'node_modules', 'playwright', 'index.mjs')).href
);

const htmlPath = join(HERE, 'acoustic-scene-classification-slides.html');
const outPath  = join(HERE, 'acoustic-scene-classification.pdf');

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  await page.goto(pathToFileURL(htmlPath).href, { waitUntil: 'load', timeout: 120000 });
  await page.emulateMedia({ media: 'print' });
  await page.pdf({
    path: outPath,
    printBackground: true,
    preferCSSPageSize: true,
    margin: { top: '0', bottom: '0', left: '0', right: '0' },
  });
  console.log('PDF ->', outPath);
} finally {
  await browser.close();
}
