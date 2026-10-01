import path from 'path';

export interface HarnessConfig {
  repoRoot: string;
  executablePath: string;
  defaultCdpPort: number;
  ipcPort: number;
  timeouts: {
    processSpawnMs: number;
    cdpConnectMs: number;
    ipcReadinessMs: number;
    uiNavigationMs: number;
    discoveryMs: number;
    planCompilationMs: number;
    migrationExecutionMs: number;
  };
  evidenceDir: string;
  userDataDir: string;
  mysql: {
    host: string;
    port: number;
    user: string;
    password?: string;
    database: string;
  };
  oracle: {
    host: string;
    port: number;
    user: string;
    password?: string;
    serviceName: string;
  };
  postgres: {
    host: string;
    port: number;
    user: string;
    password?: string;
    database: string;
  };
}

const repoRoot = path.resolve('a:/temp_akaal');

export const HARNESS_CONFIG: HarnessConfig = {
  repoRoot,
  executablePath: path.join(repoRoot, 'akaalSoftware', 'AKAAL.exe'),
  defaultCdpPort: 9244,
  ipcPort: 52199,
  timeouts: {
    processSpawnMs: 15000,
    cdpConnectMs: 25000,
    ipcReadinessMs: 15000,
    uiNavigationMs: 8000,
    discoveryMs: 30000,
    planCompilationMs: 20000,
    migrationExecutionMs: 120000,
  },
  evidenceDir: path.join(repoRoot, 'tests', 'acceptance', 'evidence'),
  userDataDir: path.join(repoRoot, '.akaal_webview_debug'),
  mysql: {
    host: process.env['DEVKROS_MYSQL_HOST'] || process.env['MYSQL_HOST'] || 'localhost',
    port: parseInt(process.env['DEVKROS_MYSQL_PORT'] || process.env['MYSQL_PORT'] || '3306', 10),
    user: process.env['DEVKROS_MYSQL_USER'] || process.env['MYSQL_USER'] || 'devkros_p8_m2_cdc',
    password: process.env['DEVKROS_MYSQL_PASSWORD'] || process.env['MYSQL_PASSWORD'] || 'DevKros#P8#Src2026',
    database: process.env['DEVKROS_MYSQL_DATABASE'] || process.env['MYSQL_DATABASE'] || 'devkros_p8_m2',
  },
  oracle: {
    host: process.env['DEVKROS_ORACLE_HOST'] || process.env['ORACLE_HOST'] || 'localhost',
    port: parseInt(process.env['DEVKROS_ORACLE_PORT'] || process.env['ORACLE_PORT'] || '1521', 10),
    user: process.env['DEVKROS_ORACLE_USER'] || process.env['ORACLE_TARGET_USER'] || 'DEVKROS_P8_M2_TGT',
    password: process.env['DEVKROS_ORACLE_PASSWORD'] || process.env['ORACLE_TARGET_PASSWORD'] || 'DevKros#P8#Tgt2026',
    serviceName: process.env['DEVKROS_ORACLE_SERVICE'] || 'FREEPDB1',
  },
  postgres: {
    host: process.env['DEVKROS_POSTGRES_HOST'] || process.env['POSTGRES_HOST'] || 'localhost',
    port: parseInt(process.env['DEVKROS_POSTGRES_PORT'] || process.env['POSTGRES_PORT'] || '5432', 10),
    user: process.env['DEVKROS_POSTGRES_USER'] || process.env['POSTGRES_USER'] || 'devkros_p8_tgt',
    password: process.env['DEVKROS_POSTGRES_PASSWORD'] || process.env['POSTGRES_PASSWORD'] || 'DevKros#P8#Tgt2026',
    database: process.env['DEVKROS_POSTGRES_DB'] || process.env['POSTGRES_DATABASE'] || 'devkros_p8',
  },
};
