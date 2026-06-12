import { Card } from './components/Card';
import { Button } from './components/Button';

export default function Home() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      
      {/* Header Section */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h2 style={{ fontSize: '2rem', marginBottom: '8px' }}>Welcome back, Admin</h2>
          <p style={{ color: 'var(--text-secondary)' }}>Here is what's happening across your AI infrastructure today.</p>
        </div>
        <Button variant="primary">+ Deploy New Agent</Button>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px' }}>
        <Card title="Active Workflows">
          <div style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            14 <span style={{ fontSize: '1rem', color: '#10b981', fontWeight: 500 }}>+2 today</span>
          </div>
        </Card>
        
        <Card title="Token Usage (24h)">
          <div style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            4.2M <span style={{ fontSize: '1rem', color: '#ef4444', fontWeight: 500 }}>+15% limit</span>
          </div>
        </Card>

        <Card title="Online Edge Nodes">
          <div style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            128 <span style={{ fontSize: '1rem', color: 'var(--text-secondary)', fontWeight: 500 }}>/ 130</span>
          </div>
        </Card>
      </div>

      {/* Main Content Area */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
        <Card title="Recent Agent Executions" className="flex-1">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '8px' }}>
            {[
              { id: 'exec-8f2a', agent: 'Data Analyst Agent', status: 'Running', time: '2m ago' },
              { id: 'exec-9b1c', agent: 'Support Triage', status: 'Completed', time: '15m ago' },
              { id: 'exec-4e7d', agent: 'Code Reviewer', status: 'Failed', time: '1h ago' },
            ].map((exec, i) => (
              <div key={i} style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                padding: '12px 16px',
                background: 'var(--bg-surface-solid)',
                borderRadius: '8px',
                border: '1px solid var(--border-subtle)'
              }}>
                <div>
                  <div style={{ fontWeight: 500 }}>{exec.agent}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>ID: {exec.id}</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <span style={{ 
                    fontSize: '0.875rem',
                    color: exec.status === 'Running' ? '#3b82f6' : exec.status === 'Completed' ? '#10b981' : '#ef4444' 
                  }}>{exec.status}</span>
                  <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)', width: '60px', textAlign: 'right' }}>{exec.time}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card title="System Alerts">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '8px' }}>
            <div style={{ padding: '12px', background: 'rgba(239, 68, 68, 0.1)', borderLeft: '4px solid #ef4444', borderRadius: '4px' }}>
              <div style={{ fontWeight: 600, fontSize: '0.875rem', color: '#ef4444' }}>Edge Node Offline</div>
              <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '4px' }}>Device node-7a has not responded for 5 mins.</div>
            </div>
            
            <div style={{ padding: '12px', background: 'rgba(245, 158, 11, 0.1)', borderLeft: '4px solid #f59e0b', borderRadius: '4px' }}>
              <div style={{ fontWeight: 600, fontSize: '0.875rem', color: '#f59e0b' }}>High Token Usage</div>
              <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '4px' }}>Budget for 'Data Analyst' is at 90%.</div>
            </div>
          </div>
        </Card>
      </div>
      
    </div>
  );
}
