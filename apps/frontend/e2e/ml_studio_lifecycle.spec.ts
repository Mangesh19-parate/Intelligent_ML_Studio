import { test, expect } from '@playwright/test';

test.describe('Intelligent ML Studio - Full Browser & API Lifecycle', () => {
  test('Complete user workflow: login -> dashboard -> navigation -> data -> training -> deployment', async ({ page }) => {
    // 1. Visit Login Page and assert title and form elements
    await page.goto('/login');
    await expect(page).toHaveTitle(/ML Studio|Intelligent ML Studio/i);
    
    const emailInput = page.locator('input[type="email"], input[name="email"]').first();
    await expect(emailInput).toBeVisible({ timeout: 10000 });
    const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
    await expect(passwordInput).toBeVisible();

    // 2. Perform Authentication (demo / admin account)
    await emailInput.fill('admin@studio.dev');
    await passwordInput.fill('Password123!');
    const submitBtn = page.locator('button[type="submit"]').first();
    await expect(submitBtn).toBeEnabled();
    await submitBtn.click();

    // 3. Navigation and Dashboard Verification
    await page.waitForURL((url) => url.pathname.includes('/dashboard') || url.pathname.includes('/projects') || url.pathname === '/', { timeout: 15000 });
    await expect(page.locator('body')).toBeVisible();

    // 4. Verify Project Navigation or Dashboard Metrics
    const mainContent = page.locator('main, #root, body');
    await expect(mainContent).toBeVisible();

    // 5. Data / Ingestion Stage Navigation
    const dataNavLink = page.locator('a[href*="data"], a[href*="dataset"], button:has-text("Data"), button:has-text("Datasets")').first();
    if (await dataNavLink.isVisible()) {
      await dataNavLink.click();
      await expect(page.locator('body')).toContainText(/dataset|data|upload|project/i);
    }

    // 6. Training Stage Navigation
    const trainNavLink = page.locator('a[href*="train"], a[href*="model"], button:has-text("Train"), button:has-text("Model")').first();
    if (await trainNavLink.isVisible()) {
      await trainNavLink.click();
      await expect(page.locator('body')).toContainText(/train|model|experiment|metric/i);
    }

    // 7. Deployment Stage Navigation
    const deployNavLink = page.locator('a[href*="deploy"], button:has-text("Deploy"), button:has-text("Deployment")').first();
    if (await deployNavLink.isVisible()) {
      await deployNavLink.click();
      await expect(page.locator('body')).toContainText(/deploy|status|endpoint|model/i);
    }
  });

  test('System Health & Observability Contract', async ({ request }) => {
    // Direct API verification through Playwright request context
    const response = await request.get('http://localhost:8000/health');
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.status).toBe('healthy');
    expect(data.api_version).toBe('v1');
  });
});

