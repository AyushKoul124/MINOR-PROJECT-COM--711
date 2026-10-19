import React, { useState, useEffect } from 'react';
import { 
  Play, 
  Activity, 
  Radio, 
  Database, 
  Clock, 
  ShieldCheck, 
  CheckCircle2, 
  AlertCircle,
  TrendingUp,
  Users,
  Network
} from 'lucide-react';
import { fetchOverview, triggerVivaAnalysis, fetchHealth } from '../api';

export default function Overview({ onNavigate }) {
  const [metrics, setMetrics] = useState(null);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [triggerResult, setTriggerResult] = useState(null);

  const loadData = async () => {
    try {
      const [ovData, healthData] = await Promise.all([fetchOverview(), fetchHealth()]);
      setMetrics(ovData);
      setHealth(healthData);
    } catch (err) {
      console.error('Error fetching overview:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleRunVivaAnalysis = async () => {
    setTriggering(true);
    setTriggerResult(null);
    try {
      const result = await triggerVivaAnalysis(50, 48);
      setTriggerResult(result);
      await loadData();
    } catch (err) {
      console.error('Error triggering live analysis:', err);
    } finally {
      setTriggering(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '400px', color: 'var(--text-muted)' }}>
        <Activity className="animate-spin" size={32} style={{ marginRight: '12px' }} />
        <span>Loading SOCMINT Executive Telemetry...</span>
      </div>
    );
  }

  const total = metrics?.total_posts || 0;
  const processed = metrics?.processed_posts || 0;
  const pending = metrics?.pending_posts || 0;
  const posCount = metrics?.sentiment_distribution?.positive || 0;
  const negCount = metrics?.sentiment_distribution?.negative || 0;
  const neuCount = metrics?.sentiment_distribution?.neutral || 0;
  const sentTotal = posCount + negCount + neuCount || 1;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Top Banner Ribbon */}
      <div style={{
        background: 'linear-gradient(90deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.9))',
        border: '1px solid var(--border-subtle)',
        borderRadius: '12px',
        padding: '20px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        boxShadow: 'var(--shadow-md)'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span className="badge badge-emerald">
              <ShieldCheck size={12} /> AIR-GAPPED VIVA TESTBED
            </span>
            <span className="badge badge-blue">
              DEVICE: {health?.device?.toUpperCase() || 'CPU'}
            </span>
            <span className="badge badge-gray">
              INVARIANT: &le; 50 POSTS / 15-25s
            </span>
          </div>
          <h3 style={{ margin: '8px 0 4px 0', fontSize: '18px', fontWeight: 600 }}>
            NTRO Social Media Intelligence & Analytics Framework
          </h3>
          <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-muted)' }}>
            Real-time multi-channel monitoring across 30 curated space, defense, and strategic policy channels.
          </p>
        </div>

        <button 
          className="btn-trigger-viva"
          onClick={handleRunVivaAnalysis}
          disabled={triggering}
        >
          {triggering ? (
            <>
              <Activity className="animate-spin" size={16} />
              <span>RUNNING ANALYSIS...</span>
            </>
          ) : (
            <>
              <Play size={16} fill="currentColor" />
              <span>RUN ANALYSIS NOW</span>
            </>
          )}
        </button>
      </div>

      {/* Trigger Feedback Banner */}
      {triggerResult && (
        <div style={{
          background: 'rgba(16, 185, 129, 0.1)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          borderRadius: '8px',
          padding: '14px 20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          color: '#34d399',
          fontFamily: 'var(--font-mono)',
          fontSize: '13px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <CheckCircle2 size={18} />
            <span>
              LIVE RUN SUCCESSFUL: Completed in {triggerResult.total_elapsed_seconds}s 
              (Timing Invariant: {triggerResult.meets_demo_timing_invariant ? 'PASS (<=30s)' : 'NON-CRITICAL DELAY'}).
            </span>
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            Finished at {new Date(triggerResult.completed_at).toLocaleTimeString()}
          </span>
        </div>
      )}

      {/* Primary KPI Row */}
      <div className="bento-grid">
        <div className="bento-card" style={{ gridColumn: 'span 3' }}>
          <div className="card-header">
            <span className="card-title"><Radio size={16} /> Monitored Channels</span>
            <span className="badge badge-blue">ACTIVE</span>
          </div>
          <div className="kpi-value">{metrics?.active_channels || 30}</div>
          <div className="kpi-subtext">Curated Indian Defense & Space Feeds</div>
        </div>

        <div className="bento-card" style={{ gridColumn: 'span 3' }}>
          <div className="card-header">
            <span className="card-title"><Database size={16} /> Total Ingested Posts</span>
            <span className="badge badge-emerald">STORED</span>
          </div>
          <div className="kpi-value">{total}</div>
          <div className="kpi-subtext">PostgreSQL 16 Raw Store</div>
        </div>

        <div className="bento-card" style={{ gridColumn: 'span 3' }}>
          <div className="card-header">
            <span className="card-title"><Activity size={16} /> Processed Analytics</span>
            <span className="badge badge-cyan">{processed} / {total}</span>
          </div>
          <div className="kpi-value">{processed}</div>
          <div className="kpi-subtext">Enriched with Sentiment & Stance</div>
        </div>

        <div className="bento-card" style={{ gridColumn: 'span 3' }}>
          <div className="card-header">
            <span className="card-title"><Clock size={16} /> Pending Queue</span>
            <span className="badge badge-amber">{pending} ROWS</span>
          </div>
          <div className="kpi-value" style={{ color: pending > 0 ? 'var(--accent-amber)' : 'var(--text-main)' }}>
            {pending}
          </div>
          <div className="kpi-subtext">Ready for Component B Runner</div>
        </div>

        {/* Sentiment Distribution Card */}
        <div className="bento-card" style={{ gridColumn: 'span 6' }}>
          <div className="card-header">
            <span className="card-title"><Activity size={16} /> Multilingual Sentiment Valence</span>
            <span className="badge badge-blue">XLM-RoBERTa</span>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '10px' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '6px' }}>
                <span style={{ color: '#34d399', fontWeight: 600 }}>POSITIVE ({posCount})</span>
                <span>{((posCount / sentTotal) * 100).toFixed(1)}%</span>
              </div>
              <div style={{ width: '100%', height: '8px', background: 'var(--bg-surface)', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ width: `${(posCount / sentTotal) * 100}%`, height: '100%', background: 'var(--accent-emerald)', borderRadius: '4px' }} />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '6px' }}>
                <span style={{ color: '#60a5fa', fontWeight: 600 }}>NEUTRAL ({neuCount})</span>
                <span>{((neuCount / sentTotal) * 100).toFixed(1)}%</span>
              </div>
              <div style={{ width: '100%', height: '8px', background: 'var(--bg-surface)', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ width: `${(neuCount / sentTotal) * 100}%`, height: '100%', background: 'var(--accent-blue)', borderRadius: '4px' }} />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '6px' }}>
                <span style={{ color: '#fb7185', fontWeight: 600 }}>NEGATIVE ({negCount})</span>
                <span>{((negCount / sentTotal) * 100).toFixed(1)}%</span>
              </div>
              <div style={{ width: '100%', height: '8px', background: 'var(--bg-surface)', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ width: `${(negCount / sentTotal) * 100}%`, height: '100%', background: 'var(--accent-rose)', borderRadius: '4px' }} />
              </div>
            </div>
          </div>
        </div>

        {/* Emotion Distribution Card */}
        <div className="bento-card" style={{ gridColumn: 'span 6' }}>
          <div className="card-header">
            <span className="card-title"><Activity size={16} /> Dominant Ekman Emotions</span>
            <span className="badge badge-purple">GoEmotions</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginTop: '10px' }}>
            {Object.entries(metrics?.top_emotions || {}).map(([emotion, count]) => (
              <div 
                key={emotion}
                style={{
                  background: 'var(--bg-surface)',
                  borderRadius: '8px',
                  padding: '12px',
                  border: '1px solid var(--border-subtle)',
                  textAlign: 'center'
                }}
              >
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                  {emotion}
                </div>
                <div style={{ fontSize: '20px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-main)', marginTop: '4px' }}>
                  {count}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Component Navigation Quick Cards */}
        <div className="bento-card" style={{ gridColumn: 'span 4', cursor: 'pointer' }} onClick={() => onNavigate('trends')}>
          <div className="card-header">
            <span className="card-title"><TrendingUp size={16} /> Trend Velocity (D)</span>
            <span className="badge badge-amber">&Delta;posts/&Delta;t</span>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: 0 }}>
            BERTopic neural clustering with hourly velocity and acceleration tracking.
          </p>
        </div>

        <div className="bento-card" style={{ gridColumn: 'span 4', cursor: 'pointer' }} onClick={() => onNavigate('demographics')}>
          <div className="card-header">
            <span className="card-title"><Users size={16} /> Demographics (C)</span>
            <span className="badge badge-emerald">k &ge; 50 DPDP</span>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: 0 }}>
            Heuristic bio-parser, diurnal rhythm analysis, and privacy suppression guards.
          </p>
        </div>

        <div className="bento-card" style={{ gridColumn: 'span 4', cursor: 'pointer' }} onClick={() => onNavigate('network')}>
          <div className="card-header">
            <span className="card-title"><Network size={16} /> Network Graph (E)</span>
            <span className="badge badge-rose">3-Signal CIB</span>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: 0 }}>
            Louvain community partitioning with advisory CIB anomaly screening flags.
          </p>
        </div>
      </div>
    </div>
  );
}
