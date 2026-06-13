'use client';

import { useState } from 'react';
import { Button } from '../components/Button';

const MODELS = [
  { id: 'mdl-001', name: 'llama3:8b-Q4_K_M', base: 'Meta-Llama-3-8B', quant: 'Q4_K_M', size: '4.5GB', tps: 45, accuracy_loss: '1.8%', status: 'loaded', nodes: 3, device: 'Raspberry Pi 5' },
  { id: 'mdl-002', name: 'llama3:8b-Q8_0',   base: 'Meta-Llama-3-8B', quant: 'Q8_0',   size: '6.0GB', tps: 22, accuracy_loss: '0.4%', status: 'available', nodes: 0, device: 'Jetson Orin' },
  { id: 'mdl-003', name: 'mistral:7b-Q4_K_M', base: 'Mistral-7B-v0.1', quant: 'Q4_K_M', size: '4.1GB', tps: 48, accuracy_loss: '1.6%', status: 'loaded', nodes: 2, device: 'Raspberry Pi 5' },
  { id: 'mdl-004', name: 'phi3:mini-Q4',      base: 'Phi-3-mini-4k',  quant: 'Q4_K_M', size: '2.2GB', tps: 78, accuracy_loss: '2.1%', status: 'available', nodes: 0, device: 'Any' },
];

const EDGE_NODES = [
  { id: 'pi5-01', device: 'Raspberry Pi 5', model: 'llama3:8b-Q4_K_M', tps: 43, ram_used: '5.2GB', ram_total: '8GB', status: 'online', uptime: '99.97%', requests: 1204 },
  { id: 'pi5-02', device: 'Raspberry Pi 5', model: 'llama3:8b-Q4_K_M', tps: 47, ram_used: '5.1GB', ram_total: '8GB', status: 'online', uptime: '99.91%', requests: 987 },
  { id: 'pi5-03', device: 'Raspberry Pi 5', model: 'mistral:7b-Q4_K_M', tps: 51, ram_used: '4.8GB', ram_total: '8GB', status: 'online', uptime: '100%', requests: 843 },
  { id: 'pi5-04', device: 'Raspberry Pi 5', model: 'mistral:7b-Q4_K_M', tps: 49, ram_used: '4.9GB', ram_total: '8GB', status: 'online', uptime: '99.85%', requests: 712 },
  { id: 'jet-01', device: 'Jetson Nano',    model: 'phi3:mini-Q4',      tps: 72, ram_used: '2.4GB', ram_total: '4GB', status: 'online', uptime: '99.99%', requests: 2341 },
  { id: 'pi5-07', device: 'Raspberry Pi 5', model: 'llama3:8b-Q4_K_M', tps: 0,  ram_used: '0GB',   ram_total: '8GB', status: 'offline', uptime: '—', requests: 0 },
];

const BENCH = [
  { prompt: 'Short (5 tokens)',  p50: 390, p95: 450, p99: 520, tps: 46 },
  { prompt: 'Medium (60 tokens)', p50: 1820, p95: 2100, p99: 2450, tps: 44 },
  { prompt: 'Long (300 tokens)', p50: 7100, p95: 8200, p99: 9100, tps: 42 },
];

export default function EdgePage() {
  const [tab, setTab] = useState<'nodes' | 'models' | 'benchmark'>('nodes');
  const [quantizing, setQuantizing] = useState(false);
  const [quantProgress, setQuantProgress] = useState(0);

  const startQuant = () => {
    setQuantizing(true);
    setQuantProgress(0);
    const id = setInterval(() => {
      setQuantProgress(p => {
        if (p >= 100) { clearInterval(id); setQuantizing(false); return 100; }
        return p + 2;
      });
    }, 80);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title"><span className="text-gradient">Edge</span> Devices</h1>
          <p className="page-sub">GGUF quantized LLMs on Raspberry Pi 5 and Jetson hardware · Target: &gt;40 TPS</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={startQuant} disabled={quantizing}>
            {quantizing ? `Quantizing ${quantProgress}%` : '+ Quantize Model'}
          </Button>
          <Button variant="primary">+ Register Node</Button>
        </div>
      </div>

      {/* Quantization progress bar */}
      {quantizing && (
        <div className="glass-card animate-fade-in">
          <div className="card-body">
            <div className="flex items-center justify-between" style={{ marginBottom: '8px' }}>
              <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>Quantizing Meta-Llama-3-8B → Q4_K_M...</span>
              <span style={{ fontSize: '0.875rem', color: 'var(--blue)', fontWeight: 600 }}>{quantProgress}%</span>
            </div>
            <div className="progress-track" style={{ height: '8px' }}>
              <div className="progress-fill" style={{ width: `${quantProgress}%`, transition: 'width 0.1s linear' }} />
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '6px' }}>
              {quantProgress < 30 ? 'Downloading HuggingFace model...' :
               quantProgress < 60 ? 'Converting to GGUF fp16...' :
               quantProgress < 90 ? 'Applying Q4_K_M quantization...' :
               'Generating Ollama Modelfile...'}
            </div>
          </div>
        </div>
      )}

      {/* KPI row */}
      <div className="grid-4 animate-fade-up">
        {[
          { label: 'Online Nodes', value: '5 / 6', badge: 'badge-emerald', badgeT: '1 offline' },
          { label: 'Avg TPS (Q4_K_M)', value: '45.8', badge: 'badge-blue', badgeT: '> 40 target ✓' },
          { label: 'Models Loaded', value: '2', badge: 'badge-violet', badgeT: 'llama3, mistral' },
          { label: 'Daily Requests', value: '6.1K', badge: 'badge-cyan', badgeT: '$0 API cost' },
        ].map((s, i) => (
          <div key={i} className="glass-card stat-card animate-fade-up" style={{ animationDelay: `${i * 0.05}s` }}>
            <div className="stat-label">{s.label}</div>
            <div className="stat-value">{s.value}</div>
            <div className={`badge ${s.badge}`}>{s.badgeT}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="tabs" style={{ width: 'fit-content' }}>
        {(['nodes', 'models', 'benchmark'] as const).map(t => (
          <button key={t} className={`tab-item ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {t === 'nodes' ? '🖥 Edge Nodes' : t === 'models' ? '🧠 Model Registry' : '📊 Benchmarks'}
          </button>
        ))}
      </div>

      {/* Nodes tab */}
      {tab === 'nodes' && (
        <div className="glass-card animate-fade-in">
          <div className="card-header"><div className="card-title">Edge Node Fleet</div></div>
          <div className="card-body" style={{ padding: 0 }}>
            <table className="data-table">
              <thead><tr>
                <th>Node</th><th>Device</th><th>Model</th>
                <th>TPS</th><th>RAM</th><th>Requests</th><th>Uptime</th><th>Status</th><th></th>
              </tr></thead>
              <tbody>
                {EDGE_NODES.map(node => {
                  const ramPct = parseInt(node.ram_used) / parseInt(node.ram_total) * 100 || 0;
                  return (
                    <tr key={node.id}>
                      <td className="font-mono text-sm">{node.id}</td>
                      <td style={{ fontWeight: 500 }}>{node.device}</td>
                      <td><span className="badge badge-violet" style={{ fontSize: '0.68rem' }}>{node.model}</span></td>
                      <td>
                        <span style={{ fontWeight: 700, color: node.tps >= 40 ? 'var(--emerald)' : node.tps > 0 ? 'var(--amber)' : 'var(--text-muted)' }}>
                          {node.tps > 0 ? `${node.tps}` : '—'}
                        </span>
                        {node.tps > 0 && <span className="text-muted text-xs"> t/s</span>}
                      </td>
                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                          <div className="text-xs" style={{ color: 'var(--text-muted)' }}>{node.ram_used} / {node.ram_total}</div>
                          <div className="progress-track" style={{ width: '80px', height: '4px' }}>
                            <div className="progress-fill" style={{ width: `${ramPct}%`, background: ramPct > 80 ? 'var(--amber)' : 'var(--emerald)' }} />
                          </div>
                        </div>
                      </td>
                      <td className="font-mono text-sm">{node.requests.toLocaleString()}</td>
                      <td className="text-sm">{node.uptime}</td>
                      <td>
                        <span className={`badge ${node.status === 'online' ? 'badge-emerald' : 'badge-rose'}`}>
                          <span className={`status-dot ${node.status === 'online' ? 'online' : 'offline'}`} />
                          {node.status}
                        </span>
                      </td>
                      <td><button className="btn btn-ghost btn-sm">···</button></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Models tab */}
      {tab === 'models' && (
        <div className="glass-card animate-fade-in">
          <div className="card-header"><div className="card-title">GGUF Model Registry</div></div>
          <div className="card-body" style={{ padding: 0 }}>
            <table className="data-table">
              <thead><tr>
                <th>Model</th><th>Base Model</th><th>Quantization</th>
                <th>Size</th><th>TPS</th><th>Accuracy Loss</th><th>Nodes</th><th>Status</th><th></th>
              </tr></thead>
              <tbody>
                {MODELS.map(m => (
                  <tr key={m.id}>
                    <td><span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.83rem', fontWeight: 600 }}>{m.name}</span></td>
                    <td className="text-sm">{m.base}</td>
                    <td>
                      <span className={`badge ${m.quant === 'Q4_K_M' ? 'badge-blue' : m.quant === 'Q8_0' ? 'badge-violet' : 'badge-cyan'}`}>{m.quant}</span>
                    </td>
                    <td className="font-mono text-sm">{m.size}</td>
                    <td>
                      <span style={{ fontWeight: 700, color: m.tps >= 40 ? 'var(--emerald)' : 'var(--amber)' }}>{m.tps}</span>
                      <span className="text-xs text-muted"> t/s</span>
                    </td>
                    <td className="text-sm" style={{ color: parseFloat(m.accuracy_loss) > 1.5 ? 'var(--amber)' : 'var(--emerald)' }}>{m.accuracy_loss}</td>
                    <td><span className="badge badge-cyan">{m.nodes} nodes</span></td>
                    <td>
                      <span className={`badge ${m.status === 'loaded' ? 'badge-emerald' : 'badge-violet'}`}>{m.status}</span>
                    </td>
                    <td>
                      {m.status === 'available' && <button className="btn btn-secondary btn-sm">Deploy</button>}
                      {m.status === 'loaded' && <button className="btn btn-ghost btn-sm">Unload</button>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Benchmark tab */}
      {tab === 'benchmark' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }} className="animate-fade-in">
          <div className="glass-card">
            <div className="card-header">
              <div><div className="card-title">Latency Benchmark Results</div><div className="card-subtitle">Model: llama3:8b-Q4_K_M · Device: Raspberry Pi 5 (8GB) · 5 runs/prompt</div></div>
              <span className="badge badge-emerald">All targets met</span>
            </div>
            <div className="card-body" style={{ padding: 0 }}>
              <table className="data-table">
                <thead><tr>
                  <th>Prompt Type</th><th>P50 Latency</th><th>P95 Latency</th><th>P99 Latency</th>
                  <th>Avg TPS</th><th>Target</th><th>Status</th>
                </tr></thead>
                <tbody>
                  {BENCH.map(b => (
                    <tr key={b.prompt}>
                      <td style={{ fontWeight: 500 }}>{b.prompt}</td>
                      <td className="font-mono text-sm">{b.p50}ms</td>
                      <td className="font-mono text-sm">{b.p95}ms</td>
                      <td className="font-mono text-sm">{b.p99}ms</td>
                      <td>
                        <span style={{ fontWeight: 700, color: 'var(--emerald)' }}>{b.tps} t/s</span>
                      </td>
                      <td className="text-sm text-muted">&gt;40 t/s</td>
                      <td><span className="badge badge-emerald">✓ Pass</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* TPS bar chart */}
          <div className="glass-card">
            <div className="card-header"><div className="card-title">TPS by Quantization &amp; Device</div></div>
            <div className="card-body">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {[
                  { label: 'Pi5 · Q4_K_M (llama3:8b)', tps: 45, max: 80, color: 'var(--blue)' },
                  { label: 'Pi5 · Q4_K_M (mistral:7b)', tps: 49, max: 80, color: 'var(--violet)' },
                  { label: 'Jetson · Q4_K_M (phi3:mini)', tps: 78, max: 80, color: 'var(--emerald)' },
                  { label: 'Pi5 · Q8_0 (llama3:8b)',    tps: 22, max: 80, color: 'var(--amber)' },
                  { label: 'Laptop CPU · Q4_K_M',       tps: 25, max: 80, color: 'var(--cyan)' },
                ].map(({ label, tps, max, color }) => (
                  <div key={label}>
                    <div className="flex items-center justify-between" style={{ marginBottom: '5px', fontSize: '0.82rem' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
                      <span style={{ fontWeight: 700, color, minWidth: '60px', textAlign: 'right' }}>{tps} t/s</span>
                    </div>
                    <div className="progress-track">
                      <div className="progress-fill" style={{ width: `${(tps / max) * 100}%`, background: color }} />
                    </div>
                  </div>
                ))}
                <div className="divider" />
                <div className="text-xs text-muted">Dashed line = 40 t/s target threshold</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
