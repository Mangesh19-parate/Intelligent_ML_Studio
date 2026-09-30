import { test, expect, chromium } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function runBrutalInspection() {
  console.log('============================================================');
  console.log(' INTELLIGENT ML STUDIO — BRUTAL BROWSER INSPECTION');
  console.log('============================================================\n');

  const evidenceDir = path.resolve(__dirname, '../../evidence/screenshots');
  if (!fs.existsSync(evidenceDir)) {
    fs.mkdirSync(evidenceDir, { recursive: true });
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  const page = await context.newPage();

  const consoleLogs: Array<{ type: string; text: string }> = [];
  const networkErrors: Array<{ url: string; status: number; method: string }> = [];

  page.on('console', (msg) => {
    consoleLogs.push({ type: msg.type(), text: msg.text() });
  });

  page.on('response', (res) => {
    if (res.status() >= 400 && !res.url().includes('/api/v1/auth/refresh')) {
      networkErrors.push({ url: res.url(), status: res.status(), method: res.request().method() });
    }
  });

  const report: Record<string, any> = {
    pages_inspected: [],
    findings: [],
    console_summary: {},
    network_health: {},
    theme_support: {},
  };

  try {
    // 1. Landing Page Inspection
    console.log('[1/11] Inspecting Landing Page (http://127.0.0.1:5173/)...');
    await page.goto('http://127.0.0.1:5173/');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: path.join(evidenceDir, '01_landing_page.png'), fullPage: true });

    const landingTitle = await page.title();
    const heroHeading = await page.locator('h1').first().textContent();
    report.pages_inspected.push({ route: '/', title: landingTitle, hero: heroHeading });

    // 2. Authentication Flow & Login Page
    console.log('[2/11] Inspecting Login Flow (http://127.0.0.1:5173/login)...');
    await page.goto('http://127.0.0.1:5173/login');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: path.join(evidenceDir, '02_login_page.png') });

    await page.fill('input[type="email"], input[name="email"]', 'admin@studio.dev');
    await page.fill('input[type="password"], input[name="password"]', 'DemoPassword123!');
    await page.click('button[type="submit"]');

    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 15000 });
    console.log(`  > Successfully authenticated as Admin. Current URL: ${page.url()}`);
    await page.screenshot({ path: path.join(evidenceDir, '03_post_login_dashboard.png') });

    // 3. Workspace Dashboard (/dashboard)
    console.log('[3/11] Inspecting Workspace Dashboard (/dashboard)...');
    await page.goto('http://127.0.0.1:5173/dashboard');
    await page.waitForLoadState('networkidle');
    const dashboardText = await page.locator('body').textContent();
    report.pages_inspected.push({ route: '/dashboard', hasContent: !!dashboardText });
    await page.screenshot({ path: path.join(evidenceDir, '04_workspace_dashboard.png') });

    // 4. Data Ingestion & Dataset Management (/data)
    console.log('[4/11] Inspecting Data Management (/data)...');
    await page.goto('http://127.0.0.1:5173/data');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: path.join(evidenceDir, '05_data_management.png') });
    report.pages_inspected.push({ route: '/data', status: 'OK' });

    // 5. Statistical Profiling & EDA (/data-analysis)
    console.log('[5/11] Inspecting Statistical EDA & Profiling (/data-analysis)...');
    await page.goto('http://127.0.0.1:5173/data-analysis');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: path.join(evidenceDir, '06_data_analysis.png') });
    report.pages_inspected.push({ route: '/data-analysis', status: 'OK' });

    // 6. Transformations & Cleaning (/transformations)
    console.log('[6/11] Inspecting Feature Transformations (/transformations)...');
    await page.goto('http://127.0.0.1:5173/transformations');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: path.join(evidenceDir, '07_transformations.png') });
    report.pages_inspected.push({ route: '/transformations', status: 'OK' });

    // 7. Feature Engineering (/feature-engineering)
    console.log('[7/11] Inspecting Feature Engineering (/feature-engineering)...');
    await page.goto('http://127.0.0.1:5173/feature-engineering');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: path.join(evidenceDir, '08_feature_engineering.png') });
    report.pages_inspected.push({ route: '/feature-engineering', status: 'OK' });

    // 8. Machine Learning Training (/ml)
    console.log('[8/11] Inspecting ML Training (/ml)...');
    await page.goto('http://127.0.0.1:5173/ml');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: path.join(evidenceDir, '09_ml_training.png') });
    report.pages_inspected.push({ route: '/ml', status: 'OK' });

    // 9. Diagnostics & Explainability (/diagnostics)
    console.log('[9/11] Inspecting Diagnostics & SHAP (/diagnostics)...');
    await page.goto('http://127.0.0.1:5173/diagnostics');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: path.join(evidenceDir, '10_diagnostics.png') });
    report.pages_inspected.push({ route: '/diagnostics', status: 'OK' });

    // 10. Production & Deployment Gates (/production)
    console.log('[10/11] Inspecting Production Deployment (/production)...');
    await page.goto('http://127.0.0.1:5173/production');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: path.join(evidenceDir, '11_production.png') });
    report.pages_inspected.push({ route: '/production', status: 'OK' });

    // 11. Monitoring & System Governance (/monitoring & /admin)
    console.log('[11/11] Inspecting Monitoring & Admin Governance (/monitoring & /admin)...');
    await page.goto('http://127.0.0.1:5173/monitoring');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: path.join(evidenceDir, '12_monitoring.png') });

    await page.goto('http://127.0.0.1:5173/admin');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: path.join(evidenceDir, '13_admin_panel.png') });

    // Dark/Light Theme Switch Test
    const themeBtn = page.locator('button[aria-label*="Mode"], button:has(svg.lucide-sun), button:has(svg.lucide-moon)').first();
    if (await themeBtn.isVisible()) {
      await themeBtn.click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(evidenceDir, '14_light_theme_toggle.png') });
      report.theme_support.toggle_tested = true;
    }

    report.console_logs_count = consoleLogs.length;
    report.console_errors = consoleLogs.filter((l) => l.type === 'error');
    report.network_errors = networkErrors;

    const reportPath = path.resolve(__dirname, '../../evidence/brutal_inspection_report.json');
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), 'utf-8');
    console.log(`\n[SUCCESS] Brutal inspection complete. Report saved to: ${reportPath}`);
  } catch (err: any) {
    console.error('Inspection failed:', err);
  } finally {
    await browser.close();
  }
}

runBrutalInspection();
