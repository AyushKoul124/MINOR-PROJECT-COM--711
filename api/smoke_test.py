"""Quick smoke test — verify all FastAPI endpoints return 200 OK with valid schemas.

Run:
    python -m api.smoke_test
"""

from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_root_and_health() -> None:
    print("[1/6] Testing Root and /api/health endpoints...")
    r_root = client.get("/")
    assert r_root.status_code == 200
    assert r_root.json()["status"] == "online"

    r_health = client.get("/api/health")
    assert r_health.status_code == 200
    data = r_health.json()
    assert data["status"] in ("healthy", "degraded")
    assert data["database_connected"] is True
    print(f"  ✓ Root and health OK: DB={data['database_connected']}, Device={data['device']}.")


def test_overview_and_datasources() -> None:
    print("[2/6] Testing /api/overview and /api/datasources endpoints...")
    r_ov = client.get("/api/overview")
    assert r_ov.status_code == 200
    ov_data = r_ov.json()
    assert "total_posts" in ov_data
    assert "active_channels" in ov_data
    print(f"  ✓ Overview OK: {ov_data['active_channels']} channels, {ov_data['total_posts']} total posts.")

    r_ds = client.get("/api/datasources")
    assert r_ds.status_code == 200
    ds_data = r_ds.json()
    assert "channels" in ds_data
    assert len(ds_data["channels"]) > 0
    print(f"  ✓ DataSources OK: {len(ds_data['channels'])} channels listed.")


def test_sentiment_endpoints() -> None:
    print("[3/6] Testing /api/sentiment/timeline and /latest endpoints...")
    r_tl = client.get("/api/sentiment/timeline?window_hours=48")
    assert r_tl.status_code == 200
    tl_data = r_tl.json()
    assert "points" in tl_data
    assert "stance_breakdown" in tl_data
    print(f"  ✓ Sentiment timeline OK: {tl_data['total_posts']} posts analyzed across window.")

    r_lat = client.get("/api/sentiment/latest?limit=5")
    assert r_lat.status_code == 200
    assert "posts" in r_lat.json()
    print("  ✓ Sentiment latest posts OK.")


def test_demographics_and_trends() -> None:
    print("[4/6] Testing /api/demographics and /api/trends endpoints...")
    r_demo = client.get("/api/demographics?window_hours=48")
    assert r_demo.status_code == 200
    demo_data = r_demo.json()
    assert "clusters" in demo_data
    assert "k_anonymity_threshold" in demo_data
    print(f"  ✓ Demographics OK: {demo_data['total_clusters']} clusters (k={demo_data['k_anonymity_threshold']}).")

    r_tr = client.get("/api/trends?window_hours=48")
    assert r_tr.status_code == 200
    tr_data = r_tr.json()
    assert "topics" in tr_data
    print(f"  ✓ Trends OK: {tr_data['total_topics']} topics returned.")


def test_network_graph_endpoint() -> None:
    print("[5/6] Testing /api/network/graph WebGL payload endpoint...")
    r_net = client.get("/api/network/graph?window_hours=48")
    assert r_net.status_code == 200
    net_data = r_net.json()
    assert "nodes" in net_data
    assert "links" in net_data
    assert "modularity" in net_data
    print(f"  ✓ Network graph OK: {net_data['total_nodes']} nodes, {net_data['total_edges']} edges, Q={net_data['modularity']}.")


def test_rag_query_endpoint() -> None:
    print("[6/6] Testing /api/rag/query endpoint...")
    payload = {"question": "What are the latest updates on space missions?", "top_k": 3}
    r_rag = client.post("/api/rag/query", json=payload)
    assert r_rag.status_code == 200
    rag_data = r_rag.json()
    assert "answer" in rag_data
    assert "audit_id" in rag_data
    print(f"  ✓ RAG query OK: provider={rag_data['provider']}, audit_id={rag_data['audit_id']}.")


def main() -> None:
    print("=" * 65)
    print("FastAPI Backend REST Endpoints Smoke Test Suite")
    print("=" * 65)
    test_root_and_health()
    test_overview_and_datasources()
    test_sentiment_endpoints()
    test_demographics_and_trends()
    test_network_graph_endpoint()
    test_rag_query_endpoint()
    print("=" * 65)
    print("ALL FASTAPI ENDPOINTS PASSED SUCCESSFULLY! Backend is ready.")
    print("=" * 65)


if __name__ == "__main__":
    main()
