import React, { useState, useEffect } from 'react';
import { TrendingUp, Flame, Tag, Clock, Activity, Zap } from 'lucide-react';
import { fetchTrends } from '../api';

export default function TrendExplorer() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const res = await fetchTrends(48);
        setData(res);
      } catch (err) {
        console.error('Failed to load trends:', err);
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
        <span>Loading BERTopic Velocity Engine...</span>
      </div>
    );
  }

  const topics = data?.topics || [];
  const surgingCount = data?.surging_count || 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Telemetry Cards */}
      <div className="bento-grid">
        <div className="bento-card" style={{ gridColumn: 'span 4' }}>
          <div className="card-header">
            <span className="card-title"><TrendingUp size={16} /> Discovered Themes</span>
            <span className="badge badge-blue">BERTopic Neural</span>
          </div>
          <div className="kpi-value">{topics.length}</div>
          <div className="kpi-subtext">HDBSCAN Cluster Partition (min_size=3)</div>
        </div>

        <div className="bento-card" style={{ gridColumn: 'span 4' }}>
          <div className="card-header">
            <span className="card-title"><Flame size={16} /> Surging Topics</span>
            <span className="badge badge-amber">&Delta;v/&Delta;t &gt; 0</span>
          </div>
          <div className="kpi-value" style={{ color: surgingCount > 0 ? 'var(--accent-amber)' : 'var(--text-main)' }}>
            {surgingCount}
          </div>
          <div className="kpi-subtext">Positive acceleration in second 24h half</div>
        </div>

        <div className="bento-card" style={{ gridColumn: 'span 4' }}>
          <div className="card-header">
            <span className="card-title"><Zap size={16} /> Max Hourly Velocity</span>
            <span className="badge badge-emerald">posts/hr</span>
          </div>
          <div className="kpi-value">
            {topics.length > 0 ? topics[0].velocity.toFixed(3) : '0.000'}
          </div>
          <div className="kpi-subtext">Peak publication frequency in window</div>
        </div>
      </div>

      {/* Ranked Topic Velocity Table */}
      <div className="bento-card">
        <div className="card-header">
          <span className="card-title">Ranked Topic Velocity & Acceleration Ledger</span>
          <span className="badge badge-cyan">Anchored strictly on posted_at</span>
        </div>

        {topics.length === 0 ? (
          <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <p style={{ margin: 0 }}>No clustered topic records currently found in the 48-hour trailing window.</p>
            <p style={{ margin: '6px 0 0 0', fontSize: '12px' }}>Click "RUN ANALYSIS NOW" on the Overview page to generate fresh neural clusters.</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto', marginTop: '12px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                  <th style={{ padding: '12px 14px' }}>RANK</th>
                  <th style={{ padding: '12px 14px' }}>CONVERSATIONAL THEME</th>
                  <th style={{ padding: '12px 14px' }}>POSTS</th>
                  <th style={{ padding: '12px 14px' }}>VELOCITY (v)</th>
                  <th style={{ padding: '12px 14px' }}>ACCELERATION (a)</th>
                  <th style={{ padding: '12px 14px' }}>STATUS</th>
                  <th style={{ padding: '12px 14px' }}>KEY TERMS</th>
                </tr>
              </thead>
              <tbody>
                {topics.map((t) => (
                  <tr 
                    key={t.id}
                    style={{ 
                      borderBottom: '1px solid rgba(30, 41, 59, 0.4)',
                      transition: 'background 0.15s ease',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(30, 41, 59, 0.3)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    <td style={{ padding: '14px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent-blue)' }}>
                      #{t.rank}
                    </td>
                    <td style={{ padding: '14px', fontWeight: 600, color: 'var(--text-main)' }}>
                      {t.topic_label}
                    </td>
                    <td style={{ padding: '14px', fontFamily: 'var(--font-mono)' }}>
                      {t.post_count}
                    </td>
                    <td style={{ padding: '14px', fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
                      {t.velocity.toFixed(4)} /hr
                    </td>
                    <td style={{ padding: '14px', fontFamily: 'var(--font-mono)', color: t.acceleration > 0 ? '#34d399' : '#94a3b8' }}>
                      {t.acceleration > 0 ? `+${t.acceleration.toFixed(4)}` : t.acceleration.toFixed(4)}
                    </td>
                    <td style={{ padding: '14px' }}>
                      {t.is_surging ? (
                        <span className="badge badge-amber">
                          <Flame size={11} /> SURGING
                        </span>
                      ) : (
                        <span className="badge badge-gray">STABLE</span>
                      )}
                    </td>
                    <td style={{ padding: '14px' }}>
                      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                        {(t.topic_keywords || []).slice(0, 3).map((kw, i) => (
                          <span key={i} className="badge badge-blue" style={{ fontSize: '10px' }}>
                            {kw}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
