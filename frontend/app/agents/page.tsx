'use client';

import { useState } from 'react';
import { Button } from '../components/Button';
import { Card } from '../components/Card';

const WORKFLOWS = [
  { id: 'wf-001', name: 'Code Review Pipeline', status: 'running', nodes: 5, runs: 24, lastRun: '2m ago',  avgDur: '1m 48s', success: 92, desc: 'planner → coder → security_reviewer → tester → create_pr' },
  { id: 'wf-002', name: 'Support Triage Agent', status: 'completed', nodes: 3, runs: 187, lastRun: '12m ago', avgDur: '38s',    success: 98, desc: 'intent_classify → entity_extract → lookup → respond' },
  { id: 'wf-003', name: 'Data Analysis Agent',  status: 'idle',    nodes: 4, runs: 12,  lastRun: '2h ago',  avgDur: '3m 12s', success: 83, desc: 'query_parse → sql_gen → execute → visualize' },
  { id: 'wf-004', name: 'RAG Q&A Workflow',     status: 'running', nodes: 4, runs: 341, lastRun: '1m ago',  avgDur: '420ms',  success: 96, desc: 'rbac_check → retrieve → rerank → generate → cite' },
];

const EXECUTION_LOG = [
  { time: '19:04:21', node: 'security_reviewer', msg: 'Found SQL injection pattern in user_search.py:L42 — routing back to coder', level: 'warn' },
  { time: '19:04:19', node: 'coder',             msg: 'Generated fix for GH-142: parameterized query with sqlalchemy.text()', level: 'info' },
  { time: '19:04:14', node: 'planner',           msg: 'Issue classified: security-critical, complexity=high, estimated=45min', level: 'info' },
  { time: '19:04:12', node: 'orchestrator',      msg: 'Workflow wf-001 started — issue GH-142 assigned to Code Review Pipeline', level: 'info' },
  { time: '19:03:58', node: 'human_checkpoint',  msg: 'Human approved PR for GH-139 — merging to main branch', level: 'success' },
  { time: '19:03:45', node: 'tester',            msg: 'Generated 8 test cases for GH-139: 3 happy path, 4 edge, 1 negative', level: 'info' },
];

const STATUS_COLOR: Record<string, string> = { running: 'blue', completed: 'emerald', idle: 'violet' };

export default function AgentsPage() {
  const [selected, setSelected] = useState<string | null>('wf-001');
  const [running, setRunning] = useState(false);

  const selectedWf = WORKFLOWS.find(w => w.id === selected);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title"><span className="text-gradient">Agent</span> Orchestration</h1>
          <p className="page-sub">LangGraph state machines — manage and monitor multi-agent workflows.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm">Import Workflow</Button>
          <Button variant="primary" onClick={() => setRunning(r => !r)}>
            {running ? '■ Stop' : '▶ New Run'}
          </Button>
        </div>
      </div>

      {/* KPI strip */}
      <div className="grid-4 animate-fade-up">
        {[
          { label: 'Active Pipelines', value: '4', badge: 'badge-blue', badgeTxt: '2 running' },
          { label: 'Total Runs (7d)', value: '564', badge: 'badge-emerald', badgeTxt: '96% success' },
          { label: 'Avg Latency', value: '1m 8s', badge: 'badge-violet', badgeTxt: 'P95: 3m 12s' },
          { label: 'Security Blocks', value: '23', badge: 'badge-amber', badgeTxt: 'vulnerabilities caught' },
        ].map((item, i) => (
          <div key={i} className="glass-card stat-card animate-fade-up" style={{ animationDelay: `${i * 0.05}s` }}>
            <div className="stat-label">{item.label}</div>
            <div className="stat-value">{item.value}</div>
            <div className={`badge ${item.badge}`}>{item.badgeTxt}</div>
          </div>
        ))}
      </div>

      {/* Main layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: '20px' }}>

        {/* Workflow list */}
        <div className="glass-card" style={{ overflow: 'hidden', height: 'fit-content' }}>
          <div className="card-header"><div className="card-title">Workflows</div></div>
          <div style={{ padding: '8px' }}>
            {WORKFLOWS.map((wf) => (
              <div
                key={wf.id}
                onClick={() => setSelected(wf.id)}
                style={{
                  padding: '14px 16px', borderRadius: 'var(--radius-md)', cursor: 'pointer',
                  background: selected === wf.id ? 'var(--bg-active)' : 'transparent',
                  border: `1px solid ${selected === wf.id ? 'var(--border-blue)' : 'transparent'}`,
                  transition: 'var(--t-fast)', marginBottom: '4px',
                }}
              >
                <div className="flex items-center justify-between" style={{ marginBottom: '6px' }}>
                  <span style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-primary)' }}>{wf.name}</span>
                  <span className={`badge badge-${STATUS_COLOR[wf.status]}`}>{wf.status}</span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {wf.nodes} nodes · {wf.runs} runs · last {wf.lastRun}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Workflow detail */}
        {selectedWf && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

            {/* Pipeline diagram */}
            <div className="glass-card">
              <div className="card-header">
                <div>
                  <div className="card-title">{selectedWf.name}</div>
                  <div className="card-subtitle">{selectedWf.desc}</div>
                </div>
                <div className="flex gap-2">
                  <span className={`badge badge-${STATUS_COLOR[selectedWf.status]}`}>{selectedWf.status}</span>
                  <Button variant="secondary" size="sm">Edit</Button>
                </div>
              </div>
              <div className="card-body">
                {/* Node pipeline display */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0', overflowX: 'auto', paddingBottom: '8px' }}>
                  {selectedWf.desc.split(' → ').map((node, i, arr) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0', flexShrink: 0 }}>
                      <div style={{
                        padding: '8px 14px', borderRadius: 'var(--radius-md)',
                        background: i === 1 && selectedWf.status === 'running'
                          ? 'rgba(59,130,246,0.2)'
                          : 'var(--bg-elevated)',
                        border: `1px solid ${i === 1 && selectedWf.status === 'running' ? 'var(--border-blue)' : 'var(--border-subtle)'}`,
                        fontSize: '0.8rem', fontFamily: 'JetBrains Mono, monospace',
                        color: i === 1 && selectedWf.status === 'running' ? 'var(--blue)' : 'var(--text-secondary)',
                        position: 'relative', whiteSpace: 'nowrap',
                      }}>
                        {i === 1 && selectedWf.status === 'running' && (
                          <span className="status-dot running" style={{ position: 'absolute', top: '-4px', right: '-4px' }} />
                        )}
                        {node}
                      </div>
                      {i < arr.length - 1 && (
                        <div style={{ width: '28px', height: '2px', background: 'var(--border-strong)', position: 'relative' }}>
                          <div style={{ position: 'absolute', right: '-4px', top: '-3px', color: 'var(--text-muted)', fontSize: '10px' }}>›</div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Metrics */}
                <div className="grid-4" style={{ marginTop: '16px', gap: '12px' }}>
                  {[
                    { l: 'Total Runs', v: String(selectedWf.runs) },
                    { l: 'Success Rate', v: `${selectedWf.success}%` },
                    { l: 'Avg Duration', v: selectedWf.avgDur },
                    { l: 'Nodes', v: String(selectedWf.nodes) },
                  ].map(({ l, v }) => (
                    <div key={l} style={{ padding: '12px 14px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '4px' }}>{l}</div>
                      <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{v}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Execution log */}
            <div className="glass-card">
              <div className="card-header">
                <div className="card-title">Live Execution Log</div>
                <div className="flex gap-2">
                  <span className="status-dot running" style={{ marginTop: '2px' }} />
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Streaming</span>
                </div>
              </div>
              <div className="card-body" style={{ padding: '8px 12px' }}>
                <div style={{ background: 'var(--bg-base)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', padding: '12px', maxHeight: '240px', overflowY: 'auto' }}>
                  {EXECUTION_LOG.map((log, i) => (
                    <div key={i} className="log-item" style={{ padding: '6px 8px' }}>
                      <span className="log-time">{log.time}</span>
                      <span style={{
                        fontSize: '0.72rem', padding: '1px 7px', borderRadius: 'var(--radius-full)',
                        background: log.level === 'warn' ? 'rgba(245,158,11,0.15)' : log.level === 'success' ? 'rgba(16,185,129,0.12)' : 'rgba(59,130,246,0.12)',
                        color: log.level === 'warn' ? 'var(--amber)' : log.level === 'success' ? 'var(--emerald)' : 'var(--blue)',
                        fontFamily: 'monospace', flexShrink: 0,
                      }}>{log.node}</span>
                      <span className="log-msg" style={{ fontSize: '0.8rem' }}>{log.msg}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

          </div>
        )}
      </div>
    </div>
  );
}
