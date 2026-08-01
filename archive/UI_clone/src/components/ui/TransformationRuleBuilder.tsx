'use client';

import React, { useState } from 'react';

export interface TransformationRule {
  id: string;
  tableName: string;
  columnName: string;
  action: 'rename' | 'mask' | 'convert_type' | 'drop' | 'custom_expr' | 'default_val';
  param: string;
  enabled: boolean;
}

export function TransformationRuleBuilder({
  rules,
  onAddRule,
  onRemoveRule,
  onToggleRule,
}: {
  rules: TransformationRule[];
  onAddRule: (rule: Omit<TransformationRule, 'id'>) => void;
  onRemoveRule: (id: string) => void;
  onToggleRule: (id: string) => void;
}) {
  const [tableName, setTableName] = useState('users');
  const [columnName, setColumnName] = useState('email');
  const [action, setAction] = useState<TransformationRule['action']>('mask');
  const [param, setParam] = useState('SHA256_SALT');

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!tableName || !columnName) return;
    onAddRule({
      tableName,
      columnName,
      action,
      param,
      enabled: true,
    });
  };

  return (
    <div className="flex flex-col gap-4 p-4 rounded-lg border" style={{ background: 'var(--akaal-surface, #141E2E)', borderColor: 'var(--akaal-border, #2A3647)' }}>
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold" style={{ color: 'var(--akaal-text, #F8FAFC)', fontFamily: "'Inter', sans-serif" }}>
            Data Transformation & Masking Rules
          </h3>
          <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted, #64748B)', fontFamily: "'Inter', sans-serif" }}>
            Configure column renaming, data redaction/hashing, type conversions, and default fallback expressions.
          </p>
        </div>
        <span className="text-xs px-2 py-0.5 rounded font-mono" style={{ background: 'rgba(37,99,235,0.15)', color: '#38BDF8', fontSize: '10px' }}>
          {rules.filter(r => r.enabled).length} Active Rule{rules.filter(r => r.enabled).length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Rule Creator Form */}
      <form onSubmit={handleCreate} className="grid grid-cols-1 sm:grid-cols-5 gap-2.5 p-3 rounded border bg-black/20" style={{ borderColor: 'var(--akaal-border, #2A3647)' }}>
        <input
          type="text"
          placeholder="Table name"
          value={tableName}
          onChange={e => setTableName(e.target.value)}
          className="text-xs px-2.5 py-1.5 rounded outline-none"
          style={{ background: 'var(--akaal-input-bg, #111827)', border: '1px solid var(--akaal-border, #2A3647)', color: 'var(--akaal-text, #F8FAFC)', fontFamily: "'Inter', sans-serif" }}
        />
        <input
          type="text"
          placeholder="Column name"
          value={columnName}
          onChange={e => setColumnName(e.target.value)}
          className="text-xs px-2.5 py-1.5 rounded outline-none"
          style={{ background: 'var(--akaal-input-bg, #111827)', border: '1px solid var(--akaal-border, #2A3647)', color: 'var(--akaal-text, #F8FAFC)', fontFamily: "'Inter', sans-serif" }}
        />
        <select
          value={action}
          onChange={e => setAction(e.target.value as any)}
          className="text-xs px-2.5 py-1.5 rounded outline-none"
          style={{ background: 'var(--akaal-input-bg, #111827)', border: '1px solid var(--akaal-border, #2A3647)', color: 'var(--akaal-text, #F8FAFC)', fontFamily: "'Inter', sans-serif" }}
        >
          <option value="mask">Mask / Hash Data</option>
          <option value="rename">Rename Column</option>
          <option value="convert_type">Convert Type</option>
          <option value="drop">Drop Column</option>
          <option value="custom_expr">Custom SQL Expression</option>
          <option value="default_val">Set Default Value</option>
        </select>
        <input
          type="text"
          placeholder="Rule parameter (e.g. SHA256, VARCHAR(255))"
          value={param}
          onChange={e => setParam(e.target.value)}
          className="text-xs px-2.5 py-1.5 rounded outline-none"
          style={{ background: 'var(--akaal-input-bg, #111827)', border: '1px solid var(--akaal-border, #2A3647)', color: 'var(--akaal-text, #F8FAFC)', fontFamily: "'Inter', sans-serif" }}
        />
        <button
          type="submit"
          className="px-3 py-1.5 rounded text-xs font-semibold transition-colors"
          style={{ background: 'var(--akaal-primary, #2563EB)', color: '#fff', fontFamily: "'Inter', sans-serif" }}
        >
          Add Rule
        </button>
      </form>

      {/* Rules List */}
      <div className="space-y-2 max-h-60 overflow-y-auto custom-scrollbar">
        {rules.length === 0 ? (
          <div className="p-4 text-center border border-dashed rounded text-xs" style={{ borderColor: 'var(--akaal-border, #2A3647)', color: 'var(--akaal-text-muted, #64748B)' }}>
            No custom transformation rules defined. Data will migrate schema-as-is.
          </div>
        ) : (
          rules.map(rule => (
            <div key={rule.id} className="flex items-center justify-between px-3 py-2 rounded border hover:bg-white/5 transition-colors text-xs" style={{ borderColor: 'var(--akaal-border, #2A3647)', background: 'rgba(255,255,255,0.02)' }}>
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={rule.enabled}
                  onChange={() => onToggleRule(rule.id)}
                  className="rounded"
                  style={{ accentColor: 'var(--akaal-primary, #2563EB)' }}
                />
                <span className="font-mono text-sky-400 font-semibold">{rule.tableName}.{rule.columnName}</span>
                <span className="px-1.5 py-0.2 rounded font-mono text-[10px] uppercase" style={{ background: 'rgba(255,255,255,0.06)', color: 'var(--akaal-text-secondary, #CBD5E1)' }}>
                  {rule.action}
                </span>
                <span className="font-mono text-[11px]" style={{ color: 'var(--akaal-text-muted, #94A3B8)' }}>
                  → {rule.param}
                </span>
              </div>

              <button
                type="button"
                onClick={() => onRemoveRule(rule.id)}
                className="text-xs px-2 py-0.5 rounded text-red-400 hover:bg-red-500/10 transition-colors"
              >
                Remove
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
