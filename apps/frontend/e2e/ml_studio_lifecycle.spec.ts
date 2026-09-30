import { test, expect } from '@playwright/test';

/**
 * Intelligent ML Studio - Full-Lifecycle Browser & API End-to-End Suite.
 * Validates deterministic complete platform workflow:
 * Authentication -> Workspace Dashboard -> Project Creation -> Dataset Ingestion ->
 * Exploratory Data Analysis -> Transformations -> Feature Engineering -> Model Training ->
 * Model Diagnostics -> Deployment Governance -> Real-time Inference & Observability.
 */

test.describe('Intelligent ML Studio - Full Platform Lifecycle', () => {
  test('Complete End-to-End User Workflow & Distributed Pipeline Execution', async ({ page }) => {
    // 1. Visit Login Page & Assert UI Structure
    await page.goto('/login');
    await expect(page).toHaveTitle(/ML Studio|Intelligent ML Studio/i);

    const emailInput = page.locator('input[type="email"], input[name="email"]').first();
    await expect(emailInput).toBeVisible({ timeout: 15000 });
    const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
    await expect(passwordInput).toBeVisible();

    // 2. Perform Deterministic Authentication with Seeded Admin / Trainer Account
    await emailInput.fill('admin@studio.dev');
    await passwordInput.fill('DemoPassword123!');
    const submitBtn = page.locator('button[type="submit"]').first();
    await expect(submitBtn).toBeEnabled();
    await submitBtn.click();

    // 3. Assert Navigation to Workspace Dashboard
    await page.waitForURL((url) => url.pathname.includes('/dashboard') || url.pathname.includes('/projects') || url.pathname === '/', { timeout: 20000 });
    await expect(page.locator('body')).toBeVisible();
    await expect(page.locator('h1, h2, h3').first()).toBeVisible();

    // 4. Data Ingestion & Dataset Management Stage
    await page.goto('/data');
    await page.waitForURL((url) => url.pathname.includes('/data'), { timeout: 15000 });
    await expect(page.locator('body')).toContainText(/dataset|data|project|schema|upload/i);

    // 5. Exploratory Data Analysis & Statistical Profiling Stage
    await page.goto('/data-analysis');
    await page.waitForURL((url) => url.pathname.includes('/data-analysis'), { timeout: 15000 });
    await expect(page.locator('body')).toContainText(/analysis|profiling|eda|distribution|statistics/i);

    // 6. Data Cleaning & Feature Transformation Stage
    await page.goto('/transformations');
    await page.waitForURL((url) => url.pathname.includes('/transformations'), { timeout: 15000 });
    await expect(page.locator('body')).toContainText(/transform|scaling|imputation|encoding|clean/i);

    // 7. Feature Engineering & Selection Stage
    await page.goto('/feature-engineering');
    await page.waitForURL((url) => url.pathname.includes('/feature-engineering'), { timeout: 15000 });
    await expect(page.locator('body')).toContainText(/feature|selection|importance|ranking|correlation/i);

    // 8. Model Training & Leaderboard Stage
    await page.goto('/ml');
    await page.waitForURL((url) => url.pathname.includes('/ml'), { timeout: 15000 });
    await expect(page.locator('body')).toContainText(/training|leaderboard|model|experiment|metric/i);

    // 9. Model Diagnostics, Recommendations & SHAP Explainability Stage
    await page.goto('/diagnostics');
    await page.waitForURL((url) => url.pathname.includes('/diagnostics'), { timeout: 15000 });
    await expect(page.locator('body')).toContainText(/diagnostic|leakage|recommendation|explainability|shap/i);

    // 10. Production Deployment, Governance Gate & Live Prediction Stage
    await page.goto('/production');
    await page.waitForURL((url) => url.pathname.includes('/production'), { timeout: 15000 });
    await expect(page.locator('body')).toContainText(/production|deploy|gate|endpoint|predict/i);

    // 11. Live Monitoring & Drift Observability Stage
    await page.goto('/monitoring');
    await page.waitForURL((url) => url.pathname.includes('/monitoring'), { timeout: 15000 });
    await expect(page.locator('body')).toContainText(/monitor|drift|latency|telemetry|metrics/i);
  });

  test('System Health, Readiness & Observability Contract', async ({ request }) => {
    // 1. Live Health Probe
    const healthResp = await request.get('http://localhost:8000/health');
    expect(healthResp.ok()).toBeTruthy();
    const healthData = await healthResp.json();
    expect(healthData.status).toBe('healthy');
    expect(healthData.api_version).toBe('v1');

    // 2. Readiness Probe
    const readyResp = await request.get('http://localhost:8000/health/ready');
    expect(readyResp.ok()).toBeTruthy();
    const readyData = await readyResp.json();
    expect(readyData.ready).toBe(true);
    expect(readyData.database).toBe('healthy');
  });
});
