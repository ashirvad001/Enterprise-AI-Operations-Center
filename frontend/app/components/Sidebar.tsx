'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV_SECTIONS = [
  {
    label: 'Platform',
    items: [
      { href: '/', icon: '⬡', label: 'Dashboard' },
      { href: '/agents', icon: '◈', label: 'Agent Orchestration' },
      { href: '/knowledge', icon: '◉', label: 'Knowledge Base' },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      { href: '/voice', icon: '◎', label: 'Voice Agent' },
      { href: '/multimodal', icon: '◇', label: 'Multimodal' },
    ],
  },
  {
    label: 'Operations',
    items: [
      { href: '/mlops', icon: '◆', label: 'MLOps Registry' },
      { href: '/edge', icon: '◌', label: 'Edge Devices' },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar">
      <div className="sidebar-inner">
        {/* Logo */}
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">E</div>
          <div>
            <div className="sidebar-logo-text">
              <span className="text-gradient">EAIOC</span>
            </div>
            <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', marginTop: '1px', letterSpacing: '0.04em' }}>
              Enterprise AI Ops
            </div>
          </div>
        </div>

        {/* Nav */}
        {NAV_SECTIONS.map((section) => (
          <div key={section.label}>
            <div className="nav-section-label">{section.label}</div>
            {section.items.map((item) => {
              const isActive = item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`nav-item ${isActive ? 'active' : ''}`}
                >
                  <span style={{ fontSize: '14px', width: '16px', textAlign: 'center', flexShrink: 0 }}>
                    {item.icon}
                  </span>
                  {item.label}
                </Link>
              );
            })}
          </div>
        ))}

        {/* Footer */}
        <div className="sidebar-footer">
          <div className="divider" style={{ marginBottom: '12px' }} />

          {/* System Status */}
          <div style={{
            padding: '10px 12px',
            background: 'rgba(16,185,129,0.06)',
            border: '1px solid rgba(16,185,129,0.15)',
            borderRadius: 'var(--radius-md)',
            marginBottom: '12px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="status-dot online" />
              <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--emerald)' }}>All Systems Operational</span>
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              5 services · 99.97% uptime
            </div>
          </div>

          {/* User */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '8px 12px' }}>
            <div className="avatar" style={{ width: '32px', height: '32px' }}>A</div>
            <div style={{ overflow: 'hidden' }}>
              <div style={{ fontSize: '0.83rem', fontWeight: 600, truncate: 'true' }}>Admin User</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Platform Admin</div>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
