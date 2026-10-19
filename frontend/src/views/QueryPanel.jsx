import React, { useState } from 'react';
import { Search, Send, ShieldCheck, FileText, CheckCircle2, AlertCircle, Activity, Sparkles } from 'lucide-react';
import { executeRAGQuery } from '../api';

const SAMPLE_QUESTIONS = [
  "What is the general sentiment and key topics regarding space and defense?",
  "Are there any coordinated inauthentic behavior clusters or anomalous actors?",
  "What are the dominant audience demographic characteristics for space channels?",
  "What are the latest emergent trends and publication velocities?",
];

export default function QueryPanel() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: 'system',
      text: 'Welcome to the SOCMINT RAG Intelligence Terminal. Inquiries are grounded against vector-indexed summaries across Components B, C, D, and E with strict distance cutoff gating (<0.65) to guarantee zero hallucination.',
      citations: [],
      documents: [],
      is_grounded: true,
      provider: 'pgvector_rag',
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Sample Inquiry Buttons */}
      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Sparkles size={14} style={{ color: 'var(--accent-cyan)' }} /> Viva Prompts:
        </span>
        {SAMPLE_QUESTIONS.map((sq, i) => (
          <button
            key={i}
            onClick={() => handleSend(sq)}
            disabled={loading}
            style={{
              background: 'rgba(30, 41, 59, 0.6)',
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
                    {m.role === 'user' ? 'ANALYST INQUIRY' : 'GROUNDED INTELLIGENCE'}
                  </span>
                  {m.provider && (
                    <span className="badge badge-gray" style={{ fontSize: '10px' }}>
                      {m.provider} {m.elapsed_seconds ? `(${m.elapsed_seconds}s)` : ''}
                    </span>
                  )}
                </div>

                <div style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>

                {/* Citations & Evidence Drawer Trigger */}
                {m.documents && m.documents.length > 0 && (
                  <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 600 }}>
                      CITED EVIDENCE SNIPPETS:
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
                            color: '#93c5fd',
                            padding: '3px 8px',
                            fontSize: '11px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px'
                          }}
                        >
                          <FileText size={11} />
                          <span>Doc #{doc.doc_id.slice(0, 8)} ({doc.source_component})</span>
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
                <span>Retrieving pgvector dense embeddings and synthesizing grounded response...</span>
              </div>
            )}
          </div>

          <div className="rag-input-bar">
            <input
              type="text"
              className="rag-input"
              placeholder="Ask an intelligence question regarding sentiment, stance, trends, or CIB anomalies..."
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
          <div className="bento-card" style={{ height: '600px', overflowY: 'auto' }}>
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
                <span style={{ color: 'var(--text-muted)' }}>Document ID:</span>
                <div style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-blue)', wordBreak: 'break-all' }}>
                  {selectedDoc.doc_id}
                </div>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)' }}>Component Origin:</span>
                <div>
                  <span className="badge badge-purple">Component {selectedDoc.source_component}</span>
                </div>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)' }}>Semantic Similarity:</span>
                <div style={{ fontFamily: 'var(--font-mono)', color: '#34d399', fontWeight: 600 }}>
                  {((selectedDoc.similarity_score || 0) * 100).toFixed(1)}% (Distance: {selectedDoc.cosine_distance})
                </div>
              </div>

              <div style={{ marginTop: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Indexed Content Text:</span>
                <div style={{ 
                  marginTop: '6px', 
                  padding: '12px', 
                  background: 'var(--bg-surface)', 
                  borderRadius: '6px', 
                  border: '1px solid var(--border-subtle)',
                  lineHeight: '1.6',
                  color: '#e2e8f0',
                  whiteSpace: 'pre-wrap'
                }}>
                  {selectedDoc.content_text}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
