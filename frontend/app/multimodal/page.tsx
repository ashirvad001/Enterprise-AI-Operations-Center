'use client';

import { useState, useCallback } from 'react';
import { Button } from '../components/Button';

type AnalysisResult = { type: string; content: string; metadata: Record<string, string>; };

const SAMPLE_RESULTS: Record<string, AnalysisResult> = {
  pdf: {
    type: 'PDF',
    content: 'Extracted 47 pages of text, 12 tables, and 8 images. Identified Q3 Financial Report structure: Executive Summary (p1-3), Revenue Analysis (p4-18), Regional Breakdown (p19-32), YoY Comparison charts extracted from p22, p25.',
    metadata: { 'Pages': '47', 'Tables': '12', 'Images': '8', 'Chunks': '142', 'Tokens': '89K', 'Router': 'pdf_parser' },
  },
  image: {
    type: 'IMAGE',
    content: 'Chart Analysis (GPT-4o Vision): Bar chart showing Q3 regional revenue. X-axis: regions (APAC, EMEA, AMER, LATAM). Y-axis: revenue in $M. Key findings: APAC leads at $124M (+18% YoY), EMEA $98M (+7%), AMER $87M (-3%), LATAM $23M (+31%). Confidence: 0.94.',
    metadata: { 'Model': 'GPT-4o Vision', 'Type': 'bar_chart', 'Confidence': '0.94', 'Latency': '1240ms', 'Router': 'vision_model' },
  },
  text: {
    type: 'TEXT',
    content: 'Direct text processing via RAG pipeline. Query: "RBAC policy for medical records". Retrieved 4 relevant chunks from medical-policy.pdf with context precision 0.84. Citations: [doc-003:p4], [doc-003:p7], [doc-003:p12].',
    metadata: { 'Chunks Retrieved': '4', 'Precision': '0.84', 'Reranked': 'Yes', 'Latency': '310ms', 'Router': 'text_direct' },
  },
};

const RECENT_ANALYSES = [
  { file: 'revenue_chart.png',     type: 'IMAGE', size: '2.1MB', time: '5m ago',  status: 'completed', router: 'vision_model' },
  { file: 'Q3_report.pdf',         type: 'PDF',   size: '4.2MB', time: '18m ago', status: 'completed', router: 'pdf_parser' },
  { file: 'api_architecture.jpg',  type: 'IMAGE', size: '0.8MB', time: '1h ago',  status: 'completed', router: 'vision_model' },
  { file: 'contracts_2024.pdf',    type: 'PDF',   size: '12MB',  time: '2h ago',  status: 'completed', router: 'pdf_parser' },
  { file: 'board_presentation.pptx', type: 'PPTX', size: '8.4MB', time: '3h ago', status: 'completed', router: 'pdf_parser' },
];

export default function MultimodalPage() {
  const [dragging, setDragging] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [selectedType, setSelectedType] = useState<'pdf' | 'image' | 'text'>('pdf');
  const [textInput, setTextInput] = useState('');

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (!file) return;
    const type = file.type.includes('pdf') ? 'pdf' : file.type.includes('image') ? 'image' : 'text';
    setSelectedType(type as 'pdf' | 'image' | 'text');
    runAnalysis(type as 'pdf' | 'image' | 'text');
  }, []);

  const runAnalysis = (type: 'pdf' | 'image' | 'text') => {
    setAnalyzing(true);
    setResult(null);
    setTimeout(() => {
      setResult(SAMPLE_RESULTS[type]);
      setAnalyzing(false);
    }, 1500);
  };

  const ROUTE_DECISION = [
    { label: 'MIME Type Check', value: 'application/pdf → PDF branch', done: true },
    { label: 'Extension Check', value: '.pdf confirmed', done: true },
    { label: 'Magic Bytes',     value: '%PDF-1.4 header verified', done: true },
    { label: 'Router Decision', value: 'pdf_parser selected', done: true },
    { label: 'OCR Required',    value: 'No (text-native PDF)', done: true },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title"><span className="text-gradient">Multimodal</span> Processing</h1>
          <p className="page-sub">PDF, image, chart, and text analysis with GPT-4o Vision and automated RAG chunking.</p>
        </div>
      </div>

      {/* KPI strip */}
      <div className="grid-4 animate-fade-up">
        {[
          { label: 'Files Processed (24h)', value: '89', badge: 'badge-blue', bt: '47 PDFs · 42 images' },
          { label: 'Avg Chunks / Doc',      value: '156', badge: 'badge-violet', bt: 'semantic chunking' },
          { label: 'Vision Accuracy',       value: '94%', badge: 'badge-emerald', bt: 'chart extraction' },
          { label: 'Citation Correctness',  value: '92%', badge: 'badge-cyan', bt: '> 90% target ✓' },
        ].map((s, i) => (
          <div key={i} className="glass-card stat-card animate-fade-up" style={{ animationDelay: `${i * 0.05}s` }}>
            <div className="stat-label">{s.label}</div>
            <div className="stat-value">{s.value}</div>
            <div className={`badge ${s.badge}`}>{s.bt}</div>
          </div>
        ))}
      </div>

      <div className="grid-2 animate-fade-up delay-1">
        {/* Upload / analyze panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

          {/* Type selector */}
          <div className="tabs" style={{ width: '100%' }}>
            {(['pdf', 'image', 'text'] as const).map(t => (
              <button key={t} style={{ flex: 1 }} className={`tab-item ${selectedType === t ? 'active' : ''}`} onClick={() => setSelectedType(t)}>
                {t === 'pdf' ? '📄 PDF' : t === 'image' ? '🖼 Image/Chart' : '✏️ Text'}
              </button>
            ))}
          </div>

          {/* Drop zone */}
          {selectedType !== 'text' ? (
            <div
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              style={{
                border: `2px dashed ${dragging ? 'var(--blue)' : 'var(--border-default)'}`,
                borderRadius: 'var(--radius-lg)', padding: '40px 24px', textAlign: 'center',
                background: dragging ? 'rgba(59,130,246,0.06)' : 'var(--bg-elevated)',
                transition: 'all 0.2s', cursor: 'pointer',
                boxShadow: dragging ? 'var(--shadow-glow)' : 'none',
              }}
              onClick={() => runAnalysis(selectedType)}
            >
              <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>{selectedType === 'pdf' ? '📄' : '🖼'}</div>
              <div style={{ fontWeight: 600, marginBottom: '6px' }}>
                {dragging ? 'Drop to analyze' : `Drop ${selectedType === 'pdf' ? 'PDF' : 'image'} here`}
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
                or click to simulate analysis
              </div>
              <div className="flex gap-2" style={{ justifyContent: 'center' }}>
                {selectedType === 'pdf'
                  ? ['application/pdf', '.pdf', 'Max 50MB'].map(t => <span key={t} className="badge badge-blue">{t}</span>)
                  : ['image/png', 'image/jpg', 'image/webp'].map(t => <span key={t} className="badge badge-violet">{t}</span>)}
              </div>
            </div>
          ) : (
            <div>
              <textarea
                className="input-field"
                style={{ height: '140px', resize: 'vertical', fontFamily: 'inherit' }}
                placeholder="Enter text query for RAG pipeline..."
                value={textInput}
                onChange={e => setTextInput(e.target.value)}
              />
              <Button variant="primary" style={{ marginTop: '8px', width: '100%' }} onClick={() => runAnalysis('text')} loading={analyzing}>
                Analyze with RAG
              </Button>
            </div>
          )}

          {/* Analyze button */}
          {selectedType !== 'text' && (
            <Button variant="primary" loading={analyzing} onClick={() => runAnalysis(selectedType)}>
              {analyzing ? 'Analyzing...' : `Analyze ${selectedType === 'pdf' ? 'PDF' : 'Image'}`}
            </Button>
          )}

          {/* Router decision tree */}
          <div className="glass-card">
            <div className="card-header"><div className="card-title">Router Decision</div><div className="card-subtitle">MIME → extension → magic bytes</div></div>
            <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '12px 16px' }}>
              {ROUTE_DECISION.map((step, i) => (
                <div key={i} className="flex items-center gap-3" style={{ fontSize: '0.8rem' }}>
                  <span style={{ color: 'var(--emerald)', flexShrink: 0 }}>✓</span>
                  <span style={{ color: 'var(--text-muted)', minWidth: '130px' }}>{step.label}</span>
                  <span style={{ fontFamily: 'JetBrains Mono', color: 'var(--text-secondary)', fontSize: '0.75rem' }}>{step.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Results panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Analysis result */}
          <div className="glass-card" style={{ minHeight: '220px' }}>
            <div className="card-header">
              <div className="card-title">Analysis Result</div>
              {result && <span className={`badge ${result.type === 'PDF' ? 'badge-rose' : result.type === 'IMAGE' ? 'badge-violet' : 'badge-blue'}`}>{result.type}</span>}
            </div>
            <div className="card-body">
              {analyzing && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {['Routing input...', 'Extracting content...', 'Chunking with semantic boundaries...'].map((s, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                      <span style={{ width: '16px', height: '16px', borderRadius: '50%', border: '2px solid var(--blue)', borderTopColor: 'transparent', animation: 'spin 0.7s linear infinite', display: 'inline-block', flexShrink: 0 }} />
                      {s}
                    </div>
                  ))}
                </div>
              )}
              {result && !analyzing && (
                <div className="animate-fade-in">
                  <p style={{ fontSize: '0.875rem', lineHeight: 1.7, color: 'var(--text-secondary)', marginBottom: '16px' }}>{result.content}</p>
                  <div className="divider" style={{ marginBottom: '12px' }} />
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {Object.entries(result.metadata).map(([k, v]) => (
                      <div key={k} style={{ padding: '4px 10px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', fontSize: '0.75rem' }}>
                        <span style={{ color: 'var(--text-muted)' }}>{k}: </span>
                        <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {!result && !analyzing && (
                <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '32px 0', fontSize: '0.875rem' }}>
                  Upload or drop a file to see analysis results
                </div>
              )}
            </div>
          </div>

          {/* Recent analyses */}
          <div className="glass-card">
            <div className="card-header"><div className="card-title">Recent Analyses</div></div>
            <div className="card-body" style={{ padding: '0 0 8px' }}>
              {RECENT_ANALYSES.map((item, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '10px 16px', borderBottom: i < RECENT_ANALYSES.length - 1 ? '1px solid var(--border-subtle)' : 'none' }}>
                  <span style={{ fontSize: '1.2rem' }}>{item.type === 'PDF' ? '📄' : item.type === 'IMAGE' ? '🖼' : '📊'}</span>
                  <div style={{ flex: 1, overflow: 'hidden' }}>
                    <div className="truncate" style={{ fontSize: '0.875rem', fontWeight: 500 }}>{item.file}</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{item.size} · {item.time}</div>
                  </div>
                  <span className="badge badge-violet" style={{ fontSize: '0.65rem' }}>{item.router}</span>
                  <span className="badge badge-emerald">✓</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
