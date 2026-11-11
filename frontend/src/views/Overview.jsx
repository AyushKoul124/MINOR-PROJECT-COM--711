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
import { fetchOverview, fetchRecentPosts, triggerVivaAnalysis } from '../api';

export default function Overview({ onNavigate }) {
  const [metrics, setMetrics] = useState(null);
  const [posts, setPosts] = useState([]);
  const [openPost, setOpenPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [triggerResult, setTriggerResult] = useState(null);
  const [triggerError, setTriggerError] = useState(null);

  const loadData = async () => {
    try {
      const [ovData, recent] = await Promise.all([
        fetchOverview(),
        fetchRecentPosts(48),
      ]);
      const nextPosts = recent.posts || [];
      setMetrics(ovData);
      setPosts(nextPosts);
      setOpenPost((current) => {
        if (!current) return null;
        return nextPosts.find((post) => post.post_id === current.post_id) || current;
      });
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

  useEffect(() => {
    if (!openPost) return undefined;
    const onKey = (event) => {
      if (event.key === 'Escape') setOpenPost(null);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [openPost]);

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

      <PostLane
        title="Posts with a picture"
        note="A photo, with the caption when the post has one."
        posts={posts.filter((post) => post.kind === 'picture' || (post.photos || []).length > 0)}
        onOpen={setOpenPost}
      />
      <PostLane
        title="Text posts"
        note="Words only. No picture was saved with these."
        posts={posts.filter((post) => (post.photos || []).length === 0)}
        onOpen={setOpenPost}
      />
      {openPost && <PostReader post={openPost} onClose={() => setOpenPost(null)} />}

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

function PostLane({ title, note, posts, onOpen }) {
  return (
    <div className="bento-card">
      <div className="card-header">
        <span className="card-title">{title}</span>
        <span className="badge badge-gray">{posts.length}</span>
      </div>
      <p style={{ margin: '8px 0 0', color: 'var(--text-muted)', fontSize: '13px' }}>{note}</p>
      {posts.length === 0 ? (
        <p style={{ color: 'var(--text-muted)' }}>Nothing in this group yet.</p>
      ) : (
        <div className="post-grid">
          {posts.map((post) => (
            <button key={post.post_id} type="button" className="post-card" onClick={() => onOpen(post)}>
              {post.photos?.[0] && <img src={post.photos[0]} alt="" />}
              <div className="post-card-body">
                <div className="post-card-meta">
                  <span>{post.channel}</span>
                  <span>{new Date(post.posted_at).toLocaleString()}</span>
                </div>
                <p>{post.content_text || 'Photo only'}</p>
                <ReactionRow reactions={post.reactions} />
                <CommentPreview comments={post.comments} />
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function PostReader({ post, onClose }) {
  return (
    <div className="post-reader-backdrop" onClick={onClose}>
      <article className="post-reader" onClick={(event) => event.stopPropagation()} role="dialog" aria-modal="true">
        <div className="post-reader-top">
          <div>
            <strong>{post.channel}</strong>
            <p>{new Date(post.posted_at).toLocaleString()}</p>
          </div>
          <button type="button" className="btn" onClick={onClose}>Close</button>
        </div>
        {(post.photos || []).map((src) => (
          <img key={src} src={src} alt="" />
        ))}
        <p className="post-reader-body">{post.content_text || 'This post has a picture and no caption.'}</p>
        <section className="post-reactions">
          <h4>Reactions</h4>
          {(post.reactions || []).length === 0 ? (
            <p className="muted-line">No reactions on this post.</p>
          ) : (
            <ReactionRow reactions={post.reactions} />
          )}
        </section>
        <section className="post-comments">
          <h4>Comments ({commentTotal(post.comments)})</h4>
          {(post.comments || []).length === 0 ? (
            <p className="muted-line">No comments on this post.</p>
          ) : (
            post.comments.map((comment) => (
              <CommentBlock key={comment.comment_id} comment={comment} />
            ))
          )}
        </section>
      </article>
    </div>
  );
}

function commentTotal(comments) {
  return (comments || []).reduce(
    (sum, comment) => sum + 1 + (comment.replies || []).length,
    0,
  );
}

function ReactionRow({ reactions }) {
  if (!reactions?.length) return null;
  return (
    <div className="reaction-row">
      {reactions.map((item) => (
        <span key={`${item.emoji}-${item.count}`} className="reaction-chip">
          {item.emoji} {item.count}
        </span>
      ))}
    </div>
  );
}

function CommentPreview({ comments }) {
  const total = commentTotal(comments);
  const first = (comments || []).find((comment) => comment.content_text) || comments?.[0];
  return (
    <div className="comment-preview">
      <span>{total === 0 ? 'No comments' : `${total} comment${total === 1 ? '' : 's'}`}</span>
      {first?.content_text && <p>{first.author}: {first.content_text}</p>}
    </div>
  );
}

function CommentBlock({ comment, nested = false }) {
  return (
    <div className={nested ? 'comment comment-reply' : 'comment'}>
      <div className="comment-meta">
        <strong>{comment.author}</strong>
        <span>{new Date(comment.posted_at).toLocaleString()}</span>
      </div>
      {comment.content_text ? <p>{comment.content_text}</p> : null}
      {(comment.photos || []).map((src) => (
        <img key={src} src={src} alt="" />
      ))}
      <ReactionRow reactions={comment.reactions} />
      {(comment.replies || []).map((reply) => (
        <CommentBlock key={reply.comment_id} comment={reply} nested />
      ))}
    </div>
  );
}
