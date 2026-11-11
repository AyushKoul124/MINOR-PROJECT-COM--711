import React, { useState, useEffect } from 'react';
import { Radio, Activity } from 'lucide-react';
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
        <span>Loading channels...</span>
      </div>
    );
  }

  const channels = data?.channels || [];
  const postsStored = channels.reduce((sum, ch) => sum + (ch.total_posts_collected || 0), 0);
  const topicCount = new Set(channels.flatMap((ch) => ch.topic_tags || [])).size;
  const lastCheck = channels
    .map((ch) => ch.last_polled_at)
    .filter(Boolean)
    .sort()
    .at(-1);

  return (
    <div className="view-stack">
      {/* Ingestion Telemetry Banner */}
      <div className="bento-grid">
        <div className="bento-card span-3">
          <div className="card-header">
            <span className="card-title">Curated Sources</span>
            <span className="badge badge-blue">{data?.total_channels || 0} TOTAL</span>
          </div>
          <div className="kpi-value">{data?.active_channels || 0}</div>
          <div className="kpi-subtext">Public Telegram channels</div>
        </div>

        <div className="bento-card span-3">
          <div className="card-header">
            <span className="card-title">Posts saved</span>
          </div>
          <div className="kpi-value">{postsStored}</div>
          <div className="kpi-subtext">Across these channels</div>
        </div>

        <div className="bento-card span-3">
          <div className="card-header">
            <span className="card-title">Topics</span>
          </div>
          <div className="kpi-value">{topicCount}</div>
          <div className="kpi-subtext">Subjects these channels cover</div>
        </div>

        <div className="bento-card span-3">
          <div className="card-header">
            <span className="card-title">Last check</span>
          </div>
          <div className="kpi-value" style={{ fontSize: '28px' }}>
            {lastCheck ? new Date(lastCheck).toLocaleTimeString() : '—'}
          </div>
          <div className="kpi-subtext">Newest channel update</div>
        </div>
      </div>

      {/* Monitored Channels Table */}
      <div className="bento-card">
        <div className="card-header">
          <span className="card-title"><Radio size={16} /> Monitored Public Telegram Channels</span>
          <span className="badge badge-cyan">{channels.length} channels</span>
        </div>

        <div style={{ overflowX: 'auto', marginTop: '12px' }}>
          <table className="data-table">
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                <th style={{ padding: '12px 14px' }}>CHANNEL</th>
                <th style={{ padding: '12px 14px' }}>FEED TITLE</th>
                <th style={{ padding: '12px 14px' }}>TOPIC TAGS</th>
                <th style={{ padding: '12px 14px' }}>POSTS STORED</th>
                <th style={{ padding: '12px 14px' }}>LAST CHECK</th>
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
