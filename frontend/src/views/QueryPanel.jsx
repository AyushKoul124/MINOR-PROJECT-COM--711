import React, { useState } from 'react';
import { Search, Send, ShieldCheck, FileText, CheckCircle2, AlertCircle, Activity, Sparkles } from 'lucide-react';
import { executeRAGQuery } from '../api';

function EvidenceBody({ text }) {
  const raw = text || '';
  const marker = 'Cited posts:';
  const splitAt = raw.indexOf(marker);
  const summary = splitAt >= 0 ? raw.slice(0, splitAt).trim() : raw;
  const citedBlock = splitAt >= 0 ? raw.slice(splitAt + marker.length).trim() : '';
  const citations = citedBlock
    .split('\n')
    .map((line) => line.replace(/^\-\s*/, '').trim())
    .filter(Boolean);

  return (
    <>
      <div style={{ marginTop: '8px' }}>
        <span style={{ color: 'var(--text-muted)' }}>Analysis summary:</span>
        <div style={{
          marginTop: '6px',
          padding: '12px',
          background: 'var(--bg-surface)',
          borderRadius: '6px',
          border: '1px solid var(--border-subtle)',
          lineHeight: '1.6',
          color: 'var(--text-main)',
          whiteSpace: 'pre-wrap',
        }}>
          {summary}
        </div>
      </div>
      <div style={{ marginTop: '8px' }}>
        <span style={{ color: 'var(--text-muted)' }}>Cited source posts:</span>
        {citations.length === 0 ? (
          <div style={{ marginTop: '6px', color: 'var(--text-dim)' }}>
            No source post was stored on this summary.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '6px' }}>
            {citations.map((line) => (
              <div
                key={line}
                style={{
                  padding: '10px 12px',
                  background: 'var(--bg-surface)',
                  borderRadius: '6px',
                  border: '1px solid var(--border-subtle)',
                  lineHeight: '1.55',
                  color: 'var(--text-main)',
                }}
              >
                {line}
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

function sourceLabel(code) {
  return {
    A: 'Sources',
    B: 'Sentiment',
    C: 'Audience',
    D: 'Topics',
    E: 'Network',
  }[code] || 'Collected posts';
}

const SAMPLE_QUESTIONS = [
  "What is the general sentiment and key topics regarding space and defense?",
  "Are any accounts posting in a suspiciously similar way?",
  "Who is the audience around space channels?",
  "Which topics are picking up right now?",
];

export default function QueryPanel() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: 'system',
      text: 'Ask about the collected posts. Answers stay tied to those posts, and you can open the ones that were used.',
      citations: [],
      documents: [],
      is_grounded: true,
    },
  ]);
  const [selectedDoc, setSelectedDoc] = useState(null);

  const handleSend = async (qText) => {
    const textToSend = qText || query;
    if (!textToSend.trim() || loading) return;

    const userMsg = { role: 'user', text: textToSend };
    setMessages((prev) => [...prev, userMsg]);
    setQuery('');
    setLoading(true);

    try {
      const resp = await executeRAGQuery(textToSend, 4);
      const botMsg = {
        role: 'system',
        text: resp.answer,
        citations: resp.citations || [],
        documents: resp.documents || [],
        is_grounded: resp.is_grounded,
        is_short_circuited: resp.is_short_circuited,
        confidence: resp.confidence,
        provider: resp.provider,
        audit_id: resp.audit_id,
        elapsed_seconds: resp.elapsed_seconds,
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      console.error('RAG Query Failed:', err);
      setMessages((prev) => [
        ...prev,
        {
          role: 'system',
          text: 'Error executing query against RAG service. Verify backend connectivity on port 8000.',
          citations: [],
          documents: [],
          is_grounded: false,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="view-stack">
      {/* Sample Inquiry Buttons */}
      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Sparkles size={14} style={{ color: 'var(--accent-cyan)' }} /> Try asking:
        </span>
        {SAMPLE_QUESTIONS.map((sq, i) => (
          <button
            key={i}
            onClick={() => handleSend(sq)}
            disabled={loading}
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-main)',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '12px',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--accent-blue)'}
            onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border-subtle)'}
          >
            {sq}
          </button>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: selectedDoc ? '1fr 340px' : '1fr', gap: '20px' }}>
        {/* Chat Terminal */}
        <div className="rag-terminal">
          <div className="rag-history">
            {messages.map((m, idx) => (
              <div 
                key={idx}
                className={`chat-bubble ${m.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-system'}`}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', fontWeight: 600, color: m.role === 'user' ? '#93c5fd' : 'var(--accent-cyan)' }}>
                    {m.role === 'user' ? 'You' : 'Answer'}
                  </span>
                  {m.elapsed_seconds != null && (
                    <span className="badge badge-gray" style={{ fontSize: '10px' }}>
                      {m.elapsed_seconds}s
                    </span>
                  )}
                </div>

                <div style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>

                {/* Citations & Evidence Drawer Trigger */}
                {m.documents && m.documents.length > 0 && (
                  <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 600 }}>
                      Posts used:
                    </div>
                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                      {m.documents.map((doc, dIdx) => (
                        <button
                          key={dIdx}
                          onClick={() => setSelectedDoc(doc)}
                          style={{
                            background: 'rgba(59, 130, 246, 0.15)',
                            border: '1px solid rgba(59, 130, 246, 0.3)',
                            borderRadius: '4px',
                            color: 'var(--accent-blue)',
                            padding: '3px 8px',
                            fontSize: '11px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px'
                          }}
                        >
                          <FileText size={11} />
                          <span>Source {doc.doc_id.slice(0, 8)}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="chat-bubble chat-bubble-system" style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)' }}>
                <Activity className="animate-spin" size={16} />
                <span>Looking through the collected posts...</span>
              </div>
            )}
          </div>

          <div className="rag-input-bar">
            <input
              type="text"
              className="rag-input"
              placeholder="Ask about sentiment, stance, topics, audience, or similar posting..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              disabled={loading}
            />
            <button
              className="btn-trigger-viva"
              style={{ padding: '8px 16px' }}
              onClick={() => handleSend()}
              disabled={loading || !query.trim()}
            >
              <Send size={15} />
            </button>
          </div>
        </div>

        {/* Selected Evidence Document Inspection Drawer */}
        {selectedDoc && (
          <div className="bento-card citation-drawer" style={{ height: '600px', overflowY: 'auto' }}>
            <div className="card-header">
              <span className="card-title">Evidence Inspector</span>
              <button 
                onClick={() => setSelectedDoc(null)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '16px' }}
              >
                &times;
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '12px' }}>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Reference:</span>
                <div style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-blue)', wordBreak: 'break-all' }}>
                  {selectedDoc.doc_id}
                </div>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)' }}>From:</span>
                <div>
                  <span className="badge badge-purple">{sourceLabel(selectedDoc.source_component)}</span>
                </div>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)' }}>Match:</span>
                <div style={{ fontFamily: 'var(--font-mono)', color: '#34d399', fontWeight: 600 }}>
                  {((selectedDoc.similarity_score || 0) * 100).toFixed(1)}%
                </div>
              </div>

              <EvidenceBody text={selectedDoc.content_text} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
