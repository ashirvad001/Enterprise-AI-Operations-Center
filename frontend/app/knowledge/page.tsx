'use client';

import { useState } from 'react';
import { Button } from '../components/Button';

const DOCUMENTS = [
  { id: 'doc-001', name: 'Q3 Financial Report 2024.pdf',   type: 'PDF',   chunks: 142, tokens: '89K', role: 'finance',    sensitivity: 'confidential', size: '4.2MB', uploaded: '2d ago', status: 'indexed' },
  { id: 'doc-002', name: 'Employee Handbook v12.pdf',       type: 'PDF',   chunks: 87,  tokens: '52K', role: 'hr',         sensitivity: 'internal',     size: '2.1MB', uploaded: '1w ago', status: 'indexed' },
  { id: 'doc-003', name: 'Medical Claims Dataset.csv',      type: 'CSV',   chunks: 234, tokens: '145K', role: 'medical',   sensitivity: 'restricted',   size: '8.9MB', uploaded: '3d ago', status: 'indexed' },
  { id: 'doc-004', name: 'API Integration Docs.md',         type: 'MD',    chunks: 56,  tokens: '31K', role: 'engineering', sensitivity: 'internal',    size: '0.8MB', uploaded: '5h ago', status: 'indexed' },
  { id: 'doc-005', name: 'Product Roadmap Q4.pptx',        type: 'PPTX',  chunks: 38,  tokens: '22K', role: 'leadership', sensitivity: 'confidential', size: '3.4MB', uploaded: '1d ago', status: 'indexing' },
  { id: 'doc-006', name: 'Legal Contracts Archive.zip',     type: 'ZIP',   chunks: 0,   tokens: '—',   role: 'legal',      sensitivity: 'restricted',   size: '24MB', uploaded: '2h ago', status: 'queued' },
];

const SENSITIVITY_BADGE: Record<string, string> = {
  public:       'badge-emerald',
  internal:     'badge-blue',
  confidential: 'badge-amber',
  restricted:   'badge-rose',
};

const QUERY_HISTORY = [
  { query: 'What is the RBAC policy for medical records?', role: 'admin',     chunks: 4, latency: '320ms', result: 'Access granted — 4 chunks retrieved' },
  { query: 'Show Q3 revenue breakdown by region',          role: 'finance',   chunks: 7, latency: '410ms', result: 'Access granted — 7 chunks retrieved' },
  { query: 'Employee termination procedures',              role: 'engineer',  chunks: 0, latency: '18ms',  result: 'Access denied — role=engineer, required=hr' },
  { query: 'Product roadmap for Q4 2024',                  role: 'pm',        chunks: 3, latency: '285ms', result: 'Access granted — 3 chunks retrieved' },
];

export default function KnowledgePage() {
  const [query, setQuery] = useState('');
  const [role, setRole] = useState('admin');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [tab, setTab] = useState<'documents' | 'query' | 'rbac'>('documents');

  const handleQuery = () => {
    if (!query.trim()) return;
    setLoading(true);
    setResult(null);
    setTimeout(() => {
      setResult(`Retrieved 4 chunks for: "${query}". Semantic similarity: 0.847. Reranking applied. Citations: [doc-001:p12], [doc-001:p14], [doc-004:p3], [doc-004:p7]. Faithfulness: 0.91.`);
      setLoading(false);
    }, 1200);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title"><span className="text-gradient">Knowledge</span> Base</h1>
          <p className="page-sub">RAG pipeline with RBAC — hybrid BM25 + dense retrieval, cross-encoder reranking.</p>
        </div>
        <Button variant="primary">+ Upload Document</Button>
      </div>

      {/* Stats */}
      <div className="grid-4 animate-fade-up">
        {[
          { label: 'Total Documents', value: '234', delta: '+12 this week' },
          { label: 'Total Chunks',    value: '47.2K', delta: 'avg 202 / doc' },
          { label: 'Index Size',      value: '2.1GB', delta: 'pgvector' },
          { label: 'RBAC Violations', value: '3', delta: 'last 24h', alert: true },
        ].map((s, i) => (
          <div key={i} className="glass-card stat-card animate-fade-up" style={{ animationDelay: `${i * 0.05}s` }}>
            <div className="stat-label">{s.label}</div>
            <div className="stat-value">{s.value}</div>
            <div className={`stat-delta ${s.alert ? 'down' : 'up'}`}>{s.alert ? '↑' : '↑'} {s.delta}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="tabs" style={{ width: 'fit-content' }}>
        {(['documents', 'query', 'rbac'] as const).map(t => (
          <button key={t} className={`tab-item ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {t === 'documents' ? '📄 Documents' : t === 'query' ? '🔍 Query Tester' : '🔒 RBAC Policy'}
          </button>
        ))}
      </div>

      {/* Documents tab */}
      {tab === 'documents' && (
        <div className="glass-card animate-fade-in">
          <div className="card-header">
            <div className="card-title">Document Index</div>
            <div className="input-search" style={{ width: '240px' }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: 'var(--text-muted)' }}><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
              <input placeholder="Search documents..." />
            </div>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr>
                  <th>Document</th><th>Type</th><th>Chunks</th><th>Tokens</th>
                  <th>Role</th><th>Sensitivity</th><th>Size</th><th>Status</th><th></th>
                </tr></thead>
                <tbody>
                  {DOCUMENTS.map(doc => (
                    <tr key={doc.id}>
                      <td>
                        <div style={{ fontWeight: 500, fontSize: '0.875rem', color: 'var(--text-primary)' }}>{doc.name}</div>
                        <div className="text-xs text-muted">{doc.uploaded}</div>
                      </td>
                      <td><span className="badge badge-violet" style={{ fontSize: '0.68rem' }}>{doc.type}</span></td>
                      <td className="font-mono text-sm">{doc.chunks}</td>
                      <td className="font-mono text-sm">{doc.tokens}</td>
                      <td><span className="badge badge-blue">{doc.role}</span></td>
                      <td><span className={`badge ${SENSITIVITY_BADGE[doc.sensitivity]}`}>{doc.sensitivity}</span></td>
                      <td className="text-sm">{doc.size}</td>
                      <td>
                        <span className={`badge ${doc.status === 'indexed' ? 'badge-emerald' : doc.status === 'indexing' ? 'badge-blue' : 'badge-amber'}`}>
                          {doc.status}
                        </span>
                      </td>
                      <td>
                        <button className="btn btn-ghost btn-sm">···</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Query tester tab */}
      {tab === 'query' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }} className="animate-fade-in">
          <div className="glass-card">
            <div className="card-header"><div className="card-title">Interactive RAG Query Tester</div></div>
            <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Query Role (simulates RBAC)</label>
                <div className="flex gap-2">
                  {['admin', 'finance', 'engineer', 'hr', 'medical'].map(r => (
                    <button key={r} onClick={() => setRole(r)} className={`btn btn-sm ${role === r ? 'btn-primary' : 'btn-secondary'}`}>{r}</button>
                  ))}
                </div>
              </div>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Query</label>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <input
                    className="input-field"
                    placeholder="Ask a question about your documents..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleQuery()}
                  />
                  <Button variant="primary" loading={loading} onClick={handleQuery} style={{ flexShrink: 0 }}>
                    Search
                  </Button>
                </div>
              </div>
              {result && (
                <div className="alert alert-info animate-fade-in">
                  <div style={{ flex: 1 }}>
                    <div className="alert-title">RAG Response</div>
                    <div className="alert-body" style={{ marginTop: '6px', fontSize: '0.83rem', lineHeight: 1.6 }}>{result}</div>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="glass-card">
            <div className="card-header"><div className="card-title">Query History</div></div>
            <div className="card-body" style={{ padding: 0 }}>
              <table className="data-table">
                <thead><tr><th>Query</th><th>Role</th><th>Chunks</th><th>Latency</th><th>Result</th></tr></thead>
                <tbody>
                  {QUERY_HISTORY.map((q, i) => (
                    <tr key={i}>
                      <td style={{ maxWidth: 280 }}><div className="truncate text-sm">{q.query}</div></td>
                      <td><span className="badge badge-blue">{q.role}</span></td>
                      <td className="font-mono text-sm">{q.chunks}</td>
                      <td className="font-mono text-sm">{q.latency}</td>
                      <td style={{ maxWidth: 240 }}>
                        <div className={`truncate text-xs ${q.chunks === 0 ? 'text-rose' : ''}`} style={{ color: q.chunks === 0 ? 'var(--rose)' : 'var(--emerald)' }}>
                          {q.result}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* RBAC policy tab */}
      {tab === 'rbac' && (
        <div className="glass-card animate-fade-in">
          <div className="card-header"><div className="card-title">RBAC Policy Matrix</div><div className="card-subtitle">Deny-by-default · role + sensitivity enforcement</div></div>
          <div className="card-body">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Role</th>
                  <th>Public</th><th>Internal</th><th>Confidential</th><th>Restricted</th>
                  <th>Allowed Domains</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { role: 'admin',       pub: true, int: true, conf: true, rest: true, domains: 'All' },
                  { role: 'finance',     pub: true, int: true, conf: true, rest: false, domains: 'finance, reporting' },
                  { role: 'hr',          pub: true, int: true, conf: false, rest: false, domains: 'hr, employee' },
                  { role: 'engineer',    pub: true, int: true, conf: false, rest: false, domains: 'engineering, api' },
                  { role: 'medical',     pub: true, int: false, conf: false, rest: true, domains: 'medical, claims' },
                  { role: 'legal',       pub: true, int: true, conf: true, rest: true, domains: 'legal, contracts' },
                  { role: 'guest',       pub: true, int: false, conf: false, rest: false, domains: 'public only' },
                ].map(row => (
                  <tr key={row.role}>
                    <td><span className="badge badge-blue">{row.role}</span></td>
                    {[row.pub, row.int, row.conf, row.rest].map((allowed, i) => (
                      <td key={i} style={{ textAlign: 'center' }}>
                        <span style={{ fontSize: '1rem', color: allowed ? 'var(--emerald)' : 'var(--rose)' }}>
                          {allowed ? '✓' : '✕'}
                        </span>
                      </td>
                    ))}
                    <td className="text-sm text-muted">{row.domains}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
