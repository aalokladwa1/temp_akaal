import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MappingStudio } from './MappingStudio';
import { mappingClient } from '../../../services/mappingClient';
import { ipcService } from '../../../services/ipcService';

vi.mock('../../../services/mappingClient', () => ({
  mappingClient: {
    compileMapping: vi.fn(),
    validateMapping: vi.fn(),
    previewMapping: vi.fn(),
    exportTemplate: vi.fn(),
    importTemplate: vi.fn(),
  },
}));

vi.mock('../../../services/ipcService', () => ({
  ipcService: {
    invokeEngineCapability: vi.fn(),
  },
}));

describe('MappingStudio Behavioral Integration Tests', () => {
  const sampleObjectDetail = {
    object_id: 'CUSTOMERS',
    object_name: 'CUSTOMERS',
    schema_id: 'public',
    columns: ['id', 'first_name', 'last_name', 'email'],
    pk_columns: ['id'],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Mapping Studio header and inputs correctly', () => {
    render(<MappingStudio selectedObjectDetail={sampleObjectDetail} selectedScope={{}} />);
    expect(screen.getByText(/Mapping Studio \(Backend Connected\)/i)).toBeInTheDocument();
    expect(screen.getByDisplayValue('public')).toBeInTheDocument();
    expect(screen.getByDisplayValue('CUSTOMERS')).toBeInTheDocument();
  });

  it('compiles mapping via mappingClient and displays status message', async () => {
    (mappingClient.compileMapping as any).mockResolvedValue({
      status: 'success',
      compiled_mapping: {
        schema_map: { public: 'public' },
        object_map: { CUSTOMERS: 'CUSTOMERS' },
        column_map: {},
        column_order: {},
        ignored_columns: {},
        target_defaults: {},
        generated_columns: {},
        fingerprint: 'fp-999',
      },
      diagnostics: [],
    });

    render(<MappingStudio selectedObjectDetail={sampleObjectDetail} selectedScope={{}} />);

    const compileBtn = screen.getByRole('button', { name: /Compile/i });
    fireEvent.click(compileBtn);

    await waitFor(() => {
      expect(mappingClient.compileMapping).toHaveBeenCalledTimes(1);
      expect(screen.getByText(/Compilation finished with status: success/i)).toBeInTheDocument();
    });
  });

  it('validates mapping via mappingClient and renders BLOCKER diagnostic alert when present', async () => {
    (mappingClient.validateMapping as any).mockResolvedValue({
      status: 'failed',
      is_valid: false,
      diagnostics: [
        { level: 'BLOCKER', code: 'DUPLICATE_TARGET_COLUMN', message: 'Two columns map to same target column' },
      ],
    });

    render(<MappingStudio selectedObjectDetail={sampleObjectDetail} selectedScope={{}} />);

    const validateBtn = screen.getByRole('button', { name: /Validate/i });
    fireEvent.click(validateBtn);

    await waitFor(() => {
      expect(mappingClient.validateMapping).toHaveBeenCalledTimes(1);
      expect(screen.getByText(/Validation FAILED with Blockers/i)).toBeInTheDocument();
      expect(screen.getByText(/\[BLOCKER\] DUPLICATE_TARGET_COLUMN/i)).toBeInTheDocument();
    });
  });

  it('executes real preview via ipcService & mappingClient and renders returned mapped rows', async () => {
    (ipcService.invokeEngineCapability as any).mockResolvedValue(
      JSON.stringify({ preview: { rows: [{ id: 101, first_name: 'Jane', last_name: 'Doe', email: 'jane@example.com' }] } })
    );

    (mappingClient.compileMapping as any).mockResolvedValue({
      status: 'success',
      compiled_mapping: {
        schema_map: {},
        object_map: {},
        column_map: { CUSTOMERS: { first_name: 'given_name', last_name: 'family_name' } },
        column_order: {},
        ignored_columns: {},
        target_defaults: {},
        generated_columns: {},
        fingerprint: 'fp-prev',
      },
      diagnostics: [],
    });

    (mappingClient.previewMapping as any).mockResolvedValue({
      status: 'success',
      source_object: 'CUSTOMERS',
      mapped_rows: [{ id: 101, given_name: 'Jane', family_name: 'Doe', email_address: 'jane@example.com' }],
      total_mapped: 1,
    });

    render(<MappingStudio selectedObjectDetail={sampleObjectDetail} selectedScope={{}} />);

    const previewBtn = screen.getByRole('button', { name: /Preview/i });
    fireEvent.click(previewBtn);

    await waitFor(() => {
      expect(ipcService.invokeEngineCapability).toHaveBeenCalledWith('p5_preview_selection', expect.any(String));
      expect(mappingClient.previewMapping).toHaveBeenCalledTimes(1);
      expect(screen.getByText(/Backend Mapped Row Transformation Preview:/i)).toBeInTheDocument();
      expect(screen.getByText(/given_name/i)).toBeInTheDocument();
    });
  });

  it('surfaces failure state when backend preview read fails (0 fake rows)', async () => {
    (ipcService.invokeEngineCapability as any).mockRejectedValue(new Error('Source database connection lost'));

    render(<MappingStudio selectedObjectDetail={sampleObjectDetail} selectedScope={{}} />);

    const previewBtn = screen.getByRole('button', { name: /Preview/i });
    fireEvent.click(previewBtn);

    await waitFor(() => {
      expect(screen.getByText(/Real bounded mapping preview failed/i)).toBeInTheDocument();
      expect(screen.getByText(/Source database connection lost/i)).toBeInTheDocument();
    });
  });

  it('exports mapping template via mappingClient.exportTemplate', async () => {
    (mappingClient.exportTemplate as any).mockResolvedValue({
      status: 'success',
      template: {
        template_id: 'tmpl-1',
        name: 'Template for CUSTOMERS',
        version: '1.0.0',
        description: 'Exported',
        routing: {},
        created_at: '2026-08-16T12:00:00Z',
      },
    });

    // Mock URL.createObjectURL
    window.URL.createObjectURL = vi.fn().mockReturnValue('blob:test');

    render(<MappingStudio selectedObjectDetail={sampleObjectDetail} selectedScope={{}} />);

    const exportBtn = screen.getByRole('button', { name: /Export/i });
    fireEvent.click(exportBtn);

    await waitFor(() => {
      expect(mappingClient.exportTemplate).toHaveBeenCalledTimes(1);
      expect(screen.getByText(/Mapping template exported successfully/i)).toBeInTheDocument();
    });
  });

  it('imports mapping template via mappingClient.importTemplate and updates compiled mapping state', async () => {
    (mappingClient.importTemplate as any).mockResolvedValue({
      status: 'success',
      compiled_mapping: {
        schema_map: { public: 'imported_schema' },
        object_map: { CUSTOMERS: 'IMPORTED_CUSTOMERS' },
        column_map: {},
        column_order: {},
        ignored_columns: {},
        target_defaults: {},
        generated_columns: {},
        fingerprint: 'fp-imported-99',
      },
      diagnostics: [],
    });

    const file = new File([JSON.stringify({ template_id: 'tmpl-import' })], 'template.json', { type: 'application/json' });

    render(<MappingStudio selectedObjectDetail={sampleObjectDetail} selectedScope={{}} />);

    const fileInput = screen.getByLabelText(/Import/i) as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(mappingClient.importTemplate).toHaveBeenCalledTimes(1);
      expect(screen.getByText(/Template imported and recompiled via backend/i)).toBeInTheDocument();
    });
  });
});
