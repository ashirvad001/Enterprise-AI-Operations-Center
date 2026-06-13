'use client';

import { useState, useEffect } from 'react';

type CostRecord = { time: string; model: string; endpoint: string; tokensIn: number; tokensOut: number; cost: number; latency: number; };

const MOCK_RECORDS: CostRecord[] = [
  { time: '19:04:21', model: 'gpt-4o-mini',   endpoint: '/api/v1/agents', tokensIn: 512,  tokensOut: 128, cost: 0.00015, latency: 410 },
  { time: '19:04:18', model: 'llama3:8b',      endpoint: '/api/v1/voice',  tokensIn: 256,  tokensOut: 64,  cost: 0.0,    latency: 820 },
  { time: '19:04:12', model: 'gpt-4o-mini',   endpoint: '/api/v1/rag',    tokensIn: 1024, tokensOut: 256, cost: 0.00032, latency: 320 },
  { time: '19:03:58', model: 'gpt-4o',         endpoint: '/api/v1/multimodal', tokensIn: 2048, tokensOut: 512, cost: 0.0179, latency: 1240 },
  { time: '19:03:45', model: 'llama3:8b',      endpoint: '/api/v1/text',   tokensIn: 384,  tokensOut: 96,  cost: 0.0,    latency: 650 },
  { time: '19:03:31', model: 'gpt-4o-mini',   endpoint: '/api/v1/agents', tokensIn: 768,  tokensOut: 192, cost: 0.00023, latency: 380 },
];

const RAGAS_HISTORY = [
  { date: '2026-06-07', faithfulness: 0.79, relevancy: 0.76, precision: 0.73, recall: 0.71, overall: 0.748 },
  { date: '2026-06-08', faithfulness: 0.82, relevancy: 0.78, precision: 0.77, recall: 0.74, overall: 0.778 },
  { date: '2026-06-09', faithfulness: 0.83, relevancy: 0.79, precision: 0.79, recall: 0.76, overall: 0.793 },
  { date: '2026-06-10', faithfulness: 0.85, relevancy: 0.80, precision: 0.81, recall: 0.77, overall: 0.808 },
  { date: '2026-06-11', faithfulness: 0.86, relevancy: 0.81, precision: 0.83, recall: 0.78, overall: 0.820 },
  { date: '2026-06-12', faithfulness: 0.87, relevancy: 0.81, precision: 0.84, recall: 0.79, overall: 0.828 },
  { date: '2026-06-13', faithfulness: 0.87, relevancy: 0.82, precision: 0.84, recall: 0.79, overall: 0.830 },
];

export default function MLOpsPage() {
  const [tab, setTab] = useState<'cost' | 'ragas' | 'audit'>('cost');
  const [totalCost, setTotalCost] = useState(0.089);

  useEffect(() => {
    const id = setInterval(() => setTotalCost(c => +(c + 0.0002).toFixed(4)), 5000);
    return () => clearInterval(id);
  }, []);

  const AUDIT_LOG = [
    { ts: '19:04:21', type: 'access',    user: 'usr-1', endpoint: '/api/v1/rag', status: 200, ms: 310, ip: '10.0.1.12', sev: 'info' },
    { ts: '19:03:58', type: 'rbac_violation', user: 'usr-2891', endpoint: '/api/v1/rag', status: 403, ms: 18, ip: '10.0.2.44', sev: 'critical' },
    { ts: '19:03:45', type: 'access',    user: 'usr-7', endpoint: '/api/v1/agents', status: 200, ms: 410, ip: '10.0.1.9', sev: 'info' },
    { ts: '19:03:12', type: 'auth',      user: 'usr-14', endpoint: '/auth/login', status: 200, ms: 42, ip: '10.0.3.21', sev: 'info' },
    { ts: '19:02:58', type: 'agent_exec', user: 'usr-1', endpoint: '/api/v1/issues/review', status: 200, ms: 98000, ip: '10.0.1.12', sev: 'info' },
    { ts: '19:02:31', type: 'auth',      user: 'usr-99', endpoint: '/auth/login', status: 401, ms: 28, ip: '10.99.0.1', sev: 'warning' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title"><span className="text-gradient">MLOps</span> Registry</h1>
          <p className="page-sub">Cost tracking, RAGAS evaluation history, and security audit logs.</p>
        </div>
      </div>

      {/* KPI */}
      <div className="grid-4 animate-fade-up">
        {[
          { label: 'Cost Today', value: `$${totalCost.toFixed(3)}`, badge: 'badge-emerald', bt: '/ $0.10 budget' },
          { label: 'Queries Today', value: '1,247', badge: 'badge-blue', bt: '98% success' },
          { label: 'RAGAS Overall', value: '83.0%', badge: 'badge-violet', bt: '+4.2% vs baseline' },
          { label: 'Audit Events', value: '6', badge: 'badge-rose', bt: '1 critical violation' },
        ].map((s, i) => (
          <div key={i} className="glass-card stat-card animate-fade-up" style={{ animationDelay: `${i * 0.05}s` }}>
            <div className="stat-label">{s.label}</div>
            <div className="stat-value">{s.value}</div>
            <div className={`badge ${s.badge}`}>{s.bt}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="tabs" style={{ width: 'fit-content' }}>
        {(['cost', 'ragas', 'audit'] as const).map(t => (
          <button key={t} className={`tab-item ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {t === 'cost' ? '💰 Cost Tracker' : t === 'ragas' ? '📊 RAGAS History' : '🔒 Audit Log'}
          </button>
        ))}
      </div>

      {/* Cost tracker */}
      {tab === 'cost' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }} className="animate-fade-in">
          {/* Cost by model */}
          <div className="grid-2">
            <div className="glass-card">
              <div className="card-header"><div className="card-title">Cost by Model</div></div>
              <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {[
                  { model: 'gpt-4o',      cost: 0.0358, pct: 40, color: 'var(--blue)' },
                  { model: 'gpt-4o-mini', cost: 0.0142, pct: 16, color: 'var(--violet)' },
                  { model: 'llama3:8b',   cost: 0.0,    pct: 0,  color: 'var(--emerald)', note: '$0 (local)' },
                  { model: 'mistral:7b',  cost: 0.0,    pct: 0,  color: 'var(--cyan)', note: '$0 (local)' },
                ].map(m => (
                  <div key={m.model}>
                    <div className="flex items-center justify-between" style={{ marginBottom: '5px', fontSize: '0.82rem' }}>
                      <span style={{ fontFamily: 'JetBrains Mono', color: 'var(--text-secondary)' }}>{m.model}</span>
                      <span style={{ fontWeight: 700, color: m.color }}>
                        {m.note ? <span className="badge badge-emerald">{m.note}</span> : `$${m.cost.toFixed(4)}`}
                      </span>
                    </div>
                    {m.pct > 0 && (
                      <div className="progress-track">
                        <div className="progress-fill" style={{ width: `${m.pct}%`, background: m.color }} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
            <div className="glass-card">
              <div className="card-header"><div className="card-title">Cost by Endpoint</div></div>
              <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {[
                  { ep: '/api/v1/multimodal', cost: 0.0358, pct: 80, color: 'var(--amber)' },
                  { ep: '/api/v1/agents',     cost: 0.0142, pct: 32, color: 'var(--blue)' },
                  { ep: '/api/v1/rag',        cost: 0.0038, pct: 9,  color: 'var(--violet)' },
                  { ep: '/api/v1/voice',      cost: 0.0,    pct: 0,  color: 'var(--emerald)', note: '$0' },
                ].map(e => (
                  <div key={e.ep}>
                    <div className="flex items-center justify-between" style={{ marginBottom: '5px', fontSize: '0.82rem' }}>
                      <span style={{ fontFamily: 'JetBrains Mono', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>{e.ep}</span>
                      <span style={{ fontWeight: 700, color: e.color }}>
                        {e.note ? <span className="badge badge-emerald">{e.note}</span> : `$${e.cost.toFixed(4)}`}
                      </span>
                    </div>
                    {e.pct > 0 && (
                      <div className="progress-track">
                        <div className="progress-fill" style={{ width: `${e.pct}%`, background: e.color }} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Usage log */}
          <div className="glass-card">
            <div className="card-header"><div className="card-title">Token Usage Log</div><div className="card-subtitle">Live cost tracking (threshold: $0.10 / query)</div></div>
            <div className="card-body" style={{ padding: 0 }}>
              <table className="data-table">
                <thead><tr><th>Time</th><th>Model</th><th>Endpoint</th><th>Tokens In</th><th>Tokens Out</th><th>Cost</th><th>Latency</th></tr></thead>
                <tbody>
                  {MOCK_RECORDS.map((r, i) => (
                    <tr key={i}>
                      <td className="font-mono text-xs">{r.time}</td>
                      <td><span className={`badge ${r.model.startsWith('gpt') ? 'badge-blue' : 'badge-emerald'}`}>{r.model}</span></td>
                      <td className="font-mono text-xs">{r.endpoint}</td>
                      <td className="font-mono text-sm">{r.tokensIn.toLocaleString()}</td>
                      <td className="font-mono text-sm">{r.tokensOut.toLocaleString()}</td>
                      <td className="font-mono text-sm" style={{ color: r.cost === 0 ? 'var(--emerald)' : r.cost > 0.01 ? 'var(--amber)' : 'var(--text-secondary)' }}>
                        {r.cost === 0 ? '$0.00 ✓' : `$${r.cost.toFixed(5)}`}
                      </td>
                      <td className="font-mono text-sm">{r.latency}ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* RAGAS history */}
      {tab === 'ragas' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }} className="animate-fade-in">
          <div className="glass-card">
            <div className="card-header">
              <div><div className="card-title">RAGAS Score Trend (7 days)</div><div className="card-subtitle">20 queries evaluated per night</div></div>
              <span className="badge badge-emerald">↑ +8.2% in 7 days</span>
            </div>
            <div className="card-body" style={{ padding: 0 }}>
              <table className="data-table">
                <thead><tr><th>Date</th><th>Faithfulness</th><th>Relevancy</th><th>Ctx. Precision</th><th>Ctx. Recall</th><th>Overall</th><th>vs Target</th></tr></thead>
                <tbody>
                  {RAGAS_HISTORY.map(r => (
                    <tr key={r.date}>
                      <td className="font-mono text-sm">{r.date}</td>
                      {[r.faithfulness, r.relevancy, r.precision, r.recall].map((v, i) => (
                        <td key={i} style={{ fontWeight: 600, color: v >= 0.80 ? 'var(--emerald)' : 'var(--amber)' }}>
                          {(v * 100).toFixed(0)}%
                        </td>
                      ))}
                      <td><strong style={{ color: r.overall >= 0.80 ? 'var(--emerald)' : 'var(--amber)' }}>{(r.overall * 100).toFixed(1)}%</strong></td>
                      <td>
                        <span className={`badge ${r.overall >= 0.80 ? 'badge-emerald' : 'badge-amber'}`}>
                          {r.overall >= 0.80 ? '✓ Met' : '✗ Miss'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Audit log */}
      {tab === 'audit' && (
        <div className="glass-card animate-fade-in">
          <div className="card-header">
            <div><div className="card-title">Security Audit Log</div><div className="card-subtitle">Structured JSON events — RBAC violations at CRITICAL severity</div></div>
            <span className="badge badge-rose">1 Critical</span>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <table className="data-table">
              <thead><tr><th>Timestamp</th><th>Type</th><th>User</th><th>Endpoint</th><th>Status</th><th>Latency</th><th>IP</th><th>Severity</th></tr></thead>
              <tbody>
                {AUDIT_LOG.map((e, i) => (
                  <tr key={i}>
                    <td className="font-mono text-xs">{e.ts}</td>
                    <td><span className={`badge ${e.type === 'rbac_violation' ? 'badge-rose' : e.type === 'auth' ? 'badge-amber' : 'badge-blue'}`}>{e.type}</span></td>
                    <td className="font-mono text-sm">{e.user}</td>
                    <td className="font-mono text-xs">{e.endpoint}</td>
                    <td className="font-mono text-sm" style={{ color: e.status < 400 ? 'var(--emerald)' : 'var(--rose)' }}>{e.status}</td>
                    <td className="font-mono text-sm">{e.ms > 1000 ? `${(e.ms/1000).toFixed(1)}s` : `${e.ms}ms`}</td>
                    <td className="font-mono text-xs text-muted">{e.ip}</td>
                    <td>
                      <span className={`badge ${e.sev === 'critical' ? 'badge-rose' : e.sev === 'warning' ? 'badge-amber' : 'badge-emerald'}`}>
                        {e.sev.toUpperCase()}
                      </span>
                    </td>
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
