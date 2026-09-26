import { defineConfig } from '@playwright/test'
import { existsSync } from 'node:fs'
import { resolve } from 'node:path'

const venvPython = resolve('..', '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')
const python = existsSync(venvPython) ? `"${venvPython}"` : 'python'
const externalUrl = process.env.URBANNEXUS_E2E_URL
export default defineConfig({
  testDir: './tests', workers: 1, timeout: 60000,
  use: { baseURL: externalUrl ?? 'http://127.0.0.1:8010', viewport: { width: 1440, height: 1080 }, trace: 'retain-on-failure' },
  outputDir: '../artifacts/playwright',
  webServer: externalUrl ? undefined : { command: `${python} ../scripts/serve_test.py`, url: 'http://127.0.0.1:8010/health', reuseExistingServer: false, timeout: 30000 },
})
