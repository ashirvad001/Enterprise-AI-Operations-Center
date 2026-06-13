'use client';

import { useState, useEffect } from 'react';
import { StatCard } from './components/Card';
import { Button } from './components/Button';

// ── Simulated live data ────────────────────────────────────────────────
const EXEC_ROWS = [
  { id: 'exec-8f2a', agent: 'Code Reviewer', issue: 'GH-142: SQL injection fix', status: 'running',   dur: '1m 12s', cost: '$0.003', tokens: '4.2K' },
  { id: 'exec-9b1c', agent: 'Support Triage', issue: 'TICKET-881: Refund request', status: 'completed', dur: '48s',    cost: '$0.001', tokens: '1.8K' },
  { id: 'exec-4e7d', agent: 'Data Analyst',   issue: 'RPT-29: Q3 revenue analysis', status: 'completed', dur: '2m 3s',  cost: '$0.007', tokens: '9.1K' },
  { id: 'exec-2a9f', agent: 'RAG Q&A',        issue: 'Query: RBAC policy for lawyers', status: 'running',   dur: '22s',   cost: '$0.002', tokens: '2.4K' },
  { id: 'exec-7c1e', agent: 'Code Reviewer',  issue: 'GH-143: Hardcoded secret', status: 'failed',    dur: '55s',   cost: '$0.002', tokens: '3.1K' },
];

const ALERTS = [
  { type: 'critical', title: 'RBAC Violation Detected', body: 'User uid-2891 attempted access to restricted medical record (doc-med-443)', time: '2m ago' },
  { type: 'warning',  title: 'High Token Cost',         body: 'Agent "Data Analyst" exceeded budget: $0.07 / $0.10 (70%)', time: '15m ago' },
  { type: 'warning',  title: 'Edge Node Degraded',      body: 'Pi5-node-07 latency spiked to 2.8s (target: <2s)', time: '34m ago' },
  { type: 'info',     title: 'Model Pulled Successfully', body: 'llama3:8b Q4_K_M loaded on edge cluster (3 nodes)', time: '1h ago' },
];

const SPARKLINE_TOKENS = [28, 35, 42, 38, 51, 46, 62, 58, 71, 67, 80, 74];
const SPARKLINE_EXEC   = [4, 6, 5, 8, 7, 9, 11, 10, 13, 12, 14, 16];
const SPARKLINE_COST   = [0.8, 1.2, 0.9, 1.5, 1.1, 1.8, 1.4, 2.1, 1.7, 2.4, 1.9, 2.8];

const STATUS_COLOR: Record<string, string> = {
  running:   'var(--blue)',
  completed: 'var(--emerald)',
  failed:    'var(--rose)',
};

// RAGAS bar chart data
const RAGAS_METRICS = [
  { label: 'Faithfulness',     score: 87, color: '#10b981' },
  { label: 'Ans. Relevancy',  score: 81, color: '#3b82f6' },
  { label: 'Ctx. Precision',  score: 84, color: '#8b5cf6' },
  { label: 'Ctx. Recall',     score: 79, color: '#06b6d4' },
];

// Ring chart
function RingChart({ value, max, label, color }: { value: number; max: number; label: string; color: string }) {
  const r = 42; const circ = 2 * Math.PI * r;
  const fill = circ - (circ * value) / max;
  return (
    <div className="ring-chart" style={{ width: 108, height: 108 }}>
      <svg width="108" height="108" viewBox="0 0 108 108">
        <circle className="ring-track" cx="54" cy="54" r={r} strokeWidth="9" />
        <circle className="ring-fill" cx="54" cy="54" r={r} strokeWidth="9"
          stroke={color} strokeDasharray={circ}
          strokeDashoffset={fill}
          style={{ transition: 'stroke-dashoffset 1.2s cubic-bezier(0.4,0,0.2,1)' }}
        />
      </svg>
      <div className="ring-label">
        <div style={{ fontSize: '1.4rem', fontWeight: 800, color }}>{value}</div>
        <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', maxWidth: 64, textAlign: 'center', lineHeight: 1.2 }}>{label}</div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 4000);
    return () => clearInterval(id);
  }, []);

  const liveTokens = (4.2 + (tick * 0.03)).toFixed(1);
  const liveWorkflows = 14 + (tick % 3);
  const liveCost = (0.089 + tick * 0.002).toFixed(3);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Welcome back, <span className="text-gradient">Admin</span></h1>
          <p className="page-sub">Here&apos;s what&apos;s happening across your AI infrastructure today.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm">↓ Export Report</Button>
          <Button variant="primary">+ Deploy Agent</Button>
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid-4 animate-fade-up">
        <StatCard
          label="Active Workflows"
          value={liveWorkflows}
          delta="+2 today" deltaType="up"
          sparkline={SPARKLINE_EXEC}
          icon={<span style={{ fontSize: '18px' }}>◈</span>}
          iconBg="rgba(59,130,246,0.15)"
        />
        <StatCard
          label="Token Usage (24h)"
          value={`${liveTokens}M`}
          delta="+15% vs yesterday" deltaType="neutral"
          sparkline={SPARKLINE_TOKENS}
          icon={<span style={{ fontSize: '18px' }}>◉</span>}
          iconBg="rgba(245,158,11,0.15)"
        />
        <StatCard
          label="Cost Today"
          value={`$${liveCost}`}
          delta="$0.10 budget" deltaType="up"
          sparkline={SPARKLINE_COST}
          icon={<span style={{ fontSize: '18px' }}>◆</span>}
          iconBg="rgba(16,185,129,0.12)"
        />
        <StatCard
          label="Online Edge Nodes"
          value="128 / 130"
          delta="2 degraded" deltaType="down"
          icon={<span style={{ fontSize: '18px' }}>◌</span>}
          iconBg="rgba(139,92,246,0.15)"
        />
      </div>

      {/* Middle row: executions + alerts */}
      <div className="grid-2-1 animate-fade-up delay-1">

        {/* Recent Executions */}
        <div className="glass-card">
          <div className="card-header">
            <div>
              <div className="card-title">Recent Agent Executions</div>
              <div className="card-subtitle">Live pipeline activity</div>
            </div>
            <Button variant="ghost" size="sm">View all →</Button>
          </div>
          <div className="card-body" style={{ padding: '0 0 8px' }}>
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Agent</th>
                    <th>Issue</th>
                    <th>Status</th>
                    <th>Tokens</th>
                    <th>Cost</th>
                    <th>Duration</th>
                  </tr>
                </thead>
                <tbody>
                  {EXEC_ROWS.map((row) => (
                    <tr key={row.id}>
                      <td>
                        <div style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{row.agent}</div>
                        <div className="text-xs text-muted font-mono">{row.id}</div>
                      </td>
                      <td style={{ maxWidth: 200 }}>
                        <div className="truncate text-sm" style={{ maxWidth: 190 }}>{row.issue}</div>
                      </td>
                      <td>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.82rem', fontWeight: 600, color: STATUS_COLOR[row.status] }}>
                          <span className={`status-dot ${row.status}`} />
                          {row.status.charAt(0).toUpperCase() + row.status.slice(1)}
                        </span>
                      </td>
                      <td className="font-mono text-sm">{row.tokens}</td>
                      <td className="font-mono text-sm">{row.cost}</td>
                      <td className="font-mono text-sm">{row.dur}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Alerts */}
        <div className="glass-card">
          <div className="card-header">
            <div>
              <div className="card-title">System Alerts</div>
              <div className="card-subtitle">Last 2 hours</div>
            </div>
            <span className="badge badge-rose">{ALERTS.length}</span>
          </div>
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {ALERTS.map((a, i) => (
              <div key={i} className={`alert alert-${a.type === 'critical' ? 'critical' : a.type === 'warning' ? 'warning' : a.type === 'info' ? 'info' : 'success'}`}>
                <div style={{ flex: 1 }}>
                  <div className="alert-title">{a.title}</div>
                  <div className="alert-body">{a.body}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '4px' }}>{a.time}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom row: RAGAS + Platform health */}
      <div className="grid-2 animate-fade-up delay-2">

        {/* RAGAS Metrics */}
        <div className="glass-card">
          <div className="card-header">
            <div>
              <div className="card-title">RAGAS Evaluation Scores</div>
              <div className="card-subtitle">Last nightly run · 20 queries evaluated</div>
            </div>
            <span className="badge badge-emerald">↑ +4.2% vs baseline</span>
          </div>
          <div className="card-body">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {RAGAS_METRICS.map((m) => (
                <div key={m.label}>
                  <div className="flex items-center justify-between" style={{ marginBottom: '6px' }}>
                    <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{m.label}</span>
                    <span style={{ fontSize: '0.875rem', fontWeight: 700, color: m.color }}>{m.score}%</span>
                  </div>
                  <div className="progress-track">
                    <div className="progress-fill" style={{ width: `${m.score}%`, background: m.color, boxShadow: `0 0 8px ${m.color}50` }} />
                  </div>
                </div>
              ))}
              <div className="divider" style={{ margin: '4px 0' }} />
              <div className="flex items-center gap-4" style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                <span>Overall: <strong style={{ color: 'var(--emerald)' }}>82.75%</strong></span>
                <span>Target: <strong style={{ color: 'var(--text-secondary)' }}>80%</strong></span>
                <span className="badge badge-emerald" style={{ marginLeft: 'auto' }}>✓ Target Met</span>
              </div>
            </div>
          </div>
        </div>

        {/* Platform Health */}
        <div className="glass-card">
          <div className="card-header">
            <div className="card-title">Platform Health</div>
            <div className="card-subtitle">All services · Real-time</div>
          </div>
          <div className="card-body">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', justifyItems: 'center' }}>
              <div style={{ textAlign: 'center' }}>
                <RingChart value={99} max={100} label="Agent Engine" color="#10b981" />
              </div>
              <div style={{ textAlign: 'center' }}>
                <RingChart value={84} max={100} label="RAG Context Precision" color="#3b82f6" />
              </div>
              <div style={{ textAlign: 'center' }}>
                <RingChart value={45} max={60}  label="Edge TPS (Pi 5)" color="#8b5cf6" />
              </div>
            </div>
            <div className="divider" style={{ margin: '16px 0' }} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {[
                { name: 'Agent Engine', status: 'online', latency: '42ms', uptime: '99.97%' },
                { name: 'RAG Service', status: 'online', latency: '310ms', uptime: '99.91%' },
                { name: 'Voice Service', status: 'online', latency: '1.8s', uptime: '99.85%' },
                { name: 'Edge Manager', status: 'online', latency: '28ms', uptime: '99.99%' },
              ].map((svc) => (
                <div key={svc.name} className="flex items-center" style={{ fontSize: '0.83rem' }}>
                  <span className={`status-dot ${svc.status}`} style={{ marginRight: '8px' }} />
                  <span style={{ flex: 1, color: 'var(--text-secondary)' }}>{svc.name}</span>
                  <span className="font-mono text-xs text-muted" style={{ marginRight: '16px' }}>{svc.latency}</span>
                  <span className="badge badge-emerald">{svc.uptime}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

    </div>
  );
}
