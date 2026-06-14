#!/usr/bin/env node
/**
 * Extract Mermaid blocks from docs HTML and render to SVG.
 * Processes Persian docs/*.html and English docs/en/*.html.
 */
import { execFileSync } from 'node:child_process';
import { mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const DOCS = join(ROOT, 'docs');
const DIAGRAMS = join(DOCS, 'diagrams');
const MERMAID_RE = /<pre class="mermaid">\s*([\s\S]*?)<\/pre>/g;

function slugify(relPath) {
  return relPath
    .replace(/\.html$/i, '')
    .replace(/[/\\]/g, '-')
    .replace(/[^\w\u0600-\u06FF-]+/g, '-')
    .replace(/-+/g, '-');
}

function mmdcBin() {
  return join(DOCS, 'node_modules', '.bin', 'mmdc');
}

function collectHtmlFiles() {
  const files = [];
  for (const name of readdirSync(DOCS)) {
    if (name.startsWith('_') || name.startsWith('.')) continue;
    const full = join(DOCS, name);
    if (name.endsWith('.html') && statSync(full).isFile()) {
      files.push({ rel: name, full });
    }
    if (name === 'en' && statSync(full).isDirectory()) {
      for (const enName of readdirSync(full)) {
        if (!enName.endsWith('.html') || enName.startsWith('_')) continue;
        files.push({ rel: `en/${enName}`, full: join(full, enName) });
      }
    }
  }
  return files;
}

mkdirSync(DIAGRAMS, { recursive: true });

let total = 0;
const manifest = {};

for (const { rel, full } of collectHtmlFiles()) {
  const content = readFileSync(full, 'utf8');
  const slug = slugify(rel);
  const diagrams = [];
  let match;
  let idx = 0;
  MERMAID_RE.lastIndex = 0;

  while ((match = MERMAID_RE.exec(content)) !== null) {
    const mmdPath = join(DIAGRAMS, `${slug}-${idx}.mmd`);
    const svgPath = join(DIAGRAMS, `${slug}-${idx}.svg`);
    const mermaidSource = match[1].trim();
    writeFileSync(mmdPath, mermaidSource, 'utf8');

    console.log(`Rendering ${slug}-${idx}.svg …`);
    execFileSync(
      mmdcBin(),
      ['-i', mmdPath, '-o', svgPath, '-b', 'white', '-t', 'neutral', '--scale', '2'],
      { stdio: 'inherit', cwd: DOCS }
    );

    diagrams.push(`diagrams/${slug}-${idx}.svg`);
    idx += 1;
    total += 1;
  }

  if (diagrams.length === 0) {
    console.log(`No diagrams in ${rel}`);
  }
  manifest[rel] = diagrams;
}

writeFileSync(
  join(DIAGRAMS, 'manifest.json'),
  JSON.stringify(manifest, null, 2),
  'utf8'
);

console.log(`Done: ${total} diagram(s) → docs/diagrams/`);
