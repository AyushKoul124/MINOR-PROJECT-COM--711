import React, { useState, useEffect } from 'react';
import { Radio, ShieldCheck, Clock, ExternalLink, Activity, Database } from 'lucide-react';
import { fetchDataSources } from '../api';

export default function DataSources() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const res = await fetchDataSources();
        setData(res);
      } catch (err) {
        console.error('Failed to load data sources:', err);
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
        <span>Loading Telegram Channel Sources & Ingestion Telemetry...</span>
      </div>
    );
  }

  const channels = data?.channels || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Ingestion Telemetry Banner */}
      <div className="bento-grid">
        <div className="bento-card" style={{ gridColumn: 'span 3' }}>
          <div className="card-header">
            <span className="card-title">Curated Sources</span>
            <span className="badge badge-blue">{data?.total_channels || 0} TOTAL</span>
          </div>
          <div className="kpi-value">{data?.active_channels || 0}</div>
          <div className="kpi-subtext">Active MTProto Channels</div>
        </div>

        <div className="bento-card" style={{ gridColumn: 'span 3' }}>
          <div className="card-header">
            <span className="card-title">Celery Beat Schedule</span>
            <span className="badge badge-purple">{data?.poll_schedule_seconds || 1200}s</span>
          </div>
          <div className="kpi-value">20 min</div>
          <div className="kpi-subtext">Staggered Polling Cycle</div>
        </div>

        <div className="bento-card" style={{ gridColumn: 'span 3' }}>
          <div className="card-header">
            <span className="card-title">Anti-Flood Jitter</span>
            <span className="badge badge-emerald">ACTIVE</span>
          </div>
          <div className="kpi-value">{data?.jitter_range || '2-5s'}</div>
          <div className="kpi-subtext">Rate-Limit Randomization</div>
        </div>

        <div className="bento-card" style={{ gridColumn: 'span 3' }}>
          <div className="card-header">
            <span className="card-title">Pyrofork Concurrency</span>
            <span className="badge badge-amber">LOCKED</span>
          </div>
          <div className="kpi-value">1</div>
          <div className="kpi-subtext">Prevents SQLite Session Lock</div>
        </div>
      </div>

      {/* Monitored Channels Table */}
      <div className="bento-card">
        <div className="card-header">
          <span className="card-title"><Radio size={16} /> Monitored Public Telegram Channels</span>
          <span className="badge badge-cyan">{channels.length} Curated Endpoints</span>
        </div>

        <div style={{ overflowX: 'auto', marginTop: '12px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                <th style={{ padding: '12px 14px' }}>IDENTIFIER</th>
                <th style={{ padding: '12px 14px' }}>FEED TITLE</th>
                <th style={{ padding: '12px 14px' }}>TOPIC TAGS</th>
                <th style={{ padding: '12px 14px' }}>POSTS STORED</th>
                <th style={{ padding: '12px 14px' }}>LAST POLLED (UTC)</th>
                <th style={{ padding: '12px 14px' }}>STATUS</th>
              </tr>
            </thead>
            <tbody>
              {channels.map((ch) => (
                <tr 
                  key={ch.id}
                  style={{ 
                    borderBottom: '1px solid rgba(30, 41, 59, 0.4)',
                    transition: 'background 0.15s ease',
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(30, 41, 59, 0.3)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <td style={{ padding: '14px', fontFamily: 'var(--font-mono)', color: 'var(--accent-blue)', fontWeight: 600 }}>
                    {ch.identifier}
                  </td>
                  <td style={{ padding: '14px', color: 'var(--text-main)', fontWeight: 600 }}>
                    {ch.display_name}
                  </td>
                  <td style={{ padding: '14px' }}>
                    <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                      {(ch.topic_tags || []).map((tag, i) => (
                        <span key={i} className="badge badge-purple" style={{ fontSize: '10px' }}>
                          {tag}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td style={{ padding: '14px', fontFamily: 'var(--font-mono)' }}>
                    {ch.total_posts_collected}
                  </td>
                  <td style={{ padding: '14px', fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-muted)' }}>
                    {ch.last_polled_at ? new Date(ch.last_polled_at).toLocaleTimeString() : 'Pending'}
                  </td>
                  <td style={{ padding: '14px' }}>
                    {ch.is_active ? (
                      <span className="badge badge-emerald">ACTIVE</span>
                    ) : (
                      <span className="badge badge-gray">PAUSED</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
