import React, { useState, useEffect } from 'react';
import { Users, Shield, Clock, Globe, BookOpen, AlertTriangle, Activity } from 'lucide-react';
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
        <span>Loading Audience Demographics & DPDP Privacy Guards...</span>
      </div>
    );
  }

  const clusters = data?.clusters || [];
  const kThreshold = data?.k_anonymity_threshold || 50;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* DPDP Section 6 Compliance Banner */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.8)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '12px',
        padding: '16px 20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ 
            width: '36px', 
            height: '36px', 
            borderRadius: '8px', 
            background: 'rgba(16, 185, 129, 0.15)', 
            border: '1px solid rgba(16, 185, 129, 0.3)',
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            color: '#34d399'
          }}>
            <Shield size={20} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)' }}>
                Digital Personal Data Protection (DPDP) Act 2023 — Section 6 Privacy Guard
              </span>
              <span className="badge badge-emerald">k &ge; {kThreshold} Compliant</span>
            </div>
            <p style={{ margin: '3px 0 0 0', fontSize: '12px', color: 'var(--text-muted)' }}>
              Demographic clusters below {kThreshold} observable accounts are suppressed via data minimization principles. Coarse heuristic proxy only.
            </p>
          </div>
        </div>

        <div style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
          <div>Clusters Evaluated: <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>{data?.total_clusters || 0}</span></div>
          <div style={{ color: 'var(--accent-rose)' }}>Suppressed: {data?.suppressed_clusters || 0}</div>
        </div>
      </div>

      {/* Diurnal Rhythm Card */}
      <div className="bento-card">
        <div className="card-header">
          <span className="card-title"><Clock size={16} /> Broadcast Diurnal Rhythm (UTC &rarr; IST Grounding)</span>
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
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Operational Peak Window</span>
            <div style={{ fontSize: '15px', fontWeight: 600, fontFamily: 'var(--font-mono)', marginTop: '6px', color: '#34d399' }}>
              {data?.diurnal_rhythm_ist?.peak_hour_ist || '14:00 - 18:00 IST'}
            </div>
          </div>
        </div>
      </div>

      {/* Demographic Clusters Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px' }}>
        {clusters.map((c) => {
          const isSuppressed = c.below_threshold;

          return (
            <div 
              key={c.id} 
              className={`bento-card ${isSuppressed ? 'sub-threshold-card' : ''}`}
            >
              <div className="card-header">
                <div>
                  <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: 'var(--text-main)' }}>
                    {c.cluster_label}
                  </h4>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    Sample Size: {c.account_count} accounts
                  </span>
                </div>

                {isSuppressed ? (
                  <span className="badge badge-gray">
                    <AlertTriangle size={11} /> BELOW THRESHOLD
                  </span>
                ) : (
                  <span className="badge badge-emerald">
                    <Shield size={11} /> k &ge; {kThreshold} PASS
                  </span>
                )}
              </div>

              {isSuppressed ? (
                <div style={{
                  padding: '20px',
                  background: 'rgba(30, 41, 59, 0.4)',
                  borderRadius: '8px',
                  border: '1px dashed var(--border-subtle)',
                  textAlign: 'center',
                  color: 'var(--text-muted)',
                  fontSize: '12px'
                }}>
                  <AlertTriangle size={24} style={{ color: 'var(--accent-amber)', marginBottom: '8px' }} />
                  <p style={{ margin: 0, fontWeight: 600, color: 'var(--text-main)' }}>
                    DPDP Section 6 Data Minimization Guard Active
                  </p>
                  <p style={{ margin: '4px 0 0 0' }}>
                    Cluster size ({c.account_count} accounts) is below the privacy threshold (k = {kThreshold}).
                    Detailed individual demographic breakdowns are suppressed.
                  </p>
                </div>
              ) : (
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
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Geographic Inferences</span>
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
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
