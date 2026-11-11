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
import { fetchOverview, triggerVivaAnalysis } from '../api';

export default function Overview({ onNavigate }) {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [triggerResult, setTriggerResult] = useState(null);
  const [triggerError, setTriggerError] = useState(null);

  const loadData = async () => {
    try {
      const ovData = await fetchOverview();
      setMetrics(ovData);
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
    setTriggerError(null);
    try {
      const result = await triggerVivaAnalysis(50, 48);
      setTriggerResult(result);
      await loadData();
    } catch (err) {
      console.error('Error triggering live analysis:', err);
      setTriggerError(
        err?.message ||
          'Analysis request failed. Start the API (uvicorn port 8000) and restart npm run dev after editing frontend/.env.'
      );
    } finally {
      setTriggering(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '400px', color: 'var(--text-muted)' }}>
        <Activity className="animate-spin" size={32} style={{ marginRight: '12px' }} />
        <span>Loading the overview...</span>
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
    <div className="view-stack">
      <div className="hero-ribbon">
        <div>
          <div className="badge-row">
            <span className="badge badge-emerald">
              <ShieldCheck size={12} /> Public channels
            </span>
            {triggering && (
              <span className="badge badge-cyan">The first run can take a few minutes</span>
            )}
          </div>
          <h3>
            Audience <em>Intel</em>
          </h3>
          <p>
            A read of public Telegram posts: how they feel, what they are about, who is talking, and how those accounts connect.
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

      {triggerError && (
        <div className="alert-banner alert-bad">
          <AlertCircle size={18} />
          <span>{triggerError}</span>
        </div>
      )}

      {/* Trigger Feedback Banner */}
      {triggerResult?.total_elapsed_seconds != null && (
        <div className="alert-banner alert-ok">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <CheckCircle2 size={18} />
            <span>
              Analysis finished in {triggerResult.total_elapsed_seconds}s.
            </span>
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            Finished at {new Date(triggerResult.completed_at).toLocaleTimeString()}
          </span>
        </div>
      )}

      {/* Primary KPI Row */}
      <div className="bento-grid">
        <div className="bento-card span-3">
          <div className="card-header">
            <span className="card-title"><Radio size={16} /> Monitored Channels</span>
            <span className="badge badge-blue">ACTIVE</span>
          </div>
          <div className="kpi-value">{metrics?.active_channels || 30}</div>
          <div className="kpi-subtext">Public Telegram channels</div>
        </div>

        <div className="bento-card span-3">
          <div className="card-header">
            <span className="card-title"><Database size={16} /> Posts saved</span>
            <span className="badge badge-emerald">STORED</span>
          </div>
          <div className="kpi-value">{total}</div>
          <div className="kpi-subtext">Posts saved from those channels</div>
        </div>

        <div className="bento-card span-3">
          <div className="card-header">
            <span className="card-title"><Activity size={16} /> Posts read</span>
            <span className="badge badge-cyan">{processed} / {total}</span>
          </div>
          <div className="kpi-value">{processed}</div>
          <div className="kpi-subtext">Enriched with Sentiment & Stance</div>
        </div>

        <div className="bento-card span-3">
          <div className="card-header">
            <span className="card-title"><Clock size={16} /> Pending Queue</span>
            <span className="badge badge-amber">Waiting</span>
          </div>
          <div className="kpi-value" style={{ color: pending > 0 ? 'var(--accent-amber)' : 'var(--text-main)' }}>
            {pending}
          </div>
          <div className="kpi-subtext">Waiting to be read</div>
        </div>

        {/* Sentiment Distribution Card */}
        <div className="bento-card span-6">
          <div className="card-header">
            <span className="card-title"><Activity size={16} /> Sentiment</span>
          </div>
          <div className="stack-sm">
            <div className="meter">
              <div className="meter-label"><span style={{ color: '#34d399' }}>POSITIVE ({posCount})</span><span>{((posCount / sentTotal) * 100).toFixed(1)}%</span></div>
              <div className="meter-track"><div className="meter-fill pos" style={{ width: `${(posCount / sentTotal) * 100}%` }} /></div>
            </div>
            <div className="meter">
              <div className="meter-label"><span style={{ color: '#38bdf8' }}>NEUTRAL ({neuCount})</span><span>{((neuCount / sentTotal) * 100).toFixed(1)}%</span></div>
              <div className="meter-track"><div className="meter-fill neu" style={{ width: `${(neuCount / sentTotal) * 100}%` }} /></div>
            </div>
            <div className="meter">
              <div className="meter-label"><span style={{ color: '#fb7185' }}>NEGATIVE ({negCount})</span><span>{((negCount / sentTotal) * 100).toFixed(1)}%</span></div>
              <div className="meter-track"><div className="meter-fill neg" style={{ width: `${(negCount / sentTotal) * 100}%` }} /></div>
            </div>
          </div>
        </div>

        {/* Emotion Distribution Card */}
        <div className="bento-card span-6">
          <div className="card-header">
            <span className="card-title"><Activity size={16} /> Emotions</span>
          </div>
          <div className="tile-grid">
            {Object.entries(metrics?.top_emotions || {}).map(([emotion, count]) => (
              <div key={emotion} className="stat-tile">
                <div className="label">{emotion}</div>
                <div className="value">{count}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="bento-card span-4 click-card" onClick={() => onNavigate('trends')}>
          <div className="card-header">
            <span className="card-title"><TrendingUp size={16} /> Topics</span>
          </div>
          <p>Themes in the posts, and which ones are speeding up or slowing down.</p>
        </div>

        <div className="bento-card span-4 click-card" onClick={() => onNavigate('demographics')}>
          <div className="card-header">
            <span className="card-title"><Users size={16} /> Audience</span>
            <span className="badge badge-emerald">Audience</span>
          </div>
          <p>Aggregate audience cards with age, geography, and interest breakdowns.</p>
        </div>

        <div className="bento-card span-4 click-card" onClick={() => onNavigate('network')}>
          <div className="card-header">
            <span className="card-title"><Network size={16} /> Network</span>
          </div>
          <p>Groups of accounts, and posts that move together.</p>
        </div>
      </div>
    </div>
  );
}
