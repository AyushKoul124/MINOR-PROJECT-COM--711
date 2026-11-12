import React, { useState, useEffect, useRef } from 'react';
import { Network, Activity, AlertTriangle } from 'lucide-react';
import { fetchNetworkGraph } from '../api';

const INK = '#111111';
const BLUE = '#1f4fff';
const LIME = '#d6ff3f';
const LINE = '#c5c5c5';

function buildLayout(nodes, links, width, height) {
  const coords = new Map();
  const points = nodes.map((node, index) => {
    const angle = (index / Math.max(nodes.length, 1)) * Math.PI * 2;
    const ring = Math.min(width, height) * 0.3;
    return {
      x: width / 2 + Math.cos(angle) * ring,
      y: height / 2 + Math.sin(angle) * ring * 0.72,
      node,
    };
  });
  const indexById = new Map(points.map((point, index) => [point.node.id, index]));
  const edges = links
    .map((link) => [indexById.get(link.source), indexById.get(link.target)])
    .filter((pair) => pair[0] != null && pair[1] != null && pair[0] !== pair[1]);

  for (let step = 0; step < 160; step += 1) {
    const disp = points.map(() => ({ x: 0, y: 0 }));
    for (let i = 0; i < points.length; i += 1) {
      for (let j = i + 1; j < points.length; j += 1) {
        let dx = points[i].x - points[j].x;
        let dy = points[i].y - points[j].y;
        const dist = Math.hypot(dx, dy) || 0.1;
        const push = 520 / (dist * dist);
        dx = (dx / dist) * push;
        dy = (dy / dist) * push;
        disp[i].x += dx;
        disp[i].y += dy;
        disp[j].x -= dx;
        disp[j].y -= dy;
      }
    }
    edges.forEach(([from, to]) => {
      const dx = points[to].x - points[from].x;
      const dy = points[to].y - points[from].y;
      disp[from].x += dx * 0.045;
      disp[from].y += dy * 0.045;
      disp[to].x -= dx * 0.045;
      disp[to].y -= dy * 0.045;
    });
    points.forEach((point, index) => {
      disp[index].x += (width / 2 - point.x) * 0.012;
      disp[index].y += (height / 2 - point.y) * 0.012;
      point.x += Math.max(-14, Math.min(14, disp[index].x));
      point.y += Math.max(-14, Math.min(14, disp[index].y));
      point.x = Math.max(36, Math.min(width - 36, point.x));
      point.y = Math.max(28, Math.min(height - 28, point.y));
    });
  }

  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  points.forEach((point) => {
    minX = Math.min(minX, point.x);
    minY = Math.min(minY, point.y);
    maxX = Math.max(maxX, point.x);
    maxY = Math.max(maxY, point.y);
  });
  const pad = 56;
  const spanX = Math.max(maxX - minX, 1);
  const spanY = Math.max(maxY - minY, 1);
  const scale = Math.min((width - pad * 2) / spanX, (height - pad * 2) / spanY);
  const offsetX = (width - spanX * scale) / 2;
  const offsetY = (height - spanY * scale) / 2;
  points.forEach((point) => {
    const degree = point.node.degree || 0;
    const flagged = point.node.coordination_signal;
    coords.set(point.node.id, {
      x: offsetX + (point.x - minX) * scale,
      y: offsetY + (point.y - minY) * scale,
      r: Math.max(flagged ? 7 : 5, Math.min(13, 5 + degree * 48)),
      node: point.node,
    });
  });
  return coords;
}

export default function NetworkGraph() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState(null);
  const [width, setWidth] = useState(960);
  const canvasRef = useRef(null);
  const frameRef = useRef(null);
  const layoutRef = useRef(new Map());

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

  useEffect(() => {
    const frame = frameRef.current;
    if (!frame) return undefined;
    const measure = () => {
      const next = frame.clientWidth;
      if (next > 0) setWidth(next);
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(frame);
    return () => observer.disconnect();
  }, [loading]);

  const nodes = data?.nodes || [];
  const links = data?.links || [];
  const linkedIds = new Set();
  links.forEach((link) => {
    linkedIds.add(link.source);
    linkedIds.add(link.target);
  });
  const seen = new Set();
  const drawnNodes = [];
  nodes.forEach((node) => {
    if (seen.has(node.id)) return;
    seen.add(node.id);
    if (linkedIds.has(node.id) || node.coordination_signal) drawnNodes.push(node);
  });
  const hiddenCount = seen.size - drawnNodes.length;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || drawnNodes.length === 0) return undefined;
    const ctx = canvas.getContext('2d');
    const height = 560;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, width, height);

    const coords = buildLayout(drawnNodes, links, width, height);
    layoutRef.current = coords;

    links.forEach((link) => {
      const source = coords.get(link.source);
      const target = coords.get(link.target);
      if (!source || !target) return;
      ctx.beginPath();
      ctx.moveTo(source.x, source.y);
      ctx.lineTo(target.x, target.y);
      ctx.strokeStyle = LINE;
      ctx.lineWidth = 1;
      ctx.stroke();
    });

    coords.forEach((entry) => {
      const flagged = entry.node.coordination_signal;
      const connector = (entry.node.betweenness || 0) >= 0.05 || (entry.node.degree || 0) >= 0.06;
      ctx.beginPath();
      ctx.arc(entry.x, entry.y, entry.r, 0, Math.PI * 2);
      ctx.fillStyle = flagged ? LIME : connector ? BLUE : INK;
      ctx.fill();
      ctx.lineWidth = 1;
      ctx.strokeStyle = INK;
      ctx.stroke();
      if (selectedNode && selectedNode.id === entry.node.id) {
        ctx.beginPath();
        ctx.arc(entry.x, entry.y, entry.r + 5, 0, Math.PI * 2);
        ctx.strokeStyle = BLUE;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    });

    return undefined;
  }, [drawnNodes, links, width, selectedNode]);

  const handleCanvasClick = (event) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = (event.clientX - rect.left) * (width / rect.width);
    const y = (event.clientY - rect.top) * (560 / rect.height);
    let hit = null;
    layoutRef.current.forEach((entry) => {
      if (entry.marker) return;
      if (Math.hypot(x - entry.x, y - entry.y) <= entry.r + 6) hit = entry.node;
    });
    setSelectedNode(hit);
  };

  if (loading) {
    return (
      <div className="loading-state">
        <Activity className="animate-spin" size={28} />
        <span>Loading the network...</span>
      </div>
    );
  }

  const flaggedNodes = [];
  const flaggedSeen = new Set();
  nodes.forEach((node) => {
    if (!node.coordination_signal || flaggedSeen.has(node.id)) return;
    flaggedSeen.add(node.id);
    flaggedNodes.push(node);
  });
  const topBrokers = [...drawnNodes].sort((a, b) => (b.betweenness || 0) - (a.betweenness || 0)).slice(0, 5);

  return (
    <div className="view-stack">
      <div className="bento-grid">
        <div className="bento-card span-3">
          <div className="card-header">
            <span className="card-title">Accounts</span>
            <span className="badge badge-blue">Shown</span>
          </div>
          <div className="kpi-value">{data?.total_nodes || 0}</div>
          <div className="kpi-subtext">Channels and named actors</div>
        </div>

        <div className="bento-card span-3">
          <div className="card-header">
            <span className="card-title">Connections</span>
            <span className="badge badge-emerald">Links</span>
          </div>
          <div className="kpi-value">{data?.total_edges || 0}</div>
          <div className="kpi-subtext">Forwards, Mentions, Replies</div>
        </div>

        <div className="bento-card span-3">
          <div className="card-header">
            <span className="card-title">Communities</span>
          </div>
          <div className="kpi-value">{data?.total_communities || 0}</div>
          <div className="kpi-subtext">Groups that talk among themselves</div>
        </div>

        <div className="bento-card span-3">
          <div className="card-header">
            <span className="card-title">Similar posting</span>
          </div>
          <div className="kpi-value" style={{ color: (data?.cib_flagged_count || 0) > 0 ? 'var(--accent-rose)' : 'var(--text-main)' }}>
            {data?.cib_flagged_count || 0}
          </div>
          <div className="kpi-subtext">Accounts that post in a similar pattern</div>
        </div>
      </div>

      <div className="bento-card graph-card" ref={frameRef}>
        <div className="card-header">
          <span className="card-title"><Network size={16} /> How accounts connect</span>
          <div className="badge-row">
            <span className="badge badge-blue">Blue marks a connector</span>
            <span className="badge">Lime marks similar posting</span>
          </div>
        </div>
        {drawnNodes.length === 0 ? (
          <div className="empty-state">No links in this window.</div>
        ) : (
          <canvas ref={canvasRef} className="graph-canvas" onClick={handleCanvasClick} />
        )}
        {hiddenCount > 0 && (
          <p className="graph-note">
            {hiddenCount} accounts have no forward, mention, or reply in this window, so they are left off the drawing.
          </p>
        )}

        {selectedNode && (
          <div className="graph-inspector">
            <button type="button" onClick={() => setSelectedNode(null)} aria-label="Close account details">×</button>
            <h3>{selectedNode.label}</h3>
            <div><span>Type</span><span>{selectedNode.entity_type}</span></div>
            <div><span>Group</span><span>{selectedNode.community_id}</span></div>
            <div><span>Connector</span><span>{selectedNode.betweenness}</span></div>
            <div><span>Links</span><span>{selectedNode.degree}</span></div>
            <div>
              <span>Similarity</span>
              <span className={selectedNode.coordination_signal ? 'flagged' : ''}>
                {selectedNode.anomaly_score} {selectedNode.coordination_signal ? 'FLAGGED' : 'CLEAR'}
              </span>
            </div>
          </div>
        )}
      </div>

      <div className="bento-grid">
        <div className="bento-card span-6">
          <div className="card-header">
            <span className="card-title">Accounts that connect the most groups</span>
          </div>
          <div className="stack-sm">
            {topBrokers.map((node, index) => (
              <div key={node.id} className="ledger-row">
                <div>
                  <span className="ledger-rank">#{index + 1}</span>
                  <span>{node.label}</span>
                  <span className="badge badge-gray">{node.entity_type}</span>
                </div>
                <span className="mono">{node.betweenness}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bento-card span-6">
          <div className="card-header">
            <span className="card-title">Flagged for similar posting</span>
          </div>
          {flaggedNodes.length === 0 ? (
            <div className="empty-state">No accounts were flagged.</div>
          ) : (
            <div className="stack-sm">
              {flaggedNodes.map((node) => (
                <div key={node.id} className="ledger-row ledger-flag">
                  <div>
                    <AlertTriangle size={14} />
                    <span>{node.label}</span>
                  </div>
                  <span className="mono">{node.anomaly_score}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
