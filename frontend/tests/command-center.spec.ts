import { test, expect } from '@playwright/test'

test.beforeEach(async ({ request }) => {
  await request.post('/api/v1/state/reset', { data: { seed: 42 } })
})

test('operator runs stress, compares real plans, approves once and sees updated state', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Command center', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Run stress test', exact: true }).click()
  await expect(page.getByText('Stress applied to a fresh synthetic ward.', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'Find minimum intervention', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Approve & simulate' })).toBeVisible()
  await expect(page.locator('.plan-card')).toHaveCount(2)
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: '../artifacts/command-center-ready.png', fullPage: true })
  await page.getByRole('button', { name: 'Approve & simulate' }).click()
  await expect(page.getByText('Approved and simulated', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Approve & simulate' })).toHaveCount(0)
  await expect(page.getByText('Outcome recorded. Ward state updated.')).toBeVisible()
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: '../artifacts/command-center-approved.png', fullPage: true })
  expect(errors).toEqual([])
})

test('zero traffic budget produces explicit safe failure and no approval button', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Run stress test', exact: true }).click()
  await expect(page.getByText('Stress applied to a fresh synthetic ward.', { exact: false })).toBeVisible()
  await page.getByRole('spinbutton', { name: 'Traffic delay increase', exact: true }).fill('0')
  await page.getByRole('button', { name: 'Find minimum intervention', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'NO SAFE ACTION FOUND' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Approve & simulate' })).toHaveCount(0)
  await page.screenshot({ path: '../artifacts/command-center-no-safe.png', fullPage: true })
})

test('mobile layout stays inside viewport and exposes stress controls', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Command center', exact: true })).toBeVisible()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)
  expect(overflow).toBe(false)
  await page.getByRole('button', { name: 'Run stress test', exact: true }).scrollIntoViewIfNeeded()
  await expect(page.getByRole('button', { name: 'Run stress test', exact: true })).toBeVisible()
  await page.screenshot({ path: '../artifacts/command-center-mobile.png', fullPage: true })
})

test('ingested zone names render as text rather than executable map markup', async ({ page, request }) => {
  const response = await request.get('/api/v1/state/current')
  const { state } = await response.json()
  state.zones[0].name = '<img src=x onerror="window.mapInjected=true">'
  await request.post('/api/v1/state/ingest', { data: state })
  await page.goto('/')
  await expect(page.locator('.map-node').first()).toBeVisible()
  expect(await page.evaluate(() => (window as unknown as { mapInjected?: boolean }).mapInjected)).toBeUndefined()
})
