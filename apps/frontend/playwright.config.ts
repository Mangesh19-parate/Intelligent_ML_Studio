import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: 'python -m uvicorn app.main:app --host 127.0.0.1 --port 8000',
      cwd: '../backend',
      url: 'http://127.0.0.1:8000/health',
      env: {
        ENV: 'testing',
        SEED_DEMO_DATA: 'true',
        AUTO_CREATE_TABLES: 'true',
      },
      reuseExistingServer: !process.env.CI,
      timeout: 60000,
    },
    {
      command: process.platform === 'win32'
        ? 'npm.cmd run dev -- --host 127.0.0.1 --port 5173'
        : 'npm run dev -- --host 127.0.0.1 --port 5173',
      url: 'http://127.0.0.1:5173',
      env: {
        VITE_API_URL: 'http://127.0.0.1:8000',
      },
      reuseExistingServer: !process.env.CI,
      timeout: 60000,
    },
  ],
});

