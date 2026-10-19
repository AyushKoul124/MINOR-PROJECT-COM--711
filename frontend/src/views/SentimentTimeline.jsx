import React, { useState, useEffect } from 'react';
import { Activity, ShieldAlert, Tag, CheckCircle2, MessageSquare } from 'lucide-react';
import { fetchSentimentTimeline, fetchLatestSentiment } from '../api';

export default function SentimentTimeline() {
  const [timeline, setTimeline] = useState(null);
  const [latestPosts, setLatestPosts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [tl, lat] = await Promise.all([
          fetchSentimentTimeline(48),
          fetchLatestSentiment(15),
        ]);
        setTimeline(tl);
        setLatestPosts(lat.posts || []);
      } catch (err) {
        console.error('Failed to load sentiment data:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '300px', color: 'var(--text-muted)' }}>
        <Activity className="animate-spin" size={28} style={{ marginRight: '10px' }} />
        <span>Loading Sentiment & Stance Intelligence...</span>
      </div>
    );
  }

  const stanceMap = timeline?.stance_breakdown || {};
  const totalStance = Object.values(stanceMap).reduce((a, b) => a + b, 0) || 1;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Telemetry Summary */}
      <div className="bento-grid">
        <div className="bento-card" style={{ gridColumn: 'span 4' }}>
          <div className="card-header">
            <span className="card-title">Analyzed Posts</span>
            <span className="badge badge-blue">48H WINDOW</span>
          </div>
          <div className="kpi-value">{timeline?.total_posts || 0}</div>
          <div className="kpi-subtext">Multi-dialectal English + Hinglish text</div>
        </div>

        <div className="bento-card" style={{ gridColumn: 'span 4' }}>
          <div className="card-header">
            <span className="card-title">Policy Stance Coverage</span>
            <span className="badge badge-purple">DistilBART NLI</span>
          </div>
          <div className="kpi-value">{totalStance}</div>
          <div className="kpi-subtext">&ge; 0.60 Confidence Threshold</div>
        </div>

        <div className="bento-card" style={{ gridColumn: 'span 4' }}>
          <div className="card-header">
            <span className="card-title">Sarcasm Flags</span>
            <span className="badge badge-amber">Emoji Incongruity</span>
          </div>
          <div className="kpi-value">{timeline?.sarcasm_count || 0}</div>
          <div className="kpi-subtext">Advisory uncertainty signals</div>
        </div>
      </div>

      {/* Policy Stance Gauges */}
      <div className="bento-card">
        <div className="card-header">
          <span className="card-title">Zero-Shot Policy Stance Breakdown</span>
          <span className="badge badge-emerald">4-Class Partition</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginTop: '12px' }}>
          {['supportive', 'against', 'neutral', 'unclear'].map((st) => {
            const count = stanceMap[st] || 0;
            const pct = ((count / totalStance) * 100).toFixed(1);
            const color = st === 'supportive' ? '#34d399' : st === 'against' ? '#fb7185' : '#94a3b8';
            return (
              <div 
                key={st}
                style={{
                  background: 'var(--bg-surface)',
                  padding: '16px',
                  borderRadius: '8px',
                  border: '1px solid var(--border-subtle)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', textTransform: 'uppercase', fontWeight: 600, color }}>{st}</span>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{pct}%</span>
                </div>
                <div style={{ fontSize: '24px', fontWeight: 700, fontFamily: 'var(--font-mono)', marginTop: '6px' }}>
                  {count}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Chronological Timeline Bucket Cards */}
      <div className="bento-card">
        <div className="card-header">
          <span className="card-title">Chronological Sentiment & Emotion Shifts</span>
          <span className="badge badge-cyan">Anchored on posted_at</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '12px' }}>
          {(timeline?.points || []).map((pt, idx) => (
            <div 
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 16px',
                background: 'var(--bg-surface)',
                borderRadius: '8px',
                border: '1px solid var(--border-subtle)',
                fontSize: '13px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)', fontSize: '12px' }}>
                  {new Date(pt.timestamp).toLocaleTimeString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                </span>
                <span className="badge badge-emerald">+{pt.positive_count} Pos</span>
                <span className="badge badge-rose">-{pt.negative_count} Neg</span>
                <span className="badge badge-gray">{pt.neutral_count} Neu</span>
              </div>

              <div style={{ display: 'flex', gap: '8px', fontSize: '11px', color: 'var(--text-muted)' }}>
                <span>Joy: {(pt.joy_avg * 100).toFixed(0)}%</span>
                <span>•</span>
                <span>Anger: {(pt.anger_avg * 100).toFixed(0)}%</span>
                <span>•</span>
                <span>Fear: {(pt.fear_avg * 100).toFixed(0)}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Latest Enriched Messages Feed */}
      <div className="bento-card">
        <div className="card-header">
          <span className="card-title"><MessageSquare size={16} /> Latest Analyzed Channel Messages</span>
          <span className="badge badge-gray">{latestPosts.length} Items</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '10px' }}>
          {latestPosts.map((p) => (
            <div 
              key={p.post_id}
              style={{
                padding: '14px',
                background: 'var(--bg-surface)',
                borderRadius: '8px',
                border: '1px solid var(--border-subtle)',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--accent-blue)' }}>
                  {p.channel_id} (Post #{p.post_id})
                </span>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <span className={`badge ${p.valence === 'positive' ? 'badge-emerald' : p.valence === 'negative' ? 'badge-rose' : 'badge-blue'}`}>
                    {p.valence?.toUpperCase()}
                  </span>
                  <span className="badge badge-purple">
                    {p.dominant_emotion?.toUpperCase()} ({(p.emotion_confidence * 100).toFixed(0)}%)
                  </span>
                  <span className="badge badge-amber">
                    STANCE: {p.stance?.toUpperCase()}
                  </span>
                  {p.sarcasm_flag && (
                    <span className="badge badge-rose">SARCASM</span>
                  )}
                </div>
              </div>
              <p style={{ margin: 0, fontSize: '13px', color: '#cbd5e1', lineHeight: '1.5' }}>
                "{p.content_text}"
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
