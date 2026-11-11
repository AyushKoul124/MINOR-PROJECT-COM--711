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
  const rhythm = data?.diurnal_rhythm_ist || {};
  const hours = Array.isArray(rhythm.hourly_counts) ? rhythm.hourly_counts : [];
  const peakCount = Math.max(1, ...hours, 0);
  const peakHour = typeof rhythm.peak_hour_ist === 'string' ? rhythm.peak_hour_ist.slice(0, 2) : '';

  const phases = [
    ['Morning', '06:00–12:00', rhythm.morning_ist_ratio || 0],
    ['Afternoon', '12:00–18:00', rhythm.afternoon_ist_ratio || 0],
    ['Evening', '18:00–23:00', rhythm.evening_ist_ratio || 0],
    ['Night', '23:00–06:00', rhythm.night_ist_ratio || 0],
  ];

  return (
    <div className="view-stack">
      <div className="bento-card">
        <div className="card-header">
          <span className="card-title"><Clock size={16} /> When people post</span>
          <span className="badge badge-blue">{rhythm.peak_hour_ist || 'No posts yet'}</span>
        </div>
        <p style={{ margin: '8px 0 0', color: 'var(--text-muted)', fontSize: '13px' }}>
          Posts in the last 48 hours, by hour in India Standard Time. {rhythm.posts || 0} posts.
        </p>
        <div className="hour-chart" role="img" aria-label="Posts by hour in India Standard Time">
          {hours.map((count, hour) => {
            const label = String(hour).padStart(2, '0');
            return (
              <div
                key={hour}
                className={label === peakHour ? 'hour-col peak' : 'hour-col'}
                title={`${label}:00 IST, ${count} posts`}
              >
                <div className="hour-bar" style={{ height: `${Math.max(2, (count / peakCount) * 100)}%` }} />
                <em>{hour % 3 === 0 ? label : ''}</em>
              </div>
            );
          })}
        </div>
        <div className="phase-row">
          {phases.map(([name, span, ratio]) => (
            <div key={name} className="phase-box">
              <span>{name} ({span})</span>
              <strong>{Math.round(ratio * 100)}%</strong>
            </div>
          ))}
        </div>
      </div>

      <div className="audience-cards">
        {clusters.length === 0 && (
          <div className="bento-card">
            <p style={{ margin: 0, color: 'var(--text-muted)' }}>No audience snapshot in this window yet.</p>
          </div>
        )}
        {clusters.map((c) => (
          <div key={c.id} className="bento-card">
            <div className="card-header">
              <div>
                <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 600 }}>{c.cluster_label}</h4>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  {c.account_count} accounts in this group
                </span>
              </div>
              <span className={c.below_threshold ? 'badge badge-amber' : 'badge badge-emerald'}>
                {c.below_threshold ? 'Below 50' : `${c.account_count} accounts`}
              </span>
            </div>
            {c.account_count < 1 ? (
              <p style={{ margin: '12px 0 0', color: 'var(--text-muted)', fontSize: '13px' }}>
                Nobody spoke under a public name in this window, so there is no age, place, or interest breakdown.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '12px' }}>
                <Dist title="Age" rows={c.age_bracket_dist} />
                <Dist title="Where they are" rows={c.geography_dist} />
                <Dist title="Language" rows={c.language_dist} />
                <Dist title="Interests" rows={c.interest_dist} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function Dist({ title, rows }) {
  const entries = Object.entries(rows || {}).filter(([, value]) => value > 0);
  if (entries.length === 0) return null;
  return (
    <div className="dist-row">
      <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>{title}</span>
      {entries.map(([name, value]) => (
        <div key={name} className="dist-line">
          <span>{name}</span>
          <div className="dist-track"><div className="dist-fill" style={{ width: `${Math.round(value * 100)}%` }} /></div>
          <span>{Math.round(value * 100)}%</span>
        </div>
      ))}
    </div>
  );
}
