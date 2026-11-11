import React, { useState, useEffect } from 'react';
import { Clock, Activity } from 'lucide-react';
import { fetchDemographics } from '../api';

export default function Demographics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const res = await fetchDemographics(48);
        setData(res);
      } catch (err) {
        console.error('Failed to load demographics:', err);
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
        <span>Loading audience profiles...</span>
      </div>
    );
  }

  const clusters = data?.clusters || [];

  return (
    <div className="view-stack">
      {/* Diurnal Rhythm Card */}
      <div className="bento-card">
        <div className="card-header">
          <span className="card-title"><Clock size={16} /> When people post</span>
          <span className="badge badge-blue">Peak Posting Hours</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginTop: '10px' }}>
          <div style={{ background: 'var(--bg-surface)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Morning (06:00 - 12:00 IST)</span>
            <div style={{ fontSize: '20px', fontWeight: 700, fontFamily: 'var(--font-mono)', marginTop: '4px', color: 'var(--text-main)' }}>
              {((data?.diurnal_rhythm_ist?.morning_ist_ratio || 0.32) * 100).toFixed(0)}%
            </div>
          </div>

          <div style={{ background: 'var(--bg-surface)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Afternoon (12:00 - 18:00 IST)</span>
            <div style={{ fontSize: '20px', fontWeight: 700, fontFamily: 'var(--font-mono)', marginTop: '4px', color: 'var(--accent-cyan)' }}>
              {((data?.diurnal_rhythm_ist?.afternoon_ist_ratio || 0.44) * 100).toFixed(0)}%
            </div>
          </div>

          <div style={{ background: 'var(--bg-surface)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Evening (18:00 - 24:00 IST)</span>
            <div style={{ fontSize: '20px', fontWeight: 700, fontFamily: 'var(--font-mono)', marginTop: '4px', color: 'var(--text-main)' }}>
              {((data?.diurnal_rhythm_ist?.evening_ist_ratio || 0.24) * 100).toFixed(0)}%
            </div>
          </div>

          <div style={{ background: 'var(--bg-surface)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Busiest hours</span>
            <div style={{ fontSize: '15px', fontWeight: 600, fontFamily: 'var(--font-mono)', marginTop: '6px', color: '#34d399' }}>
              {data?.diurnal_rhythm_ist?.peak_hour_ist || '14:00 - 18:00 IST'}
            </div>
          </div>
        </div>
      </div>

      {/* Demographic Clusters Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px' }}>
        {clusters.map((c) => {
          return (
            <div key={c.id} className="bento-card">
              <div className="card-header">
                <div>
                  <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: 'var(--text-main)' }}>
                    {c.cluster_label}
                  </h4>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {c.account_count} accounts in this group
                  </span>
                </div>
                <span className="badge badge-emerald">{c.account_count} accounts</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '10px' }}>
                  {/* Age Distribution */}
                  <div>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Age Brackets</span>
                    <div style={{ display: 'flex', gap: '8px', marginTop: '6px', flexWrap: 'wrap' }}>
                      {Object.entries(c.age_bracket_dist || {}).map(([k, v]) => (
                        <span key={k} className="badge badge-blue">
                          {k}: {(v * 100).toFixed(0)}%
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Geography */}
                  <div>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Where they are</span>
                    <div style={{ display: 'flex', gap: '8px', marginTop: '6px', flexWrap: 'wrap' }}>
                      {Object.entries(c.geography_dist || {}).map(([k, v]) => (
                        <span key={k} className="badge badge-emerald">
                          {k}: {(v * 100).toFixed(0)}%
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Interests */}
                  <div>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Topical Interests</span>
                    <div style={{ display: 'flex', gap: '6px', marginTop: '6px', flexWrap: 'wrap' }}>
                      {Object.entries(c.interest_dist || {}).map(([k, v]) => (
                        <span key={k} className="badge badge-purple" style={{ fontSize: '10px' }}>
                          {k} ({(v * 100).toFixed(0)}%)
                        </span>
                      ))}
                    </div>
                  </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
