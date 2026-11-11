import React, { useState } from 'react';

import Overview from './views/Overview';
import SentimentTimeline from './views/SentimentTimeline';
import TrendExplorer from './views/TrendExplorer';
import Demographics from './views/Demographics';
import NetworkGraph from './views/NetworkGraph';
import DataSources from './views/DataSources';
import QueryPanel from './views/QueryPanel';

const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', desc: 'Channels, posts, and the latest read' },
  { id: 'sentiment', label: 'Sentiment', desc: 'How the posts feel, and where they stand' },
  { id: 'trends', label: 'Trends', desc: 'What people are talking about, and how fast' },
  { id: 'demographics', label: 'Audience', desc: 'Age, place, language, and interests' },
  { id: 'network', label: 'Network', desc: 'Who is connected to whom' },
  { id: 'datasources', label: 'Sources', desc: 'Public Telegram channels' },
  { id: 'rag', label: 'Ask', desc: 'Answers drawn from the collected posts' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const currentNav = NAV_ITEMS.find((n) => n.id === activeTab) || NAV_ITEMS[0];

  return (
    <div className="site">
      <header className="mast">
        <div className="mast-top">
          <div className="brand">
            <span className="brand-mark">AU</span>
            <div>
              <strong>AUDIENCE</strong>
              <small>Public Telegram intelligence</small>
            </div>
          </div>
          <div className="mast-side">
            <span className="live-dot" />
            Watching public channels
          </div>
        </div>
        <nav className="mast-nav" aria-label="Dashboard views">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={activeTab === item.id ? 'active' : ''}
              onClick={() => setActiveTab(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </header>

      <div className="stage">
        <header className="stage-bar">
          <div>
            <p className="crumb">{currentNav.label}</p>
            <h1>{currentNav.label}</h1>
            <p className="stage-desc">{currentNav.desc}</p>
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
        </div>
      </div>
  );
}
