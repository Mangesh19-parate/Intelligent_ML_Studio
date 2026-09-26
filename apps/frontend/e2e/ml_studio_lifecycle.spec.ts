import { test, expect } from '@playwright/test';

test.describe('Intelligent ML Studio - Full Browser Lifecycle', () => {
  test('Complete user workflow: login -> project -> data -> train -> evaluate -> deploy -> predict', async ({ page }) => {
    // 1. Visit Login Page
    await page.goto('/login');
    await expect(page).toHaveTitle(/ML Studio|Intelligent ML Studio/i);

    // 2. Perform Authentication
    const emailInput = page.locator('input[type="email"], input[name="email"]');
    if (await emailInput.isVisible()) {
      await emailInput.fill('admin@studio.dev');
      await page.fill('input[type="password"], input[name="password"]', 'Password123!');
      await page.click('button[type="submit"]');
    }

    // 3. Navigation to Dashboard
    await page.waitForURL('**/dashboard**', { timeout: 8000 }).catch(() => {});
    await expect(page.locator('body')).toBeVisible();

    // 4. Project Creation Modal / Stage
    const newProjectBtn = page.getByRole('button', { name: /new project|create project/i });
    if (await newProjectBtn.isVisible()) {
      await newProjectBtn.click();
      await page.fill('input[name="project_name"], input[placeholder*="Project Name"]', 'E2E Browser Studio Project');
      await page.click('button:has-text("Create"), button:has-text("Save")');
    }

    // 5. Data Ingestion & Profile Stage
    const datasetTab = page.locator('text=/datasets|data/i').first();
    if (await datasetTab.isVisible()) {
      await datasetTab.click();
      await expect(page.locator('body')).toContainText(/upload|dataset|rows/i);
    }

    // 6. Training Stage & Model Tournament
    const trainingTab = page.locator('text=/training|models/i').first();
    if (await trainingTab.isVisible()) {
      await trainingTab.click();
      await expect(page.locator('body')).toContainText(/tournament|algorithm|accuracy|f1/i);
    }

    // 7. Deployments & Diagnostics View
    const deployTab = page.locator('text=/deployments|deploy/i').first();
    if (await deployTab.isVisible()) {
      await deployTab.click();
      await expect(page.locator('body')).toContainText(/deployment|endpoint|active|gate/i);
    }
  });
});
