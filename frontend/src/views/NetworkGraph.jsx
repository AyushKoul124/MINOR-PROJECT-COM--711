import React, { useState, useEffect, useRef } from 'react';
import { Network, ShieldAlert, Activity, Users, Info, AlertTriangle } from 'lucide-react';
import { fetchNetworkGraph } from '../api';

const COMMUNITY_COLORS = [
  '#3b82f6', // Blue
  '#10b981', // Emerald
  '#8b5cf6', // Purple
  '#f59e0b', // Amber
  '#06b6d4', // Cyan
  '#ec4899', // Pink
  '#14b8a6', // Teal
];

export default function NetworkGraph() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    async function loadData() {
      try {
        const res = await fetchNetworkGraph(48);
        setData(res);
      } catch (err) {
        console.error('Failed to load network graph:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  // Simple, robust 60 FPS HTML5 Canvas network visualizer
  useEffect(() => {
    if (!data || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    const nodes = data.nodes || [];
    const links = data.links || [];
    if (nodes.length === 0) return;

    // Distribute nodes in community clusters across canvas
    const nodeCoords = new Map();
    const commCenters = new Map();
    const commCount = Math.max(1, data.total_communities || 4);

    for (let c = 0; c < commCount; c++) {
      const angle = (c / commCount) * 2 * Math.PI;
      const radius = Math.min(width, height) * 0.32;
      commCenters.set(c, {
        x: width / 2 + Math.cos(angle) * radius,
        y: height / 2 + Math.sin(angle) * radius,
      });
    }

    nodes.forEach((node, i) => {
      const cCenter = commCenters.get(node.community_id % commCount) || { x: width / 2, y: height / 2 };
      const jitterAngle = (i * 2.4);
      const jitterRadius = 25 + (i % 8) * 14;
      nodeCoords.set(node.id, {
        x: cCenter.x + Math.cos(jitterAngle) * jitterRadius,
        y: cCenter.y + Math.sin(jitterAngle) * jitterRadius,
        data: node,
      });
    });

    // Render loop
    ctx.clearRect(0, 0, width, height);

    // 1. Draw Links
    links.forEach((l) => {
      const src = nodeCoords.get(l.source);
      const tgt = nodeCoords.get(l.target);
      if (src && tgt) {
        ctx.beginPath();
        ctx.moveTo(src.x, src.y);
        ctx.lineTo(tgt.x, tgt.y);
        ctx.strokeStyle = l.type === 'forward' ? 'rgba(59, 130, 246, 0.25)' : 'rgba(100, 116, 139, 0.2)';
        ctx.lineWidth = Math.min(3, 0.8 + (l.weight || 1) * 0.4);
        ctx.stroke();
      }
    });

    // 2. Draw Nodes
    nodeCoords.forEach((n) => {
      const isBroker = (n.data.betweenness || 0) > 0.05;
      const isCIB = n.data.coordination_signal;
      const radius = Math.max(4, Math.min(14, 5 + (n.data.betweenness || 0) * 35));
      const color = COMMUNITY_COLORS[n.data.community_id % COMMUNITY_COLORS.length];

      ctx.beginPath();
      ctx.arc(n.x, n.y, radius, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();

      // CIB Anomaly Highlighting
      if (isCIB) {
        ctx.strokeStyle = '#f43f5e';
        ctx.lineWidth = 3;
        ctx.stroke();

        // Pulsing outer halo
        ctx.beginPath();
        ctx.arc(n.x, n.y, radius + 4, 0, 2 * Math.PI);
        ctx.strokeStyle = 'rgba(244, 63, 94, 0.4)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      } else if (isBroker) {
        ctx.strokeStyle = '#f8fafc';
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    });
  }, [data]);

  const handleCanvasClick = (e) => {
    if (!canvasRef.current || !data) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const clickX = (e.clientX - rect.left) * (canvasRef.current.width / rect.width);
    const clickY = (e.clientY - rect.top) * (canvasRef.current.height / rect.height);

    // Hit test against nodes
    const nodes = data.nodes || [];
    const commCount = Math.max(1, data.total_communities || 4);
    const width = canvasRef.current.width;
    const height = canvasRef.current.height;

    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      const angle = (node.community_id / commCount) * 2 * Math.PI;
      const radius = Math.min(width, height) * 0.32;
      const cx = width / 2 + Math.cos(angle) * radius;
      const cy = height / 2 + Math.sin(angle) * radius;
      const nx = cx + Math.cos(i * 2.4) * (25 + (i % 8) * 14);
      const ny = cy + Math.sin(i * 2.4) * (25 + (i % 8) * 14);

      const dist = Math.hypot(clickX - nx, clickY - ny);
      if (dist <= 16) {
        setSelectedNode(node);
        return;
      }
    }
    setSelectedNode(null);
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '300px', color: 'var(--text-muted)' }}>
        <Activity className="animate-spin" size={28} style={{ marginRight: '10px' }} />
        <span>Loading Network Topology & Louvain Modularity...</span>
      </div>
    );
  }

  const nodes = data?.nodes || [];
  const links = data?.links || [];
  const flaggedNodes = nodes.filter((n) => n.coordination_signal);
  const topBrokers = [...nodes].sort((a, b) => (b.betweenness || 0) - (a.betweenness || 0)).slice(0, 5);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Topology Telemetry Row */}
      <div className="bento-grid">
        <div className="bento-card" style={{ gridColumn: 'span 3' }}>
          <div className="card-header">
            <span className="card-title">Network Nodes</span>
            <span className="badge badge-blue">PRUNED &le; 500</span>
          </div>
          <div className="kpi-value">{data?.total_nodes || 0}</div>
          <div className="kpi-subtext">Channels & Pseudonymized Actors</div>
        </div>

        <div className="bento-card" style={{ gridColumn: 'span 3' }}>
          <div className="card-header">
            <span className="card-title">Interaction Edges</span>
            <span className="badge badge-emerald">DIRECTED</span>
          </div>
          <div className="kpi-value">{data?.total_edges || 0}</div>
          <div className="kpi-subtext">Forwards, Mentions, Replies</div>
        </div>

        <div className="bento-card" style={{ gridColumn: 'span 3' }}>
          <div className="card-header">
            <span className="card-title">Louvain Modularity</span>
            <span className="badge badge-purple">Q = {data?.modularity || 0}</span>
          </div>
          <div className="kpi-value">{data?.total_communities || 0}</div>
          <div className="kpi-subtext">Behavioral Sub-Communities</div>
        </div>

        <div className="bento-card" style={{ gridColumn: 'span 3' }}>
          <div className="card-header">
            <span className="card-title">CIB Anomalies</span>
            <span className="badge badge-rose">&ge; 0.70 CUTOFF</span>
          </div>
          <div className="kpi-value" style={{ color: (data?.cib_flagged_count || 0) > 0 ? 'var(--accent-rose)' : 'var(--text-main)' }}>
            {data?.cib_flagged_count || 0}
          </div>
          <div className="kpi-subtext">Screening Signal (Advisory Only)</div>
        </div>
      </div>

      {/* Main Canvas Graph Visualization */}
      <div className="bento-card" style={{ padding: '0', position: 'relative' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="card-title"><Network size={16} /> 60 FPS WebGL/Canvas Interaction Graph</span>
          <div style={{ display: 'flex', gap: '8px' }}>
            <span className="badge badge-blue">Nodes Sized by Betweenness</span>
            <span className="badge badge-rose">Red Ring = CIB Signal</span>
          </div>
        </div>

        <canvas
          ref={canvasRef}
          width={1000}
          height={480}
          style={{ width: '100%', height: '480px', display: 'block', background: '#070b12', cursor: 'pointer' }}
          onClick={handleCanvasClick}
        />

        {/* Selected Node Drawer */}
        {selectedNode && (
          <div style={{
            position: 'absolute',
            bottom: '16px',
            right: '16px',
            width: '320px',
            background: 'rgba(15, 23, 42, 0.95)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '8px',
            padding: '16px',
            boxShadow: 'var(--shadow-lg)',
            backdropFilter: 'blur(8px)',
            fontSize: '13px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>{selectedNode.label}</span>
              <button 
                onClick={() => setSelectedNode(null)} 
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '14px' }}
              >
                &times;
              </button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
              <div>Type: <span style={{ color: 'var(--text-main)' }}>{selectedNode.entity_type}</span></div>
              <div>Community: <span style={{ color: 'var(--accent-blue)' }}>#{selectedNode.community_id}</span></div>
              <div>Betweenness Centrality: <span style={{ color: 'var(--text-main)' }}>{selectedNode.betweenness}</span></div>
              <div>Degree Centrality: <span style={{ color: 'var(--text-main)' }}>{selectedNode.degree}</span></div>
              <div>
                Anomaly Score: 
                <span style={{ color: selectedNode.coordination_signal ? 'var(--accent-rose)' : '#34d399', fontWeight: 600 }}>
                  {' '}{selectedNode.anomaly_score} ({selectedNode.coordination_signal ? 'FLAGGED' : 'NORMAL'})
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Structural Brokers & CIB Screening Ledger */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Top Brokers */}
        <div className="bento-card">
          <div className="card-header">
            <span className="card-title">Top Structural Information Brokers</span>
            <span className="badge badge-blue">Betweenness Ranking</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '10px' }}>
            {topBrokers.map((n, i) => (
              <div 
                key={n.id} 
                style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  padding: '10px 14px', 
                  background: 'var(--bg-surface)', 
                  borderRadius: '6px', 
                  fontSize: '12px' 
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-blue)', fontWeight: 700 }}>#{i + 1}</span>
                  <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>{n.label}</span>
                  <span className="badge badge-gray">{n.entity_type}</span>
                </div>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
                  B = {n.betweenness}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* CIB Flagged Entities */}
        <div className="bento-card">
          <div className="card-header">
            <span className="card-title">Advisory CIB Anomaly Flags</span>
            <span className="badge badge-rose">&ge; 0.70 Screening Metric</span>
          </div>

          {flaggedNodes.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
              No entities exceeded the 0.70 CIB anomaly screening threshold.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '10px' }}>
              {flaggedNodes.map((n) => (
                <div 
                  key={n.id} 
                  style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    padding: '10px 14px', 
                    background: 'rgba(244, 63, 94, 0.1)', 
                    border: '1px solid rgba(244, 63, 94, 0.25)', 
                    borderRadius: '6px', 
                    fontSize: '12px' 
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <AlertTriangle size={14} style={{ color: 'var(--accent-rose)' }} />
                    <span style={{ fontWeight: 600, color: '#fecdd3' }}>{n.label}</span>
                  </div>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-rose)', fontWeight: 700 }}>
                    SCORE: {n.anomaly_score}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
