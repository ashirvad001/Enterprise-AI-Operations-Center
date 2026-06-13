'use client';

import { useState, useRef } from 'react';
import { Button } from '../components/Button';

type SessionMsg = { role: 'user' | 'bot'; text: string; meta?: string };

const PIPELINE_STAGES = [
  { id: 'stt',    label: 'STT',    detail: 'faster-whisper',  target: '<500ms' },
  { id: 'intent', label: 'Intent', detail: 'BERT classifier', target: '>85% acc' },
  { id: 'entity', label: 'Entity', detail: 'spaCy + regex',   target: '<20ms' },
  { id: 'llm',    label: 'LLM',    detail: 'Ollama llama3',   target: '<1000ms' },
  { id: 'tts',    label: 'TTS',    detail: 'Azure Neural',    target: '<500ms' },
];

const SESSIONS = [
  { id: 'sess-001', user: 'John D.', intent: 'tracking', turns: 3, escalated: false, dur: '1m 48s', csat: 4.5 },
  { id: 'sess-002', user: 'Sarah M.', intent: 'refund', turns: 2, escalated: false, dur: '58s', csat: 5 },
  { id: 'sess-003', user: 'Mike R.', intent: 'complaint', turns: 5, escalated: true, dur: '3m 12s', csat: 2 },
  { id: 'sess-004', user: 'Emily K.', intent: 'ordering', turns: 4, escalated: false, dur: '2m 05s', csat: 4 },
];

const MOCK_RESPONSES: Record<string, string> = {
  tracking: "I can help you track your order. Could you provide your order number?",
  refund:   "I'll initiate a refund review for you. This typically takes 3-5 business days to process.",
  ordering: "I'd be happy to help you place an order. Which product are you interested in?",
  complaint:"I sincerely apologize for the experience. Could you share more details so I can help resolve this?",
};

function detectIntent(text: string): string {
  const lower = text.toLowerCase();
  if (/track|order|where|arrive|delivery|ship/.test(lower)) return 'tracking';
  if (/refund|return|money|cancel|charge/.test(lower)) return 'refund';
  if (/buy|purchase|order|price|how much/.test(lower)) return 'ordering';
  if (/complaint|bad|unhappy|terrible|problem/.test(lower)) return 'complaint';
  return 'tracking';
}

export default function VoicePage() {
  const [messages, setMessages] = useState<SessionMsg[]>([
    { role: 'bot', text: 'Hello! I\'m your AI support assistant. How can I help you today?' },
  ]);
  const [input, setInput] = useState('');
  const [currentStage, setCurrentStage] = useState(-1);
  const [latencies, setLatencies] = useState<Record<string, number>>({});
  const [processing, setProcessing] = useState(false);
  const [detectedIntent, setDetectedIntent] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const simulatePipeline = async (text: string) => {
    setProcessing(true);
    setCurrentStage(0);
    const newLatencies: Record<string, number> = {};

    const stageTimes = [380, 45, 20, 750, 410];
    for (let i = 0; i < PIPELINE_STAGES.length; i++) {
      setCurrentStage(i);
      await new Promise(r => setTimeout(r, Math.round(stageTimes[i] * 0.15)));
      newLatencies[PIPELINE_STAGES[i].id] = stageTimes[i] + Math.round(Math.random() * 40 - 20);
    }

    setLatencies(newLatencies);
    setCurrentStage(-1);

    const intent = detectIntent(text);
    setDetectedIntent(intent);
    const response = MOCK_RESPONSES[intent] ?? "I'm here to help. Could you tell me more?";
    const totalMs = Object.values(newLatencies).reduce((a, b) => a + b, 0);

    setMessages(prev => [
      ...prev,
      { role: 'user', text },
      { role: 'bot', text: response, meta: `Intent: ${intent} · E2E: ${totalMs}ms` },
    ]);
    setProcessing(false);
  };

  const handleSend = () => {
    if (!input.trim() || processing) return;
    const txt = input.trim();
    setInput('');
    simulatePipeline(txt);
    inputRef.current?.focus();
  };

  const totalLatency = Object.values(latencies).reduce((a, b) => a + b, 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title"><span className="text-gradient">Voice</span> Agent</h1>
          <p className="page-sub">STT → Intent Classification → Entity Extraction → LLM → TTS · Target: &lt;2s E2E</p>
        </div>
        <div className="badge badge-emerald" style={{ fontSize: '0.85rem', padding: '6px 14px' }}>
          {totalLatency > 0 ? `${totalLatency}ms` : '—'} E2E {totalLatency > 0 && totalLatency < 2000 ? '✓' : ''}
        </div>
      </div>

      {/* Pipeline Stage Visualizer */}
      <div className="glass-card animate-fade-up">
        <div className="card-header"><div className="card-title">Pipeline Stage Monitor</div><div className="card-subtitle">Real-time per-stage latency breakdown</div></div>
        <div className="card-body">
          <div style={{ display: 'flex', alignItems: 'stretch', gap: '0', overflowX: 'auto' }}>
            {PIPELINE_STAGES.map((stage, i) => {
              const isActive = currentStage === i;
              const isDone   = currentStage > i || (!processing && latencies[stage.id]);
              const latency  = latencies[stage.id];
              return (
                <div key={stage.id} style={{ display: 'flex', alignItems: 'center', flex: 1, minWidth: 110 }}>
                  <div style={{
                    flex: 1, padding: '16px 12px', borderRadius: 'var(--radius-md)',
                    background: isActive ? 'rgba(59,130,246,0.2)' : isDone ? 'rgba(16,185,129,0.1)' : 'var(--bg-elevated)',
                    border: `1px solid ${isActive ? 'var(--border-blue)' : isDone ? 'rgba(16,185,129,0.3)' : 'var(--border-subtle)'}`,
                    transition: 'all 0.3s', textAlign: 'center',
                    boxShadow: isActive ? 'var(--shadow-glow)' : 'none',
                  }}>
                    <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '4px' }}>{stage.detail}</div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: isActive ? 'var(--blue)' : isDone ? 'var(--emerald)' : 'var(--text-primary)' }}>
                      {isActive ? (
                        <span style={{ display: 'inline-block', animation: 'spin 0.6s linear infinite', fontSize: '14px' }}>⟳</span>
                      ) : latency ? `${latency}ms` : '—'}
                    </div>
                    <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-secondary)', marginTop: '4px' }}>{stage.label}</div>
                    <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', marginTop: '2px' }}>Target: {stage.target}</div>
                  </div>
                  {i < PIPELINE_STAGES.length - 1 && (
                    <div style={{ width: '20px', display: 'flex', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '16px' }}>›</div>
                  )}
                </div>
              );
            })}
          </div>
          {totalLatency > 0 && (
            <div style={{ marginTop: '12px', textAlign: 'right', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Total: <strong style={{ color: totalLatency < 2000 ? 'var(--emerald)' : 'var(--rose)' }}>{totalLatency}ms</strong>
              {totalLatency < 2000 ? ' — ✓ Target Met' : ' — ✗ Over Budget'}
            </div>
          )}
        </div>
      </div>

      <div className="grid-2 animate-fade-up delay-1">
        {/* Chat interface */}
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', height: '500px' }}>
          <div className="card-header">
            <div className="card-title">Voice Chat Interface</div>
            {detectedIntent && <span className={`badge badge-blue`}>Intent: {detectedIntent}</span>}
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '8px 20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {messages.map((msg, i) => (
              <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
                <div style={{
                  maxWidth: '75%', padding: '10px 14px', borderRadius: msg.role === 'user' ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
                  background: msg.role === 'user' ? 'var(--gradient-brand)' : 'var(--bg-elevated)',
                  border: msg.role === 'bot' ? '1px solid var(--border-subtle)' : 'none',
                  fontSize: '0.875rem', lineHeight: 1.5,
                  color: msg.role === 'user' ? '#fff' : 'var(--text-primary)',
                }}>
                  {msg.text}
                </div>
                {msg.meta && <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '4px', padding: '0 4px' }}>{msg.meta}</div>}
              </div>
            ))}
            {processing && (
              <div style={{ display: 'flex', alignItems: 'flex-start' }}>
                <div style={{ padding: '10px 14px', borderRadius: '14px 14px 14px 4px', background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ display: 'inline-flex', gap: '4px' }}>
                    {[0, 1, 2].map(i => (
                      <span key={i} style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--text-muted)', animation: `pulse-dot 1.2s ${i * 0.2}s infinite` }} />
                    ))}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div style={{ padding: '12px 16px', borderTop: '1px solid var(--border-subtle)', display: 'flex', gap: '8px' }}>
            <input
              ref={inputRef}
              className="input-field"
              placeholder="Type a message or simulate voice input..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            />
            <button className="btn btn-primary" onClick={handleSend} disabled={processing || !input.trim()}>
              ▶
            </button>
            <button className="btn btn-secondary btn-icon" title="Simulate voice input">
              🎙
            </button>
          </div>
        </div>

        {/* Session history */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="glass-card">
            <div className="card-header"><div className="card-title">Recent Sessions</div></div>
            <div className="card-body" style={{ padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {SESSIONS.map(sess => (
                <div key={sess.id} style={{ padding: '12px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                  <div className="flex items-center justify-between" style={{ marginBottom: '6px' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>{sess.user}</span>
                    {sess.escalated
                      ? <span className="badge badge-rose">Escalated</span>
                      : <span className="badge badge-emerald">Resolved</span>}
                  </div>
                  <div className="flex gap-3" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    <span><span className="badge badge-violet">{sess.intent}</span></span>
                    <span>{sess.turns} turns</span>
                    <span>{sess.dur}</span>
                    <span>CSAT: <strong style={{ color: sess.csat >= 4 ? 'var(--emerald)' : sess.csat >= 3 ? 'var(--amber)' : 'var(--rose)' }}>{'★'.repeat(Math.round(sess.csat))}</strong></span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Intent distribution */}
          <div className="glass-card">
            <div className="card-header"><div className="card-title">Intent Distribution (24h)</div></div>
            <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {[
                { intent: 'tracking', pct: 42, color: 'var(--blue)' },
                { intent: 'refund',   pct: 28, color: 'var(--violet)' },
                { intent: 'ordering', pct: 20, color: 'var(--emerald)' },
                { intent: 'complaint',pct: 10, color: 'var(--rose)' },
              ].map(({ intent, pct, color }) => (
                <div key={intent}>
                  <div className="flex items-center justify-between" style={{ marginBottom: '5px', fontSize: '0.82rem' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>{intent}</span>
                    <span style={{ fontWeight: 600, color }}>{pct}%</span>
                  </div>
                  <div className="progress-track">
                    <div className="progress-fill" style={{ width: `${pct}%`, background: color }} />
                  </div>
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
