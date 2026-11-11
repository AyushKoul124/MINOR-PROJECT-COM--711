/**
 * API client helper communicating with the FastAPI backend on port 8000.
 * Vite proxies /api → http://127.0.0.1:8000 (see vite.config.js).
 */

const BASE_URL = '/api';

function basicAuthHeader() {
  const username = import.meta.env.VITE_API_BASIC_AUTH_USERNAME;
  const password = import.meta.env.VITE_API_BASIC_AUTH_PASSWORD;
  if (username && password) {
    return { Authorization: `Basic ${btoa(`${username}:${password}`)}` };
  }
  return {};
}

async function apiFetch(path, options = {}) {
  const headers = {
    ...basicAuthHeader(),
    ...(options.headers || {}),
  };
  let res;
  try {
    res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  } catch {
    throw new Error(
      'Cannot reach the API. In a terminal run: uvicorn api.main:app --host 127.0.0.1 --port 8000'
    );
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    if (data == null) {
      throw new Error(
        `API returned ${res.status} with no JSON body. Start the backend: uvicorn api.main:app --host 127.0.0.1 --port 8000`
      );
    }
    const detail = data?.detail;
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg || JSON.stringify(d)).join('; ')
          : `Request failed (${res.status})`;
    throw new Error(message);
  }
  return data;
}

export async function fetchHealth() {
  return apiFetch('/health');
}

export async function fetchOverview() {
  return apiFetch('/overview');
}

export async function triggerVivaAnalysis(bBatchLimit = 50, windowHours = 48) {
  return apiFetch('/orchestrator/trigger', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ b_batch_limit: bBatchLimit, window_hours: windowHours }),
  });
}

export async function fetchSentimentTimeline(windowHours = 48) {
  return apiFetch(`/sentiment/timeline?window_hours=${windowHours}`);
}

export async function fetchLatestSentiment(limit = 20) {
  return apiFetch(`/sentiment/latest?limit=${limit}`);
}

export async function fetchDemographics(windowHours = 48) {
  return apiFetch(`/demographics?window_hours=${windowHours}`);
}

export async function fetchTrends(windowHours = 48) {
  return apiFetch(`/trends?window_hours=${windowHours}`);
}

export async function fetchNetworkGraph(windowHours = 48) {
  return apiFetch(`/network/graph?window_hours=${windowHours}`);
}

export async function executeRAGQuery(question, topK = 5) {
  return apiFetch('/rag/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, top_k: topK }),
  });
}

export async function fetchDataSources() {
  return apiFetch('/datasources');
}
