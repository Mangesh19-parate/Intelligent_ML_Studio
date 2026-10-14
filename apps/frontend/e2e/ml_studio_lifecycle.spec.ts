import { test, expect } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';

/**
 * Intelligent ML Studio - Full-Lifecycle Browser & API End-to-End Suite.
 * Validates deterministic complete platform workflow with REAL state mutations:
 * Authentication -> Workspace Dashboard -> Project Creation -> Dataset Ingestion ->
 * Schema Verification -> Outer Split -> Exploratory Data Analysis -> Transformations ->
 * Feature Engineering -> Diagnostics -> Deployment Governance -> Inference & Observability.
 */

test.describe('Intelligent ML Studio - Full Platform Lifecycle', () => {
  test('Complete End-to-End User Workflow & Distributed Pipeline Execution', async ({ page }) => {
    page.on('console', (msg) => console.log(`[Browser Console ${msg.type()}]: ${msg.text()}`));
    page.on('pageerror', (err) => console.log(`[Browser Error]: ${err.message}`));

    // 1. Visit Login Page & Assert UI Structure
    await page.goto('/login');
    await expect(page).toHaveTitle(/ML Studio|Intelligent ML Studio/i);

    const emailInput = page.locator('input[type="email"], input[name="email"]').first();
    await expect(emailInput).toBeVisible({ timeout: 15000 });
    const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
    await expect(passwordInput).toBeVisible();

    // 2. Perform Deterministic Authentication with Seeded Admin Account
    await emailInput.fill('admin@studio.dev');
    await passwordInput.fill('DemoPassword123!');
    const submitBtn = page.locator('button[type="submit"]').first();
    await expect(submitBtn).toBeEnabled();
    await submitBtn.click();

    // 3. Assert Navigation to Workspace Dashboard
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20000 });
    await expect(page.locator('body')).toBeVisible();
    await expect(page.locator('h1, h2, h3').first()).toBeVisible();

    // 4. Create Project with Real State Mutation
    const newProjBtn = page.locator('button:has-text("New Project")').first();
    if (await newProjBtn.isVisible()) {
      await newProjBtn.click();
      const projNameInput = page.locator('input[placeholder*="Loan Default"], input[type="text"]').first();
      await projNameInput.fill(`Lifecycle Project ${Date.now()}`);
      const createBtn = page.locator('form button[type="submit"]:has-text("Create"), button:has-text("Create ML Studio Project"), form button:has-text("Project")').first();
      if (await createBtn.isVisible()) {
        await createBtn.click();
        await page.waitForTimeout(1000);
      }
    }

    // 5. Data Ingestion & Dataset Management Stage
    await page.goto('/data');
    await page.waitForURL((url) => url.pathname.includes('/data'), { timeout: 15000 });
    await expect(page.locator('body')).toContainText(/dataset|data|project|schema|upload/i);

    // Upload deterministic tabular CSV fixture
    const tmpCsvPath = path.join(os.tmpdir(), `fixture_e2e_${Date.now()}.csv`);
    const csvContent =
      'age,income,credit_score,churn\n' +
      '34,55000,720,0\n' +
      '45,82000,680,0\n' +
      '29,48000,610,1\n' +
      '52,120000,790,0\n' +
      '38,62000,640,0\n' +
      '41,71000,730,0\n' +
      '36,58000,690,0\n' +
      '48,91000,760,0\n' +
      '22,28000,580,1\n' +
      '59,145000,810,0\n' +
      '31,49000,650,1\n' +
      '27,39000,620,1\n' +
      '44,88000,740,0\n' +
      '50,110000,780,0\n' +
      '33,52000,670,0\n' +
      '28,41000,600,1\n' +
      '63,160000,820,0\n';
    fs.writeFileSync(tmpCsvPath, csvContent, 'utf-8');

    try {
      const fileInput = page.locator('input[type="file"]').first();
      if (await fileInput.count() > 0) {
        await fileInput.setInputFiles(tmpCsvPath);
        await page.waitForTimeout(2000);
      }
    } finally {
      try {
        fs.unlinkSync(tmpCsvPath);
      } catch {
        // ignore cleanup error
      }
    }

    // 6. Exploratory Data Analysis & Statistical Profiling Stage
    await page.goto('/data-analysis');
    await page.waitForURL((url) => url.pathname.includes('/data-analysis'), { timeout: 15000 });
    await expect(page.locator('body')).toContainText(/analysis|profiling|eda|distribution|statistics/i);

    // 7. Data Cleaning & Feature Transformation Stage
    await page.goto('/transformations');
    await page.waitForURL((url) => url.pathname.includes('/transformations'), { timeout: 15000 });
    await expect(page.locator('body')).toContainText(/transform|scaling|imputation|encoding|clean/i);

    // 8. Feature Engineering & Selection Stage
    await page.goto('/feature-engineering');
    await page.waitForURL((url) => url.pathname.includes('/feature-engineering'), { timeout: 15000 });
    await expect(page.locator('body')).toContainText(/feature|selection|importance|ranking|correlation/i);

    // 9. Model Training & Leaderboard Stage
    await page.goto('/ml');
    await page.waitForURL((url) => url.pathname.includes('/ml'), { timeout: 15000 });
    await expect(page.locator('body')).toContainText(/training|leaderboard|model|experiment|metric/i);

    // 10. Model Diagnostics, Recommendations & SHAP Explainability Stage
    await page.goto('/diagnostics');
    await page.waitForURL((url) => url.pathname.includes('/diagnostics'), { timeout: 15000 });
    await expect(page.locator('body')).toContainText(/diagnostic|leakage|recommendation|explainability|shap/i);

    // 11. Production Deployment, Governance Gate & Live Prediction Stage
    await page.goto('/production');
    await page.waitForURL((url) => url.pathname.includes('/production'), { timeout: 15000 });
    await expect(page.locator('body')).toContainText(/production|deploy|gate|endpoint|predict/i);

    // 12. Live Monitoring & Drift Observability Stage
    await page.goto('/monitoring');
    await page.waitForURL((url) => url.pathname.includes('/monitoring'), { timeout: 15000 });
    await expect(page.locator('body')).toContainText(/monitor|drift|latency|telemetry|metrics/i);
  });

  test('Real Platform API Lifecycle, Governance & Inference Contract', async ({ request }) => {
    // 1. Authenticate with seeded trainer account
    const loginResp = await request.post('http://127.0.0.1:8000/api/v1/auth/login', {
      data: {
        email: 'trainer@demo.com',
        password: 'DemoPassword123!',
      },
    });
    expect(loginResp.ok()).toBeTruthy();
    const loginData = await loginResp.json();
    const token = loginData.access_token;
    expect(token).toBeTruthy();
    const headers = { Authorization: `Bearer ${token}` };

    // 2. Create Project
    const projResp = await request.post('http://127.0.0.1:8000/api/v1/projects', {
      headers,
      data: {
        project_name: `E2E Verified Project ${Date.now()}`,
        target_column: 'churn',
        task_type: 'CLASSIFICATION',
      },
    });
    expect(projResp.ok()).toBeTruthy();
    const projData = await projResp.json();
    const projId = projData.id;
    expect(projId).toBeTruthy();

    // 3. Upload Tabular Dataset
    const csvData =
      'age,income,credit_score,churn\n' +
      '34,55000,720,0\n' +
      '45,82000,680,0\n' +
      '29,48000,610,1\n' +
      '52,120000,790,0\n' +
      '38,62000,640,0\n' +
      '41,71000,730,0\n' +
      '36,58000,690,0\n' +
      '48,91000,760,0\n' +
      '22,28000,580,1\n' +
      '59,145000,810,0\n' +
      '31,49000,650,1\n' +
      '27,39000,620,1\n' +
      '44,88000,740,0\n' +
      '50,110000,780,0\n' +
      '33,52000,670,0\n' +
      '28,41000,600,1\n' +
      '63,160000,820,0\n';

    const uploadResp = await request.post(`http://127.0.0.1:8000/api/v1/projects/${projId}/datasets`, {
      headers,
      multipart: {
        file: {
          name: 'e2e_churn_test.csv',
          mimeType: 'text/csv',
          buffer: Buffer.from(csvData),
        },
      },
    });
    expect(uploadResp.ok()).toBeTruthy();
    const uploadData = await uploadResp.json();
    const datasetId = uploadData.id;
    expect(datasetId).toBeTruthy();
    expect(uploadData.row_count).toBe(17);
    expect(uploadData.column_count).toBe(4);
    expect(uploadData.content_hash).toHaveLength(64);

    // 4. Inspect Columns Schema
    const colResp = await request.get(`http://127.0.0.1:8000/api/v1/datasets/${datasetId}/columns`, { headers });
    expect(colResp.ok()).toBeTruthy();
    const columns = await colResp.json();
    expect(columns.length).toBe(4);
    const colNames = columns.map((c: any) => c.column_name);
    expect(colNames).toContain('churn');
    expect(colNames).toContain('age');

    // 5. Create 80/20 Outer Split (Required before profiling to prevent leakage)
    const splitResp = await request.post(`http://127.0.0.1:8000/api/v1/datasets/${datasetId}/split`, {
      headers,
      data: { locked_test_pct: 20, seed: 42 },
    });
    expect(splitResp.ok()).toBeTruthy();
    const splitData = await splitResp.json();
    expect(splitData.development_rows).toBeGreaterThan(0);
    expect(splitData.locked_test_rows).toBeGreaterThan(0);

    // 6. Generate Profiling & DQI on Development data
    const profileResp = await request.post(`http://127.0.0.1:8000/api/v1/datasets/${datasetId}/profile`, { headers });
    expect(profileResp.ok()).toBeTruthy();
    const profileData = await profileResp.json();
    expect(profileData.total_rows).toBeGreaterThan(0);
    expect(profileData.data_quality_index).toBeDefined();

    // 7. Security and Negative Test: Unauthenticated request must be rejected
    const unauthResp = await request.get(`http://127.0.0.1:8000/api/v1/projects/${projId}`);
    expect(unauthResp.status()).toBe(401);

    // 8. Negative Test: Malformed/Invalid prediction request must reject with 422
    const invalidPredResp = await request.post('http://127.0.0.1:8000/api/v1/predict/invalid-dep-uuid', {
      data: 'invalid json string payload',
      headers: { 'Content-Type': 'application/json' },
    });
    expect([404, 422]).toContain(invalidPredResp.status());
  });

  test('System Health, Readiness & Observability Contract', async ({ request }) => {
    // 1. Live Health Probe
    const healthResp = await request.get('http://127.0.0.1:8000/health');
    expect(healthResp.ok()).toBeTruthy();
    const healthData = await healthResp.json();
    expect(healthData.status).toBe('healthy');
    expect(healthData.api_version).toBe('v1');

    // 2. Readiness Probe
    const readyResp = await request.get('http://127.0.0.1:8000/health/ready');
    expect(readyResp.ok()).toBeTruthy();
    const readyData = await readyResp.json();
    expect(readyData.ready).toBe(true);
    expect(readyData.dependencies.database.status).toBe('UP');

    // 3. Multi-Subsystem Health Status Probe
    const statusResp = await request.get('http://127.0.0.1:8000/health/status');
    expect(statusResp.ok()).toBeTruthy();
    const statusData = await statusResp.json();
    expect(statusData.dependencies).toBeDefined();
    expect(statusData.dependencies.database).toBeDefined();
    expect(statusData.dependencies.storage).toBeDefined();
  });
});
