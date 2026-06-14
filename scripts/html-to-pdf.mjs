#!/usr/bin/env node
/**
 * Convert docs/*.html to PDF via Playwright (Chromium).
 * Persian RTL + Vazirmatn + embedded SVG diagrams.
 */
import { createServer } from 'node:http';
import { mkdirSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { extname, join } from 'node:path';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { pathToFileURL } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const DOCS = join(ROOT, 'docs');
const PDF_DIR = join(DOCS, 'pdf');
const MANIFEST_PATH = join(DOCS, 'diagrams', 'manifest.json');

const { chromium } = await import(
  pathToFileURL(join(DOCS, 'node_modules', 'playwright', 'index.mjs')).href
);

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.css': 'text/css',
  '.json': 'application/json',
  '.woff2': 'font/woff2',
  '.woff': 'font/woff',
};

function startStaticServer(port) {
  return new Promise((resolve) => {
    const server = createServer((req, res) => {
      const raw = decodeURIComponent((req.url || '/').split('?')[0]);
      const rel = raw === '/' ? 'index.html' : raw.replace(/^\//, '');
      const filePath = join(DOCS, rel);

      try {
        if (!statSync(filePath).isFile()) {
          res.writeHead(404);
          res.end('Not found');
          return;
        }
      } catch {
        res.writeHead(404);
        res.end('Not found');
        return;
      }

      const body = readFileSync(filePath);
      res.writeHead(200, {
        'Content-Type': MIME[extname(filePath)] || 'application/octet-stream',
      });
      res.end(body);
    });
    server.listen(port, '127.0.0.1', () => resolve(server));
  });
}

const PRINT_CSS = `
  @page { size: A4; margin: 14mm 12mm; }
  html, body {
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  .mermaid-wrap pre.mermaid { display: none !important; }
  img.diagram-svg {
    display: block;
    width: 100%;
    max-width: 100%;
    height: auto;
    margin: 0.5rem 0;
  }
  a { color: #2563eb; text-decoration: none; }
  .site-header, .no-print { display: none !important; }
`;

async function htmlToPdf(page, htmlFile, diagramPaths, outPath, port) {
  const url = `http://127.0.0.1:${port}/${encodeURIComponent(htmlFile)}`;
  await page.goto(url, { waitUntil: 'networkidle', timeout: 120_000 });

  await page.addStyleTag({ content: PRINT_CSS });

  await page.evaluate((paths) => {
    const pres = document.querySelectorAll('pre.mermaid');
    pres.forEach((pre, i) => {
      const src = paths[i];
      if (!src) return;
      const img = document.createElement('img');
      img.className = 'diagram-svg';
      img.alt = 'diagram';
      img.src = src;
      pre.replaceWith(img);
    });
  }, diagramPaths);

  if (diagramPaths.length) {
    await page.waitForFunction(
      () => {
        const imgs = document.querySelectorAll('img.diagram-svg');
        return imgs.length === 0 || [...imgs].every((img) => img.complete && img.naturalWidth > 0);
      },
      { timeout: 30_000 }
    );
  }

  await page.emulateMedia({ media: 'print' });

  await page.pdf({
    path: outPath,
    format: 'A4',
    printBackground: true,
    preferCSSPageSize: true,
    margin: { top: '14mm', bottom: '14mm', left: '12mm', right: '12mm' },
  });

  console.log(`PDF → ${outPath}`);
}

const PORT = 8765;
mkdirSync(PDF_DIR, { recursive: true });

const manifest = JSON.parse(
  readFileSync(MANIFEST_PATH, 'utf8')
);

function collectHtmlFiles() {
  const files = [];
  for (const name of readdirSync(DOCS)) {
    if (name.startsWith('_') || name.startsWith('.')) continue;
    const full = join(DOCS, name);
    if (name.endsWith('.html') && statSync(full).isFile()) {
      files.push(name);
    }
    if (name === 'en' && statSync(full).isDirectory()) {
      for (const enName of readdirSync(full)) {
        if (!enName.endsWith('.html') || enName.startsWith('_')) continue;
        files.push(`en/${enName}`);
      }
    }
  }
  return files;
}

const htmlFiles = collectHtmlFiles();

const server = await startStaticServer(PORT);
const browser = await chromium.launch({ headless: true });

try {
  const page = await browser.newPage();
  for (const file of htmlFiles) {
    const pdfName = file.replace(/\.html$/i, '.pdf');
    const pdfDir = file.startsWith('en/') ? join(PDF_DIR, 'en') : PDF_DIR;
    mkdirSync(pdfDir, { recursive: true });
    await htmlToPdf(
      page,
      file,
      manifest[file] || [],
      join(pdfDir, pdfName.replace(/^en\//, '')),
      PORT
    );
  }
} finally {
  await browser.close();
  server.close();
}

console.log(`Done: ${htmlFiles.length} PDF(s) → docs/pdf/ (+ docs/pdf/en/)`);
