/**
 * AKAAL Administration — 5.8 Compliance Service
 * Authoritative presentation service for Control Frameworks, Framework Views,
 * Technical Control Mapping, Exceptions, and Compliance Evidence.
 */

import { Injectable, signal, computed, Optional, inject } from '@angular/core';
import { AdministrationIpcService } from '../../../core/services/ipc/administration.ipc';
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
  private adminIpc?: AdministrationIpcService;

  constructor(@Optional() adminIpc?: AdministrationIpcService) {
    if (adminIpc) {
      this.adminIpc = adminIpc;
    } else {
      try {
        this.adminIpc = inject(AdministrationIpcService, { optional: true }) || undefined;
      } catch {
        this.adminIpc = undefined;
      }
    }
    this.loadFromBackend();
  }

  public async loadFromBackend(): Promise<void> {
    if (!this.adminIpc) return;
    try {
      const respFw = await this.adminIpc.listComplianceFrameworks();
      if (respFw.status === 'SUCCESS' && Array.isArray(respFw.data)) {
        this.frameworks.set(respFw.data);
      }

      const respExc = await this.adminIpc.listComplianceExceptions();
      if (respExc.status === 'SUCCESS' && Array.isArray(respExc.data)) {
        this.exceptions.set(respExc.data);
      }

      const respEv = await this.adminIpc.listComplianceEvidence();
      if (respEv.status === 'SUCCESS' && Array.isArray(respEv.data)) {
        this.evidence.set(respEv.data);
      }
    } catch {
      // Offline fallback
    }
  }
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
  public customFrameworks = signal<CustomFramework[]>([]);

  // Control Mappings
  public controlMappings = signal<ControlMapping[]>([]);

  // Compliance Exceptions
  public exceptions = signal<ComplianceException[]>([]);

  // Compliance Evidence
  public evidence = signal<ComplianceEvidence[]>([]);

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
