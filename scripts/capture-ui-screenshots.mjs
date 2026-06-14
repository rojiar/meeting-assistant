#!/usr/bin/env node
/**
 * Capture UI screenshots for docs (requires frontend + backend running locally).
 * Usage: ./scripts/capture-ui-screenshots.sh
 */
import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = join(ROOT, 'docs', 'screenshots');
const FRONTEND_URL = process.env.FRONTEND_URL ?? 'http://localhost:4321';
const BACKEND_URL = process.env.BACKEND_URL ?? 'http://127.0.0.1:8000';

const { chromium } = await import(
  pathToFileURL(join(ROOT, 'docs', 'node_modules', 'playwright', 'index.mjs')).href
);

async function fetchMeetingId() {
  if (process.env.SCREENSHOT_MEETING_ID) {
    return process.env.SCREENSHOT_MEETING_ID;
  }
  const res = await fetch(`${BACKEND_URL}/api/meetings`);
  if (!res.ok) {
    throw new Error(`Backend ${BACKEND_URL} returned ${res.status}`);
  }
  const meetings = await res.json();
  if (!meetings.length) {
    throw new Error('No meetings in database — process a sample meeting first.');
  }
  return meetings[0].id;
}

async function capture(page, name, options = {}) {
  const path = join(OUT, `${name}.png`);
  await page.screenshot({ path, fullPage: true, ...options });
  console.log(`  ✓ ${name}.png`);
  return name;
}

async function main() {
  const meetingId = await fetchMeetingId();
  await mkdir(OUT, { recursive: true });

  console.log(`Frontend: ${FRONTEND_URL}`);
  console.log(`Meeting:  ${meetingId}`);

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1280, height: 900 },
    deviceScaleFactor: 1,
  });

  const captured = [];

  await page.goto(`${FRONTEND_URL}/`, { waitUntil: 'networkidle' });
  await page.waitForSelector('.meeting-card', { timeout: 20_000 });
  captured.push(await capture(page, 'home'));

  await page.goto(`${FRONTEND_URL}/meeting/${meetingId}`, {
    waitUntil: 'networkidle',
  });
  await page.waitForSelector('.meeting-header h1', { timeout: 15_000 });
  captured.push(await capture(page, 'meeting-summary'));

  await page.click('[data-tab="tasks"]');
  await page.waitForSelector('#panel-tasks:not(.hidden)', { timeout: 5000 });
  captured.push(await capture(page, 'meeting-tasks'));

  await page.click('[data-tab="rag"]');
  await page.waitForSelector('#panel-rag:not(.hidden)', { timeout: 5000 });
  captured.push(await capture(page, 'meeting-rag'));

  await page.goto(`${FRONTEND_URL}/tasks`, { waitUntil: 'networkidle' });
  await page.waitForSelector('.task-table, #tasks-table-wrap p', {
    timeout: 15_000,
  });
  captured.push(await capture(page, 'tasks'));

  await page.goto(`${FRONTEND_URL}/settings`, { waitUntil: 'networkidle' });
  await page.waitForSelector('#health', { timeout: 15_000 });
  await page.waitForFunction(
    () => document.querySelector('#health')?.textContent?.trim().length > 0,
    { timeout: 15_000 }
  );
  captured.push(await capture(page, 'settings'));

  await browser.close();

  const manifest = {
    captured_at: new Date().toISOString(),
    frontend_url: FRONTEND_URL,
    meeting_id: meetingId,
    files: captured.map((name) => ({
      file: `${name}.png`,
      path: `screenshots/${name}.png`,
    })),
  };
  await writeFile(
    join(OUT, 'manifest.json'),
    `${JSON.stringify(manifest, null, 2)}\n`,
    'utf8'
  );
  console.log(`\nSaved ${captured.length} screenshots → docs/screenshots/`);
}

main().catch((err) => {
  console.error(err.message ?? err);
  process.exit(1);
});
