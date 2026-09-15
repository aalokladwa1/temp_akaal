/**
 * AKAAL Administration — 5.8 Compliance Service
 * Authoritative presentation service for Control Frameworks, Framework Views,
 * Technical Control Mapping, Exceptions, and Compliance Evidence.
 */

import { Injectable, signal, computed } from '@angular/core';
import {
  ControlFramework,
  FrameworkControl,
  CustomFramework,
  ControlMapping,
  ComplianceException,
  ComplianceEvidence,
  RegulatoryDomain
} from '../models/compliance.models';

@Injectable({
  providedIn: 'root'
})
export class ComplianceService {
  // Built-in Control Frameworks
  public frameworks = signal<ControlFramework[]>([
    {
      id: 'fw-gdpr',
      name: 'General Data Protection Regulation',
      code: 'EU-GDPR-2016/679',
      version: '2016/679',
      regulatoryDomain: 'GDPR',
      authorityBody: 'European Parliament and Council',
      totalControls: 32,
      mappedControlsCount: 28,
      status: 'ACTIVE',
      isBuiltIn: true,
      description: 'Technical privacy safeguards, data subject erasure controls, cross-border transfer boundaries, and cryptographic encryption.'
    },
    {
      id: 'fw-pci',
      name: 'Payment Card Industry Data Security Standard',
      code: 'PCI-DSS-v4.0',
      version: '4.0.1',
      regulatoryDomain: 'PCI_DSS',
      authorityBody: 'PCI Security Standards Council',
      totalControls: 44,
      mappedControlsCount: 40,
      status: 'ACTIVE',
      isBuiltIn: true,
      description: 'Cardholder data protection, network segmentation, format-preserving tokenization, and administrative audit logging.'
    },
    {
      id: 'fw-hipaa',
      name: 'Health Insurance Portability and Accountability Act',
      code: 'HIPAA-Security-Rule',
      version: '45 CFR Part 160/164',
      regulatoryDomain: 'HIPAA',
      authorityBody: 'U.S. Department of Health and Human Services',
      totalControls: 26,
      mappedControlsCount: 24,
      status: 'ACTIVE',
      isBuiltIn: true,
      description: 'Electronic Protected Health Information (ePHI) confidentiality, transit encryption, and integrity verification.'
    },
    {
      id: 'fw-soc2',
      name: 'AICPA Trust Services Criteria (SOC 2 Type II)',
      code: 'SOC-2-TSC-2022',
      version: '2022',
      regulatoryDomain: 'SOC_2',
      authorityBody: 'American Institute of CPAs',
      totalControls: 38,
      mappedControlsCount: 35,
      status: 'ACTIVE',
      isBuiltIn: true,
      description: 'Security, availability, processing integrity, and confidentiality trust services criteria.'
    },
    {
      id: 'fw-iso27001',
      name: 'ISO/IEC 27001:2022 Information Security Controls',
      code: 'ISO-27001:2022',
      version: '2022 Annex A',
      regulatoryDomain: 'ISO_27001',
      authorityBody: 'International Organization for Standardization',
      totalControls: 93,
      mappedControlsCount: 81,
      status: 'ACTIVE',
      isBuiltIn: true,
      description: 'Organizational, people, physical, and technological information security management controls.'
    }
  ]);

  // Framework Controls Catalog
  public frameworkControls = signal<FrameworkControl[]>([
    {
      id: 'fc-gdpr-art32',
      frameworkId: 'fw-gdpr',
      controlCode: 'GDPR-Art-32',
      title: 'Security of Processing and Pseudonymization',
      domain: 'Technical Safeguards',
      description: 'Implement appropriate technical and organizational measures to ensure a level of security appropriate to the risk.',
      mappedTechnicalControls: ['TECH-FPE-01', 'TECH-TLS-02'],
      mappingState: 'FULLY_MAPPED',
      evidenceCount: 6
    },
    {
      id: 'fc-gdpr-art17',
      frameworkId: 'fw-gdpr',
      controlCode: 'GDPR-Art-17',
      title: 'Right to Erasure (Right to be Forgotten)',
      domain: 'Data Subject Rights',
      description: 'Erasure of personal data without undue delay where data is no longer necessary in relation to processing purposes.',
      mappedTechnicalControls: ['TECH-PURGE-01'],
      mappingState: 'PARTIALLY_MAPPED',
      evidenceCount: 2
    },
    {
      id: 'fc-pci-req3',
      frameworkId: 'fw-pci',
      controlCode: 'PCI-Req-3.4',
      title: 'Render Primary Account Number (PAN) Unreadable',
      domain: 'Cardholder Data Protection',
      description: 'Render PAN unreadable anywhere it is stored using strong cryptography, one-way hashes, or tokenization.',
      mappedTechnicalControls: ['TECH-FPE-01', 'TECH-KMS-01'],
      mappingState: 'FULLY_MAPPED',
      evidenceCount: 8
    },
    {
      id: 'fc-pci-req10',
      frameworkId: 'fw-pci',
      controlCode: 'PCI-Req-10.2',
      title: 'Audit Trail for Administrative and System Access',
      domain: 'Logging and Monitoring',
      description: 'Implement automated audit trails for all system components to reconstruct user access to cardholder data.',
      mappedTechnicalControls: ['TECH-AUDIT-01', 'TECH-WORM-01'],
      mappingState: 'FULLY_MAPPED',
      evidenceCount: 12
    },
    {
      id: 'fc-hipaa-164312',
      frameworkId: 'fw-hipaa',
      controlCode: 'HIPAA-164.312(a)',
      title: 'Access Control and Unique User Identification',
      domain: 'Technical Safeguards',
      description: 'Assign a unique name and/or number for identifying and tracking user identity in electronic health systems.',
      mappedTechnicalControls: ['TECH-MFA-01', 'TECH-RBAC-01'],
      mappingState: 'FULLY_MAPPED',
      evidenceCount: 4
    },
    {
      id: 'fc-soc2-cc6',
      frameworkId: 'fw-soc2',
      controlCode: 'SOC2-CC6.1',
      title: 'Logical Boundary and Perimeter Defense',
      domain: 'Logical Access Controls',
      description: 'Restricts logical access to system components through role-based entitlements and boundary isolation.',
      mappedTechnicalControls: ['TECH-ENCLAVE-01', 'TECH-RBAC-01'],
      mappingState: 'FULLY_MAPPED',
      evidenceCount: 5
    }
  ]);

  // Custom Frameworks
  public customFrameworks = signal<CustomFramework[]>([
    {
      id: 'cfw-01',
      name: 'Internal Sovereign FinTech Security Standard',
      code: 'CORP-FINTECH-SEC-v2',
      version: '2.1.0',
      authorityOwner: 'Enterprise Risk & Governance Committee',
      description: 'Mandatory zero-trust dual-custody controls for cross-border financial transactions and ledger migrations.',
      controlsCount: 14,
      createdAt: '2025-11-14',
      status: 'ACTIVE'
    }
  ]);

  // Control Mappings
  public controlMappings = signal<ControlMapping[]>([
    {
      id: 'map-01',
      frameworkControlId: 'fc-gdpr-art32',
      frameworkName: 'General Data Protection Regulation',
      controlCode: 'GDPR-Art-32',
      akaalTechnicalControlId: 'TECH-FPE-01',
      technicalControlName: 'NIST FF3-1 Format-Preserving Encryption Engine',
      rationale: 'In-flight columnar tokenization renders identity fields pseudonymous prior to network transit.',
      verifiedAt: '2026-02-10',
      status: 'ACTIVE'
    },
    {
      id: 'map-02',
      frameworkControlId: 'fc-pci-req3',
      frameworkName: 'Payment Card Industry Data Security Standard',
      controlCode: 'PCI-Req-3.4',
      akaalTechnicalControlId: 'TECH-KMS-01',
      technicalControlName: 'Envelope KMS AES-256-GCM Cryptographic Storage',
      rationale: 'Envelope encryption guarantees card numbers are stored strictly under hardware-backed customer keys.',
      verifiedAt: '2026-02-12',
      status: 'ACTIVE'
    },
    {
      id: 'map-03',
      frameworkControlId: 'fc-pci-req10',
      frameworkName: 'Payment Card Industry Data Security Standard',
      controlCode: 'PCI-Req-10.2',
      akaalTechnicalControlId: 'TECH-AUDIT-01',
      technicalControlName: 'Tamper-Evident SHA-256 Merkle Audit Stream',
      rationale: 'Administrative mutations produce chained SHA-256 hashes forwarded to SIEM collectors.',
      verifiedAt: '2026-02-15',
      status: 'ACTIVE'
    }
  ]);

  // Compliance Exceptions
  public exceptions = signal<ComplianceException[]>([
    {
      id: 'exc-01',
      code: 'EXC-2026-001',
      title: 'Temporary Non-FIDO2 Legacy Service Account Exception',
      frameworkId: 'fw-hipaa',
      controlCode: 'HIPAA-164.312(a)',
      reason: 'Batch ingestion daemon connects via mutual TLS certificate rather than interactive WebAuthn MFA.',
      scope: 'Service Account: svc-batch-importer-01',
      justification: 'Automated machine-to-machine background process authenticated via X.509 client certificate under isolated VPC.',
      approvedBy: 'Chief Information Security Officer',
      validUntil: '2026-12-31',
      status: 'APPROVED'
    }
  ]);

  // Compliance Evidence
  public evidence = signal<ComplianceEvidence[]>([
    {
      id: 'ev-01',
      evidenceType: 'HASH_ATTESTATION',
      title: 'PostgreSQL Bulk Migration Execution Digest Attestation',
      relatedControlCode: 'PCI-Req-10.2',
      originSystem: 'akaalEngine/runtime',
      sha256Digest: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      verificationStatus: 'DIGEST_VERIFIED',
      collectedAt: '2026-02-19 14:02 UTC',
      sizeBytes: 4120
    },
    {
      id: 'ev-02',
      evidenceType: 'ENCRYPTION_PROOF',
      title: 'TLS 1.3 Cipher Suite Inspection & Key Exchange Attestation',
      relatedControlCode: 'GDPR-Art-32',
      originSystem: 'akaalPipeline/security',
      sha256Digest: '7b52009b64fd0a2a49e6d8a939753077792b0554ca5a6e8b4e76a666e5f8f8f2',
      verificationStatus: 'DIGEST_VERIFIED',
      collectedAt: '2026-02-18 09:30 UTC',
      sizeBytes: 1890
    },
    {
      id: 'ev-03',
      evidenceType: 'IMMUTABLE_LOG_DIGEST',
      title: 'Administrative Role Assignment Audit Batch Digest',
      relatedControlCode: 'SOC2-CC6.1',
      originSystem: 'akaal/governance',
      sha256Digest: '8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4',
      verificationStatus: 'DIGEST_VERIFIED',
      collectedAt: '2026-02-17 16:45 UTC',
      sizeBytes: 8340
    }
  ]);

  public getFrameworkById(id: string): ControlFramework | undefined {
    return this.frameworks().find(f => f.id === id);
  }

  public getFrameworkByDomain(domain: RegulatoryDomain): ControlFramework | undefined {
    return this.frameworks().find(f => f.regulatoryDomain === domain);
  }

  public getControlsForFramework(frameworkId: string): FrameworkControl[] {
    return this.frameworkControls().filter(c => c.frameworkId === frameworkId);
  }

  public getEvidenceById(id: string): ComplianceEvidence | undefined {
    return this.evidence().find(e => e.id === id);
  }

  public createCustomFramework(fw: Omit<CustomFramework, 'id' | 'createdAt' | 'status'>): void {
    const newRecord: CustomFramework = {
      ...fw,
      id: `cfw-${Date.now()}`,
      createdAt: new Date().toISOString().split('T')[0],
      status: 'ACTIVE'
    };
    this.customFrameworks.update(list => [newRecord, ...list]);
  }

  public createException(exc: Omit<ComplianceException, 'id' | 'status'>): void {
    const newRecord: ComplianceException = {
      ...exc,
      id: `exc-${Date.now()}`,
      status: 'APPROVED'
    };
    this.exceptions.update(list => [newRecord, ...list]);
  }
}
