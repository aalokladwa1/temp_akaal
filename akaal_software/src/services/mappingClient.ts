/**
 * Structural Mapping Client Service.
 * Bridges React UI components to backend Python Gateway mapping capabilities via IPC.
 */
import { ipcService } from './ipcService';

export interface ColumnMappingDTO {
  source_column: string;
  target_column: string;
  source_object: string;
  target_object: string;
  is_ignored?: boolean;
  target_default?: string;
  is_generated?: boolean;
  datatype_override?: string;
}

export interface BulkMappingRuleDTO {
  rule_id: string;
  rule_type: string; // "SCHEMA_RENAME" | "OBJECT_RENAME" | "COLUMN_RENAME" | "CASE_CONVERT"
  pattern: string;
  replacement: string;
  is_regex?: boolean;
  priority?: number;
}

export interface RoutingDefinitionDTO {
  schema_routes?: Array<{ source_schema: string; target_schema: string }>;
  object_routes?: Array<{ source_schema: string; source_object: string; target_schema: string; target_object: string; object_type: string }>;
  column_mappings?: ColumnMappingDTO[];
  bulk_rules?: BulkMappingRuleDTO[];
}

export interface CompilationDiagnosticDTO {
  level: string; // "INFO" | "WARNING" | "BLOCKER"
  code: string;
  message: string;
  target?: string;
}

export interface CompiledMappingDTO {
  schema_map: Record<string, string>;
  object_map: Record<string, string>;
  column_map: Record<string, Record<string, string>>;
  column_order: Record<string, string[]>;
  ignored_columns: Record<string, string[]>;
  target_defaults: Record<string, Record<string, string>>;
  generated_columns: Record<string, string[]>;
  fingerprint: string;
}

export interface CompileMappingResponseDTO {
  status: string;
  compiled_mapping?: CompiledMappingDTO;
  diagnostics: CompilationDiagnosticDTO[];
}

export interface ValidateMappingResponseDTO {
  status: string;
  is_valid: boolean;
  diagnostics: CompilationDiagnosticDTO[];
}

export interface PreviewMappingResponseDTO {
  status: string;
  source_object: string;
  mapped_rows: Record<string, any>[];
  total_mapped: number;
}

export interface MappingTemplateDTO {
  template_id: string;
  name: string;
  version: string;
  description: string;
  routing: RoutingDefinitionDTO;
  created_at: string;
}

export interface ExportTemplateResponseDTO {
  status: string;
  template: MappingTemplateDTO;
}

export const mappingClient = {
  async compileMapping(selectedScope: any, routingDefinition: RoutingDefinitionDTO): Promise<CompileMappingResponseDTO> {
    const raw = await ipcService.invokeEngineCapability(
      'p5_compile_mapping',
      JSON.stringify({ selected_scope: selectedScope, routing_definition: routingDefinition })
    );
    return typeof raw === 'string' ? JSON.parse(raw) : raw;
  },

  async validateMapping(selectedScope: any, routingDefinition: RoutingDefinitionDTO): Promise<ValidateMappingResponseDTO> {
    const raw = await ipcService.invokeEngineCapability(
      'p5_validate_mapping',
      JSON.stringify({ selected_scope: selectedScope, routing_definition: routingDefinition })
    );
    return typeof raw === 'string' ? JSON.parse(raw) : raw;
  },

  async previewMapping(objectId: string, sourceRows: any[], compiledMapping: CompiledMappingDTO): Promise<PreviewMappingResponseDTO> {
    const raw = await ipcService.invokeEngineCapability(
      'p5_preview_mapping',
      JSON.stringify({ object_id: objectId, source_rows: sourceRows, compiled_mapping: compiledMapping })
    );
    return typeof raw === 'string' ? JSON.parse(raw) : raw;
  },

  async exportTemplate(routingDefinition: RoutingDefinitionDTO, name: string = 'Standard Mapping Template'): Promise<ExportTemplateResponseDTO> {
    const raw = await ipcService.invokeEngineCapability(
      'p5_export_mapping_template',
      JSON.stringify({ routing_definition: routingDefinition, name })
    );
    return typeof raw === 'string' ? JSON.parse(raw) : raw;
  },

  async importTemplate(template: MappingTemplateDTO, selectedScope: any): Promise<CompileMappingResponseDTO> {
    const raw = await ipcService.invokeEngineCapability(
      'p5_import_mapping_template',
      JSON.stringify({ template, selected_scope: selectedScope })
    );
    return typeof raw === 'string' ? JSON.parse(raw) : raw;
  },
};
