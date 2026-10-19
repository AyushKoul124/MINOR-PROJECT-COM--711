/**
 * API client helper communicating with the FastAPI backend on port 8000.
 */

const BASE_URL = '/api';

export async function fetchHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  return res.json();
}

export async function fetchOverview() {
  const res = await fetch(`${BASE_URL}/overview`);
  return res.json();
}

export async function triggerVivaAnalysis(bBatchLimit = 50, windowHours = 48) {
  const res = await fetch(`${BASE_URL}/orchestrator/trigger`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ b_batch_limit: bBatchLimit, window_hours: windowHours }),
  });
  return res.json();
}

export async function fetchSentimentTimeline(windowHours = 48) {
  const res = await fetch(`${BASE_URL}/sentiment/timeline?window_hours=${windowHours}`);
  return res.json();
}

export async function fetchLatestSentiment(limit = 20) {
  const res = await fetch(`${BASE_URL}/sentiment/latest?limit=${limit}`);
  return res.json();
}

export async function fetchDemographics(windowHours = 48) {
  const res = await fetch(`${BASE_URL}/demographics?window_hours=${windowHours}`);
  return res.json();
}

export async function fetchTrends(windowHours = 48) {
  const res = await fetch(`${BASE_URL}/trends?window_hours=${windowHours}`);
  return res.json();
}

export async function fetchNetworkGraph(windowHours = 48) {
  const res = await fetch(`${BASE_URL}/network/graph?window_hours=${windowHours}`);
  return res.json();
}

export async function executeRAGQuery(question, topK = 5) {
  const res = await fetch(`${BASE_URL}/rag/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, top_k: topK }),
  });
  return res.json();
}

export async function fetchDataSources() {
  const res = await fetch(`${BASE_URL}/datasources`);
  return res.json();
}
