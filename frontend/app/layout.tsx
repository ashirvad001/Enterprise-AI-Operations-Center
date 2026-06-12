import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'EAIOC | Enterprise AI Operations Center',
  description: 'Multi-Agent Orchestration, MLOps, and IoT Edge Management',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="dashboard-layout">
          {/* Sidebar */}
          <aside className="sidebar">
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
              <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'var(--accent-gradient)' }}></div>
              <h2 style={{ fontSize: '1.25rem', margin: 0 }}><span className="text-gradient">EAIOC</span></h2>
            </div>
            
            <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {['Dashboard', 'Agent Orchestration', 'Knowledge Base', 'MLOps Registry', 'Edge Devices'].map((item, i) => (
                <div 
                  key={i} 
                  style={{ 
                    padding: '10px 16px', 
                    borderRadius: '8px', 
                    color: i === 0 ? 'var(--text-primary)' : 'var(--text-secondary)',
                    background: i === 0 ? 'var(--border-subtle)' : 'transparent',
                    cursor: 'pointer',
                    transition: 'var(--transition-fast)',
                    fontWeight: 500
                  }}
                  onMouseOver={(e) => {
                    if (i !== 0) e.currentTarget.style.color = 'var(--text-primary)';
                  }}
                  onMouseOut={(e) => {
                    if (i !== 0) e.currentTarget.style.color = 'var(--text-secondary)';
                  }}
                >
                  {item}
                </div>
              ))}
            </nav>
          </aside>

          {/* Main Layout */}
          <main className="main-content">
            <header className="top-header">
              <h1 style={{ fontSize: '1.25rem', fontWeight: 600 }}>System Overview</h1>
              <div style={{ marginLeft: 'auto', display: 'flex', gap: '16px', alignItems: 'center' }}>
                <div style={{ 
                  padding: '6px 12px', 
                  borderRadius: '20px', 
                  background: 'var(--border-subtle)',
                  fontSize: '0.875rem',
                  color: 'var(--text-secondary)'
                }}>
                  Environment: <span style={{ color: '#10b981', fontWeight: 600 }}>Production</span>
                </div>
                <div style={{ width: '36px', height: '36px', borderRadius: '50%', background: 'var(--border-strong)' }}></div>
              </div>
            </header>

            <div className="content-area">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
