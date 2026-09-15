/**
 * Pass 0 - Domain Semantic Concept Scanner
 * 
 * Corrects S1-4:
 * - Clarifies that concepts represent an empirical inventory of discovered domain
 *   semantic families and specialized enterprise capabilities, rather than a
 *   closed or exhaustive product domain universe.
 * - Expands scanning to capture granular specialized enterprise concepts:
 *   Schema Drift, LOB Handling, CDC Capture Engines, Data Masking/Tokenization,
 *   Segregation of Duties (SoD), JIT Privilege Elevation, and Cryptographic Proofs.
 */

const fs = require('fs');
const path = require('path');

const manifestsDir = path.resolve(__dirname, 'manifests');
const inventoryPath = path.join(manifestsDir, 'inventory_breakdown.json');
const frontendRoot = path.resolve(__dirname, '../../../frontend');

const inventory = JSON.parse(fs.readFileSync(inventoryPath, 'utf8'));

const primaryConceptFamilies = [
  { id: 'organization_workspace', term: 'Organization / Workspace / Tenant Hierarchy', regex: /organization|workspace|tenant/i, category: 'Multi-Tenancy' },
  { id: 'environment', term: 'Environment Tiering (Dev / Stage / Prod / DR)', regex: /environment|production|staging/i, category: 'Infrastructure' },
  { id: 'provider_connector', term: 'Providers & Connectors (48 Physical Engines)', regex: /provider|connector/i, category: 'Connectivity' },
  { id: 'connection_routing', term: 'Connections & Routing (TLS, SSH Bastion, Proxy)', regex: /connection|ssh_bastion|http_proxy|tls|probe/i, category: 'Connectivity' },
  { id: 'migration_definition', term: 'Migration Definition & Modes (M1–M8)', regex: /migrationmode|executionmode|m1_bulk|m2_bulk_cdc|m8_validation/i, category: 'Migration Core' },
  { id: 'project_initiative', term: 'Projects & Strategic Initiatives', regex: /initiative|project/i, category: 'Portfolio' },
  { id: 'schema_discovery', term: 'Schema Discovery & Estate (Tables, Columns, Types)', regex: /schema|table|column|datatype/i, category: 'Schema & Data' },
  { id: 'mapping_transform', term: 'Mapping & Data Controls (Transform, Cleanse)', regex: /mapping|transformation|cleansing/i, category: 'Schema & Data' },
  { id: 'configuration_engine', term: 'Enterprise Engine Tuning (Batches, Workers, Queues)', regex: /batchsize|buffer|concurrency|worker|backpressure/i, category: 'Engine Config' },
  { id: 'plan_dag', term: 'Dynamic Migration Plan & DAG Scheduling', regex: /plannode|dag|executionplan|barrier/i, category: 'Execution Plan' },
  { id: 'governance_approval', term: 'Governance, Readiness & Four-Eyes Approvals', regex: /foureyers|four-eyes|governance|barrier|approval/i, category: 'Governance' },
  { id: 'cockpit_execution', term: 'Execution Cockpit & Live Operations', regex: /cockpit|throughput|cdclag|watermark/i, category: 'Operations' },
  { id: 'cdc_replication', term: 'Continuous CDC & Stream Replication', regex: /cdc|streaming|lag|wal|binlog/i, category: 'Replication' },
  { id: 'cutover_failback', term: 'Cutover & Failback Operations', regex: /cutover|failback|switchover/i, category: 'Operations' },
  { id: 'validation_assurance', term: 'Validation & Integrity Assurance (M8)', regex: /validation|reconciliation|checksum|discrepancy/i, category: 'Validation' },
  { id: 'repair_remediation', term: 'Discrepancy Repair & Remediation', regex: /repair|remediation|revalidation/i, category: 'Validation' },
  { id: 'reports_library', term: 'Reports Library & Dossiers (13 Report Types)', regex: /report|dossier|catalog/i, category: 'Reporting' },
  { id: 'certification_evidence', term: 'Certification, Forensic Evidence & Hashes', regex: /certification|evidence|attestation|checksum/i, category: 'Reporting' },
  { id: 'monitoring_observability', term: 'System Monitoring & Observability', regex: /monitoring|telemetry|metric|tracing/i, category: 'Observability' },
  { id: 'alerts_incidents', term: 'Alerts, Incidents & Escalation Policies', regex: /alert|incident|escalation|pagerduty/i, category: 'Observability' },
  { id: 'audit_trail', term: 'Audit Trail, Retention & Legal Hold', regex: /audittrail|legalhold|retention/i, category: 'Compliance' },
  { id: 'compliance_controls', term: 'Compliance Frameworks & Controls (SOC2, HIPAA, GDPR)', regex: /compliance|soc2|hipaa|gdpr|framework/i, category: 'Compliance' },
  { id: 'identity_access', term: 'Identity, Access, SSO, SCIM, Roles & Permissions', regex: /sso|saml|oidc|scim|role|permission/i, category: 'Identity' },
  { id: 'secrets_vault', term: 'Secrets, Vault, KMS & Key Rotation', regex: /secret|vault|kms|keystore/i, category: 'Security' },
  { id: 'platform_lifecycle', term: 'Platform Admin, Maintenance & Licensing', regex: /maintenance|licensing|backup|restore|resilience/i, category: 'Platform' },
  { id: 'settings_preferences', term: 'Workstation Settings & Preferences', regex: /workstation|settings|preferences/i, category: 'Workstation' },
  { id: 'ai_intelligence', term: 'AI & Operator Intelligence Assistance', regex: /ai-intelligence|intelligence|assistant|rca/i, category: 'Intelligence' }
];

const granularEnterpriseCapabilities = [
  { id: 'schema_drift', term: 'Schema Drift Detection & Assessment', regex: /drift|schemadrift/i, category: 'Schema & Data' },
  { id: 'lob_handling', term: 'Large Object (LOB) Chunking & Streaming', regex: /\blob\b|clob|blob|chunking/i, category: 'Schema & Data' },
  { id: 'cdc_engines', term: 'CDC Capture Engines (LogMiner, Debezium, WAL)', regex: /logminer|debezium|wal2json|pgoutput|binlog/i, category: 'Replication' },
  { id: 'data_masking', term: 'Data Masking, Tokenization & Cleansing', regex: /masking|tokenization|anonymiz/i, category: 'Security' },
  { id: 'sod_enforcement', term: 'Segregation of Duties (SoD) & Toxic Combinations', regex: /\bsod\b|segregation.*duties/i, category: 'Governance' },
  { id: 'jit_elevation', term: 'Just-In-Time (JIT) Privilege Elevation & Break-Glass', regex: /\bjit\b|elevation|breakglass|break-glass/i, category: 'Identity' },
  { id: 'checksum_proofs', term: 'Cryptographic Checksum Proofs (SHA-256 Parity)', regex: /checksum|sha256|hashproof/i, category: 'Validation' }
];

const allTsFiles = [...inventory.models, ...inventory.services, ...inventory.components];

function scanList(conceptList) {
  return conceptList.map(c => {
    const matchingFiles = [];
    allTsFiles.forEach(f => {
      const fullPath = path.resolve(frontendRoot, f);
      const content = fs.readFileSync(fullPath, 'utf8');
      if (c.regex.test(content)) {
        matchingFiles.push(f);
      }
    });
    return {
      id: c.id,
      term: c.term,
      category: c.category,
      fileCount: matchingFiles.length,
      sampleFiles: matchingFiles.slice(0, 5)
    };
  });
}

const primaryResults = scanList(primaryConceptFamilies);
const granularResults = scanList(granularEnterpriseCapabilities);

console.log('=== DISCOVERED DOMAIN SEMANTIC FAMILIES (PRIMARY) ===');
primaryResults.forEach(r => {
  console.log(`${r.category.padEnd(16)} | ${r.term.padEnd(52)}: ${r.fileCount.toString().padStart(3)} files`);
});

console.log('\n=== GRANULAR SPECIALIZED ENTERPRISE CAPABILITIES ===');
granularResults.forEach(r => {
  console.log(`${r.category.padEnd(16)} | ${r.term.padEnd(52)}: ${r.fileCount.toString().padStart(3)} files`);
});

fs.writeFileSync(path.join(manifestsDir, 'domain_concepts_inventory.json'), JSON.stringify({
  qualification: 'Empirical inventory of discovered domain semantic families and specialized capabilities across frontend files (not an exhaustive universe claim)',
  primaryFamilies: primaryResults,
  granularCapabilities: granularResults
}, null, 2));
