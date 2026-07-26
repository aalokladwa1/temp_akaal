'use client';

import React, { useState } from 'react';

export interface SchemaObject {
  id: string;
  name: string;
  schema: string;
  type: 'table' | 'view' | 'procedure' | 'function' | 'sequence' | 'index' | 'trigger' | 'constraint';
  rowCount?: number;
  sizeBytes?: number;
  columnsCount?: number;
  selected: boolean;
}

export function SchemaExplorer({
  objects,
  onToggleSelect,
  onToggleSelectAll,
  onInspectObject,
}: {
  objects: SchemaObject[];
  onToggleSelect: (id: string) => void;
  onToggleSelectAll: (select: boolean) => void;
  onInspectObject?: (obj: SchemaObject) => void;
}) {
  const [search, setSearch] = useState('');
  const [activeType, setActiveType] = useState<string>('all');
  const [collapsedSchemas, setCollapsedSchemas] = useState<Set<string>>(new Set());

  const filtered = objects.filter(obj => {
    if (activeType !== 'all' && obj.type !== activeType) return false;
    if (search && !obj.name.toLowerCase().includes(search.toLowerCase()) && !obj.schema.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const schemas = Array.from(new Set(filtered.map(o => o.schema)));
  const allSelected = filtered.length > 0 && filtered.every(o => o.selected);

  const toggleSchemaCollapse = (schema: string) => {
    setCollapsedSchemas(prev => {
      const next = new Set(prev);
      if (next.has(schema)) next.delete(schema);
      else next.add(schema);
      return next;
    });
  };

  const getIconForType = (type: SchemaObject['type']) => {
    switch (type) {
      case 'table': return <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><rect x="1.5" y="2" width="9" height="8" rx="1" stroke="#38BDF8" strokeWidth="1.2" /><path d="M1.5 5h9M5 5v5" stroke="#38BDF8" strokeWidth="1.2" /></svg>;
      case 'view': return <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><circle cx="6" cy="6" r="4" stroke="#A855F7" strokeWidth="1.2" /><path d="M6 3.5v5" stroke="#A855F7" strokeWidth="1.2" /></svg>;
      case 'procedure':
      case 'function': return <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2.5 3.5l3.5 2.5-3.5 2.5M6.5 8.5h3" stroke="#F59E0B" strokeWidth="1.2" strokeLinecap="round" /></svg>;
      case 'sequence': return <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2 9l3-6 3 3 2-2" stroke="#22C55E" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg>;
      default: return <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><circle cx="6" cy="6" r="3.5" stroke="#94A3B8" strokeWidth="1.2" /></svg>;
    }
  };

  return (
    <div className="flex flex-col h-full rounded-lg overflow-hidden border" style={{ background: 'var(--akaal-surface, #141E2E)', borderColor: 'var(--akaal-border, #2A3647)' }}>
      {/* Toolbar */}
      <div className="p-3 border-b flex flex-wrap items-center justify-between gap-3" style={{ borderColor: 'var(--akaal-border, #2A3647)', background: 'var(--akaal-sidebar-bg, #0D1520)' }}>
        <div className="flex items-center gap-2 flex-1 min-w-[200px]">
          <input
            type="search"
            placeholder="Search schema objects (tables, views, functions)…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full text-xs rounded px-2.5 py-1.5 outline-none"
            style={{ background: 'var(--akaal-input-bg, #111827)', border: '1px solid var(--akaal-border, #2A3647)', color: 'var(--akaal-text, #F8FAFC)', fontFamily: "'Inter', sans-serif" }}
          />
        </div>

        {/* Type Filter Pills */}
        <div className="flex items-center gap-1 overflow-x-auto">
          {['all', 'table', 'view', 'procedure', 'sequence'].map(type => (
            <button
              key={type}
              type="button"
              onClick={() => setActiveType(type)}
              className="px-2 py-1 rounded text-xs capitalize transition-colors font-medium"
              style={{
                background: activeType === type ? 'var(--akaal-primary, #2563EB)' : 'transparent',
                color: activeType === type ? '#fff' : 'var(--akaal-text-muted, #94A3B8)',
                fontFamily: "'Inter', sans-serif",
                fontSize: '11px',
              }}
            >
              {type === 'all' ? 'All Objects' : `${type}s`}
            </button>
          ))}
        </div>
      </div>

      {/* Select All Bar */}
      <div className="px-4 py-2 border-b flex items-center justify-between" style={{ borderColor: 'var(--akaal-border, #2A3647)', background: 'rgba(255,255,255,0.02)' }}>
        <label className="flex items-center gap-2 text-xs font-medium cursor-pointer" style={{ color: 'var(--akaal-text-secondary, #CBD5E1)', fontFamily: "'Inter', sans-serif" }}>
          <input
            type="checkbox"
            checked={allSelected}
            onChange={e => onToggleSelectAll(e.target.checked)}
            className="rounded"
            style={{ accentColor: 'var(--akaal-primary, #2563EB)' }}
          />
          <span>Select All Filtered ({filtered.filter(o => o.selected).length}/{filtered.length})</span>
        </label>
        <span className="text-xs font-mono" style={{ color: 'var(--akaal-text-muted, #64748B)', fontSize: '10px' }}>
          {schemas.length} Schema{schemas.length !== 1 ? 's' : ''} Discovered
        </span>
      </div>

      {/* Tree Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3 custom-scrollbar">
        {schemas.map(schema => {
          const schemaObjects = filtered.filter(o => o.schema === schema);
          const isCollapsed = collapsedSchemas.has(schema);
          return (
            <div key={schema} className="rounded border" style={{ borderColor: 'var(--akaal-border, #2A3647)', background: 'rgba(0,0,0,0.1)' }}>
              <button
                type="button"
                onClick={() => toggleSchemaCollapse(schema)}
                className="w-full flex items-center justify-between px-3 py-2 text-left font-medium text-xs hover:bg-white/5 transition-colors"
                style={{ color: 'var(--akaal-text, #F8FAFC)', fontFamily: "'Inter', sans-serif" }}
              >
                <div className="flex items-center gap-2">
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none" style={{ transform: isCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)', transition: 'transform 0.15s' }}>
                    <path d="M2.5 3.5l2.5 2.5 2.5-2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
                  </svg>
                  <span className="font-semibold">{schema}</span>
                  <span className="text-xs px-1.5 py-0.2 rounded font-mono" style={{ background: 'rgba(255,255,255,0.06)', color: 'var(--akaal-text-muted, #64748B)', fontSize: '10px' }}>
                    {schemaObjects.length}
                  </span>
                </div>
              </button>

              {!isCollapsed && (
                <div className="p-2 space-y-1 border-t" style={{ borderColor: 'var(--akaal-border, #2A3647)' }}>
                  {schemaObjects.map(obj => (
                    <div
                      key={obj.id}
                      className="flex items-center justify-between px-2.5 py-1.5 rounded hover:bg-white/5 transition-colors text-xs"
                    >
                      <label className="flex items-center gap-2.5 min-w-0 cursor-pointer flex-1">
                        <input
                          type="checkbox"
                          checked={obj.selected}
                          onChange={() => onToggleSelect(obj.id)}
                          className="rounded"
                          style={{ accentColor: 'var(--akaal-primary, #2563EB)' }}
                        />
                        <span className="flex-shrink-0">{getIconForType(obj.type)}</span>
                        <span className="truncate font-mono" style={{ color: 'var(--akaal-text-secondary, #CBD5E1)', fontSize: '11px' }}>
                          {obj.name}
                        </span>
                      </label>

                      <div className="flex items-center gap-3 font-mono text-[10px]" style={{ color: 'var(--akaal-text-muted, #64748B)' }}>
                        {obj.rowCount !== undefined && (
                          <span>{obj.rowCount.toLocaleString()} rows</span>
                        )}
                        {onInspectObject && (
                          <button
                            type="button"
                            onClick={() => onInspectObject(obj)}
                            className="px-1.5 py-0.5 rounded text-[10px] hover:bg-white/10 hover:text-white transition-colors"
                          >
                            Inspect
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
