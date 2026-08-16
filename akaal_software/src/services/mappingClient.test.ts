import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mappingClient, RoutingDefinitionDTO } from './mappingClient';
import { ipcService } from './ipcService';

vi.mock('./ipcService', () => ({
  ipcService: {
    invokeEngineCapability: vi.fn(),
  },
}));

describe('mappingClient IPC Boundary Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('compileMapping forwards routing definition to p5_compile_mapping capability', async () => {
    const mockResponse = {
      status: 'success',
      compiled_mapping: {
        schema_map: { public: 'dw' },
        object_map: { CUSTOMERS: 'CLIENTS' },
        column_map: {},
        column_order: {},
        ignored_columns: {},
        target_defaults: {},
        generated_columns: {},
        fingerprint: 'fp-1234',
      },
      diagnostics: [],
    };

    (ipcService.invokeEngineCapability as any).mockResolvedValue(JSON.stringify(mockResponse));

    const routing: RoutingDefinitionDTO = {
      schema_routes: [{ source_schema: 'public', target_schema: 'dw' }],
    };

    const res = await mappingClient.compileMapping({}, routing);

    expect(ipcService.invokeEngineCapability).toHaveBeenCalledWith(
      'p5_compile_mapping',
      expect.stringContaining('"target_schema":"dw"')
    );
    expect(res.status).toBe('success');
    expect(res.compiled_mapping?.fingerprint).toBe('fp-1234');
  });

  it('validateMapping forwards payload and returns validation diagnostics', async () => {
    const mockResponse = {
      status: 'valid',
      is_valid: true,
      diagnostics: [{ level: 'INFO', code: 'VALID', message: 'Mapping is valid' }],
    };

    (ipcService.invokeEngineCapability as any).mockResolvedValue(JSON.stringify(mockResponse));

    const res = await mappingClient.validateMapping({}, {});

    expect(ipcService.invokeEngineCapability).toHaveBeenCalledWith(
      'p5_validate_mapping',
      expect.any(String)
    );
    expect(res.is_valid).toBe(true);
    expect(res.diagnostics.length).toBe(1);
  });

  it('previewMapping sends source rows and compiled mapping to p5_preview_mapping', async () => {
    const mockResponse = {
      status: 'success',
      source_object: 'CUSTOMERS',
      mapped_rows: [{ given_name: 'Alice', family_name: 'Smith' }],
      total_mapped: 1,
    };

    (ipcService.invokeEngineCapability as any).mockResolvedValue(JSON.stringify(mockResponse));

    const compiledMapping = {
      schema_map: {},
      object_map: {},
      column_map: { CUSTOMERS: { first_name: 'given_name', last_name: 'family_name' } },
      column_order: {},
      ignored_columns: {},
      target_defaults: {},
      generated_columns: {},
      fingerprint: 'fp-1',
    };

    const res = await mappingClient.previewMapping(
      'CUSTOMERS',
      [{ first_name: 'Alice', last_name: 'Smith' }],
      compiledMapping
    );

    expect(ipcService.invokeEngineCapability).toHaveBeenCalledWith(
      'p5_preview_mapping',
      expect.stringContaining('given_name')
    );
    expect(res.mapped_rows[0].given_name).toBe('Alice');
    expect(res.total_mapped).toBe(1);
  });

  it('exportTemplate returns template DTO from p5_export_mapping_template', async () => {
    const mockResponse = {
      status: 'success',
      template: {
        template_id: 'tmpl-1',
        name: 'Standard Template',
        version: '1.0.0',
        description: 'Test template',
        routing: {},
        created_at: '2026-08-16T12:00:00Z',
      },
    };

    (ipcService.invokeEngineCapability as any).mockResolvedValue(JSON.stringify(mockResponse));

    const res = await mappingClient.exportTemplate({}, 'Standard Template');

    expect(ipcService.invokeEngineCapability).toHaveBeenCalledWith(
      'p5_export_mapping_template',
      expect.stringContaining('Standard Template')
    );
    expect(res.template.template_id).toBe('tmpl-1');
  });

  it('importTemplate passes imported json template to p5_import_mapping_template', async () => {
    const mockResponse = {
      status: 'success',
      compiled_mapping: { fingerprint: 'fp-imported' },
      diagnostics: [],
    };

    (ipcService.invokeEngineCapability as any).mockResolvedValue(JSON.stringify(mockResponse));

    const templateDTO = {
      template_id: 'tmpl-1',
      name: 'Imported Template',
      version: '1.0.0',
      description: 'Import test',
      routing: {},
      created_at: '2026-08-16T12:00:00Z',
    };

    const res = await mappingClient.importTemplate(templateDTO, {});

    expect(ipcService.invokeEngineCapability).toHaveBeenCalledWith(
      'p5_import_mapping_template',
      expect.stringContaining('Imported Template')
    );
    expect(res.compiled_mapping?.fingerprint).toBe('fp-imported');
  });

  it('propagates IPC error when backend throws exception', async () => {
    (ipcService.invokeEngineCapability as any).mockRejectedValue(new Error('Backend connection failed'));

    await expect(mappingClient.compileMapping({}, {})).rejects.toThrow('Backend connection failed');
  });
});
