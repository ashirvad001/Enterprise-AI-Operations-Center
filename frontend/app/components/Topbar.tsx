'use client';

import { useState, useEffect } from 'react';
import { usePathname } from 'next/navigation';

const PAGE_TITLES: Record<string, { title: string; sub: string }> = {
  '/':           { title: 'Dashboard',          sub: 'System overview and live metrics' },
  '/agents':     { title: 'Agent Orchestration', sub: 'LangGraph pipelines and workflow management' },
  '/knowledge':  { title: 'Knowledge Base',     sub: 'RAG documents, RBAC, and vector store' },
  '/voice':      { title: 'Voice Agent',        sub: 'Real-time STT → intent → TTS pipeline' },
  '/multimodal': { title: 'Multimodal',         sub: 'PDF, image, and chart processing' },
  '/mlops':      { title: 'MLOps Registry',     sub: 'Model registry, cost tracking, and RAGAS metrics' },
  '/edge':       { title: 'Edge Devices',       sub: 'Quantized LLM deployment and benchmark results' },
};

export function Topbar() {
  const pathname = usePathname();
  const [time, setTime] = useState('');

  const route = Object.keys(PAGE_TITLES)
    .filter((k) => k !== '/')
    .find((k) => pathname.startsWith(k)) ?? '/';
  const { title, sub } = PAGE_TITLES[route] ?? PAGE_TITLES['/'];

  useEffect(() => {
    const update = () => setTime(new Date().toLocaleTimeString('en-US', { hour12: false }));
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="topbar" style={{ marginLeft: 'var(--sidebar-width)' }}>
      <div>
        <div className="topbar-title">{title}</div>
        <div className="topbar-subtitle">{sub}</div>
      </div>

      <div className="topbar-spacer" />

      {/* Search */}
      <div className="input-search" style={{ width: '220px' }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: 'var(--text-muted)', flexShrink: 0 }}>
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        <input placeholder="Search..." />
        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', background: 'var(--bg-base)', padding: '2px 6px', borderRadius: '4px', border: '1px solid var(--border-subtle)', flexShrink: 0 }}>⌘K</span>
      </div>

      {/* Alerts bell */}
      <button className="btn btn-icon btn-ghost" style={{ position: 'relative' }} aria-label="Notifications">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>
        </svg>
        <span style={{
          position: 'absolute', top: '6px', right: '6px',
          width: '8px', height: '8px', borderRadius: '50%',
          background: 'var(--rose)', border: '2px solid var(--bg-base)',
        }} />
      </button>

      {/* Live clock */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '8px',
        padding: '7px 14px', borderRadius: 'var(--radius-md)',
        background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)',
        fontSize: '0.78rem', fontFamily: 'JetBrains Mono, monospace',
        color: 'var(--text-secondary)',
      }}>
        <span className="status-dot online" />
        {time || '––:––:––'}
      </div>

      {/* Environment badge */}
      <div className="badge badge-emerald">Production</div>
    </header>
  );
}
