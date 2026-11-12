import React, { useState, useEffect, useRef } from 'react';
import { Activity } from 'lucide-react';
import { fetchNetworkGraph } from '../api';

const INK = '#111111';
const BLUE = '#1f4fff';
const LIME = '#d6ff3f';
const LINE = '#c5c5c5';
const MUTED = '#8a8a8a';
const CANVAS_HEIGHT = 320;

function isConnector(node) {
  return (node.betweenness || 0) >= 0.05 || (node.degree || 0) >= 0.06;
}

function readableName(node) {
  const text = String(node?.label || '').trim();
  if (!text || /^-?\d+$/.test(text)) return '';
  return text.length > 22 ? `${text.slice(0, 20)}…` : text;
}

function groupPair(node, links, byId) {
  const weight = new Map();
  links.forEach((link) => {
    const otherId = link.source === node.id ? link.target : link.target === node.id ? link.source : null;
    if (!otherId) return;
    const other = byId.get(otherId);
    if (!other) return;
    const key = other.community_id;
    weight.set(key, (weight.get(key) || 0) + 1);
  });
  weight.set(node.community_id, (weight.get(node.community_id) || 0) + 0.01);
  const ranked = [...weight.entries()].sort((a, b) => b[1] - a[1]).map(([id]) => id);
  if (ranked.length < 2) return `Group ${node.community_id}`;
  return `Group ${ranked[0]}↔Group ${ranked[1]}`;
}

function staysInside(memberIds, links) {
  let touching = 0;
  let inside = 0;
  links.forEach((link) => {
    const left = memberIds.has(link.source);
    const right = memberIds.has(link.target);
    if (!left && !right) return;
    touching += 1;
    if (left && right) inside += 1;
  });
  if (!touching) return 1;
  return inside / touching;
}

function buildReading(nodes, links) {
  const byId = new Map();
  nodes.forEach((node) => {
    if (!byId.has(node.id)) byId.set(node.id, node);
  });
  const linkedIds = new Set();
  links.forEach((link) => {
    linkedIds.add(link.source);
    linkedIds.add(link.target);
  });
  const drawn = [];
  byId.forEach((node) => {
    if (linkedIds.has(node.id) || node.coordination_signal) drawn.push(node);
  });
  const hiddenCount = byId.size - drawn.length;
  const buckets = new Map();
  drawn.forEach((node) => {
    const key = node.community_id ?? 0;
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key).push(node);
  });
  const groups = [...buckets.entries()].map(([id, members]) => {
    const memberIds = new Set(members.map((node) => node.id));
    return {
      id,
      members,
      count: members.length,
      staysInside: staysInside(memberIds, links),
      onCanvas: members.length >= 4,
    };
  });
  const canvasGroups = groups.filter((group) => group.onCanvas);
  const smallGroups = groups.filter((group) => !group.onCanvas);
  const placedIds = new Set(canvasGroups.flatMap((group) => group.members.map((node) => node.id)));
  const flaggedAside = drawn.filter((node) => node.coordination_signal && !placedIds.has(node.id));
  if (flaggedAside.length) {
    canvasGroups.push({
      id: 'flagged',
      members: flaggedAside,
      count: flaggedAside.length,
      staysInside: 1,
      onCanvas: true,
      synthetic: true,
    });
  }
  const canvasNodes = canvasGroups.flatMap((group) => group.members);
  const canvasIds = new Set(canvasNodes.map((node) => node.id));
  const connectors = canvasNodes.filter(isConnector);
  const flagged = drawn.filter((node) => node.coordination_signal);
  const openNext = [...canvasNodes]
    .sort((a, b) => (b.betweenness || 0) - (a.betweenness || 0) || (b.degree || 0) - (a.degree || 0))
    .slice(0, 8)
    .map((node) => ({
      node,
      pair: groupPair(node, links, byId),
      name: readableName(node) || node.label || node.id,
    }));
  const labeledIds = [];
  canvasGroups.forEach((group) => {
    const hub = [...group.members]
      .filter((node) => readableName(node))
      .sort((a, b) => (b.degree || 0) - (a.degree || 0))[0];
    if (hub && labeledIds.length < 5) labeledIds.push(hub.id);
    group.members.forEach((node) => {
      if (node.coordination_signal && !labeledIds.includes(node.id) && labeledIds.length < 5) {
        labeledIds.push(node.id);
      }
    });
  });
  return {
    hiddenCount,
    canvasGroups,
    smallGroups,
    canvasNodes,
    canvasIds,
    connectors,
    flagged,
    openNext,
    labeledIds,
    byId,
  };
}

function placeMembers(coords, group, left, top, boxW, boxH) {
  const size = group.members.length;
  const innerCols = Math.max(1, Math.ceil(Math.sqrt(size)));
  const gap = 26;
  const originX = left + 24;
  const originY = top + 84;
  group.members.forEach((node, memberIndex) => {
    const col = memberIndex % innerCols;
    const row = Math.floor(memberIndex / innerCols);
    const x = originX + col * gap;
    const y = originY + row * gap;
    const degree = node.degree || 0;
    const flagged = node.coordination_signal;
    coords.set(node.id, {
      x,
      y,
      r: Math.max(flagged ? 7 : 4.5, Math.min(9, 4.5 + degree * 28)),
      node,
      groupId: group.id,
      left,
      right: left + boxW,
      top,
      boxW,
      boxH,
    });
  });
}

function buildLayout(groups, width) {
  const coords = new Map();
  const ordered = [...groups].sort((a, b) => b.members.length - a.members.length);
  const dot = 26;
  let x = 8;
  let y = 4;
  let rowH = 0;
  ordered.forEach((group) => {
    const size = group.members.length;
    const innerCols = Math.max(1, Math.ceil(Math.sqrt(size)));
    const innerRows = Math.ceil(size / innerCols);
    const boxW = (innerCols - 1) * dot + 150;
    const boxH = (innerRows - 1) * dot + 110;
    if (x > 8 && x + boxW > width - 4) {
      x = 8;
      y += rowH + 16;
      rowH = 0;
    }
    placeMembers(coords, group, x, y, boxW, boxH);
    x += boxW + 22;
    rowH = Math.max(rowH, boxH);
  });
  return coords;
}

function drawGraph(ctx, reading, coords, links, width, height, selectedId) {
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, width, height);

  reading.canvasGroups.forEach((group) => {
    const members = group.members.map((node) => coords.get(node.id)).filter(Boolean);
    if (!members.length) return;
    const minX = Math.min(...members.map((entry) => entry.x)) - 16;
    const minY = Math.min(...members.map((entry) => entry.y)) - 16;
    const maxX = Math.max(...members.map((entry) => entry.x)) + 16;
    const maxY = Math.max(...members.map((entry) => entry.y)) + 16;
    ctx.strokeStyle = 'rgba(31, 79, 255, 0.55)';
    ctx.lineWidth = 1;
    ctx.strokeRect(minX, minY, maxX - minX, maxY - minY);
  });

  links.forEach((link) => {
    if (!reading.canvasIds.has(link.source) || !reading.canvasIds.has(link.target)) return;
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
    const connector = isConnector(entry.node);
    ctx.beginPath();
    ctx.arc(entry.x, entry.y, entry.r, 0, Math.PI * 2);
    ctx.fillStyle = flagged ? LIME : connector ? BLUE : INK;
    ctx.fill();
    ctx.lineWidth = 1;
    ctx.strokeStyle = INK;
    ctx.stroke();
    if (selectedId && selectedId === entry.node.id) {
      ctx.beginPath();
      ctx.arc(entry.x, entry.y, entry.r + 5, 0, Math.PI * 2);
      ctx.strokeStyle = BLUE;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
  });

  ctx.textAlign = 'left';
  ctx.textBaseline = 'bottom';
  ctx.font = '500 11px "IBM Plex Mono", ui-monospace, monospace';
  reading.canvasGroups.forEach((group) => {
    const members = group.members.map((node) => coords.get(node.id)).filter(Boolean);
    if (!members.length) return;
    const minX = Math.min(...members.map((entry) => entry.x)) - 16;
    const minY = Math.min(...members.map((entry) => entry.y)) - 16;
    const share = Math.round(group.staysInside * 100);
    const title = group.synthetic
      ? `Flagged · ${group.count}`
      : `G${group.id} · ${group.count} · ${share}% inside`;
    const notes = [];
    group.members
      .filter((node) => reading.labeledIds.includes(node.id))
      .forEach((node) => {
        const name = readableName(node);
        if (name) notes.push({ text: name, color: INK });
        if (node.coordination_signal) {
          notes.push({ text: `flagged: ${node.anomaly_score}`, color: '#3f6212' });
        } else if (isConnector(node)) {
          const pair = groupPair(node, links, reading.byId).replaceAll('Group ', 'G').replaceAll('↔', ' and ');
          notes.push({ text: `connects ${pair}`, color: BLUE });
        }
      });
    const lines = [...notes, { text: title, color: MUTED }];
    const maxText = Math.max(120, (members[0].boxW || 160) - 12);
    lines.forEach((line, index) => {
      const y = minY - 6 - (lines.length - 1 - index) * 15;
      let text = line.text;
      while (text.length > 4 && ctx.measureText(`${text}…`).width > maxText) text = text.slice(0, -1);
      if (text !== line.text) text = `${text}…`;
      ctx.fillStyle = line.color;
      ctx.fillText(text, members[0].left + 10, y);
    });
  });
}

export default function NetworkGraph() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState(null);
  const [width, setWidth] = useState(720);
  const canvasRef = useRef(null);
  const frameRef = useRef(null);
  const layoutRef = useRef(new Map());

  useEffect(() => {
    async function loadData() {
      try {
        setData(await fetchNetworkGraph(48));
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

  const reading = buildReading(data?.nodes || [], data?.links || []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || reading.canvasNodes.length === 0) return undefined;
    const ctx = canvas.getContext('2d');
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(CANVAS_HEIGHT * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const coords = buildLayout(reading.canvasGroups, width);
    layoutRef.current = coords;
    drawGraph(ctx, reading, coords, data?.links || [], width, CANVAS_HEIGHT, selectedNode?.id);
    return undefined;
  }, [data, reading, width, selectedNode]);

  const handleCanvasClick = (event) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = (event.clientX - rect.left) * (width / rect.width);
    const y = (event.clientY - rect.top) * (CANVAS_HEIGHT / rect.height);
    let hit = null;
    layoutRef.current.forEach((entry) => {
      if (Math.hypot(x - entry.x, y - entry.y) <= entry.r + 8) hit = entry.node;
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

  const start = reading.openNext.find((row) => readableName(row.node)) || reading.openNext[0];
  const flaggedCount = reading.flagged.length;
  const connectorCount = reading.connectors.length;
  const groupCount = reading.canvasGroups.filter((group) => !group.synthetic).length;

  return (
    <div className="view-stack">
      <section className="graph-card">
        <p className="graph-finding">
          <span className="mono">{groupCount}</span> {groupCount === 1 ? 'group' : 'groups'},{' '}
          <span className="mono">{connectorCount}</span> {connectorCount === 1 ? 'connector' : 'connectors'},{' '}
          <span className="mono">{flaggedCount}</span> flagged {flaggedCount === 1 ? 'account' : 'accounts'} in this window.
          {start ? <> Start with <span className="mono">{readableName(start.node) || start.name}</span>’s neighbours.</> : null}
        </p>

        <div className="graph-stats">
          <div className="graph-stat">
            <strong className="mono">{reading.canvasNodes.length}</strong>
            <span>Accounts drawn</span>
          </div>
          <div className="graph-stat">
            <strong className="mono">{groupCount}</strong>
            <span>Groups</span>
          </div>
          <div className="graph-stat connectors">
            <strong className="mono">{connectorCount}</strong>
            <span>Connectors</span>
          </div>
          <div className="graph-stat flagged">
            <strong className="mono">{flaggedCount}</strong>
            <span>Flagged</span>
          </div>
        </div>

        <div className="graph-stage">
          <div className="graph-canvas-wrap" ref={frameRef}>
            {reading.canvasNodes.length === 0 ? (
              <div className="empty-state">No links in this window.</div>
            ) : (
              <canvas ref={canvasRef} className="graph-canvas" onClick={handleCanvasClick} />
            )}
          </div>
          <aside className="open-next">
            <h3>Open next</h3>
            {reading.openNext.length === 0 ? (
              <p className="graph-note">No account links this window.</p>
            ) : (
              reading.openNext.map((row, index) => (
                <button
                  key={row.node.id}
                  type="button"
                  className={selectedNode?.id === row.node.id ? 'open-row on' : 'open-row'}
                  onClick={() => setSelectedNode(row.node)}
                >
                  <span className="mono">{index + 1}</span>
                  <span>
                    <strong>{row.name}</strong>
                    <em>{row.pair}</em>
                  </span>
                  <span className="open-score">
                    <span className="mono">{Number(row.node.betweenness || 0).toFixed(4)}</span>
                    {row.node.coordination_signal && <span className="lime-tag">lime</span>}
                  </span>
                </button>
              ))
            )}
          </aside>
        </div>

        {reading.smallGroups.length > 0 && (
          <div className="other-groups">
            <span>Other groups</span>
            {reading.smallGroups.map((group) => (
              <span key={group.id} className="other-chip">
                Group {group.id} · {group.count}
              </span>
            ))}
          </div>
        )}

        <div className="how-to-read">
          <p>
            <strong><i className="swatch ink" /> Cluster</strong>
            Accounts inside one outline talk among themselves.
          </p>
          <p>
            <strong><i className="swatch blue" /> Blue</strong>
            A connector. This account carries talk from one group into another.
          </p>
          <p>
            <strong><i className="swatch lime" /> Lime</strong>
            Similar posting at 0.70 or above. An advisory flag, not a finding of coordination.
          </p>
        </div>

        {reading.hiddenCount > 0 && (
          <p className="graph-caption">
            {reading.hiddenCount} accounts have no forward, mention, or reply in this window, so they are left off the drawing.
          </p>
        )}
      </section>
    </div>
  );
}
