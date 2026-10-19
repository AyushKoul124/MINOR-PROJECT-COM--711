import React, { useState } from 'react';
import { 
  Activity, 
  Radio, 
  TrendingUp, 
  Users, 
  Network, 
  Search, 
  ShieldCheck, 
  Database,
  Layers
} from 'lucide-react';

import Overview from './views/Overview';
import SentimentTimeline from './views/SentimentTimeline';
import TrendExplorer from './views/TrendExplorer';
import Demographics from './views/Demographics';
import NetworkGraph from './views/NetworkGraph';
import DataSources from './views/DataSources';
import QueryPanel from './views/QueryPanel';

const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', icon: Layers, desc: 'Executive Telemetry & KPI Bento' },
  { id: 'sentiment', label: 'Sentiment & Stance', icon: Activity, desc: 'XLM-RoBERTa, GoEmotions & DistilBART' },
  { id: 'trends', label: 'Trend Velocity', icon: TrendingUp, desc: 'BERTopic Clustering, Velocity & Acceleration' },
  { id: 'demographics', label: 'Demographics (DPDP)', icon: Users, desc: 'Heuristic Bio-Parser & k-Anonymity (k>=50)' },
  { id: 'network', label: 'Network & CIB', icon: Network, desc: 'Louvain Modularity & 3-Signal CIB Screening' },
  { id: 'datasources', label: 'Monitored Feeds', icon: Radio, desc: '30 Telegram Channels & Ingestion State' },
  { id: 'rag', label: 'RAG Terminal', icon: Search, desc: 'Grounded Retrieval (<0.65 Cutoff) & Audit Log' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');

  const currentNav = NAV_ITEMS.find((n) => n.id === activeTab) || NAV_ITEMS[0];

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo-badge">
            <div className="logo-icon">
              <ShieldCheck size={20} color="#ffffff" />
            </div>
            <div className="logo-text">
              <h1>SOCMINT-AI</h1>
              <span>NTRO TESTBED v4.8</span>
            </div>
          </div>
        </div>

        <ul className="nav-menu">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <li key={item.id} className="nav-item">
                <button
                  className={isActive ? 'active' : ''}
                  onClick={() => setActiveTab(item.id)}
                >
                  <Icon size={16} />
                  <span>{item.label}</span>
                </button>
              </li>
            );
          })}
        </ul>

        <div className="sidebar-footer">
          <div style={{ color: 'var(--accent-emerald)', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10b981' }} />
            OFFLINE READY
          </div>
          <div>GTX 1650 Ti / 4GB VRAM</div>
          <div style={{ color: 'var(--text-dim)', fontSize: '10px', marginTop: '2px' }}>Dec 2026 Viva Defense</div>
        </div>
      </aside>

      {/* Main Analytical View Area */}
      <main className="main-content">
        <header className="top-bar">
          <div className="view-title-group">
            <h2>{currentNav.label}</h2>
            <p>{currentNav.desc}</p>
          </div>

          <div className="top-actions">
            <div style={{ 
              fontFamily: 'var(--font-mono)', 
              fontSize: '11px', 
              color: 'var(--text-muted)', 
              background: 'var(--bg-surface)', 
              padding: '6px 12px', 
              borderRadius: '6px',
              border: '1px solid var(--border-subtle)'
            }}>
              POSTED_AT UTC ANCHORED
            </div>
          </div>
        </header>

        <section className="page-body">
          {activeTab === 'overview' && <Overview onNavigate={setActiveTab} />}
          {activeTab === 'sentiment' && <SentimentTimeline />}
          {activeTab === 'trends' && <TrendExplorer />}
          {activeTab === 'demographics' && <Demographics />}
          {activeTab === 'network' && <NetworkGraph />}
          {activeTab === 'datasources' && <DataSources />}
          {activeTab === 'rag' && <QueryPanel />}
        </section>
      </main>
    </div>
  );
}
