import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['src/**/*.spec.ts'],
    poolOptions: {
      threads: {
        execArgv: ['--max-old-space-size=8192']
      },
      forks: {
        execArgv: ['--max-old-space-size=8192']
      }
    }
  }
});
