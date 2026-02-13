import requests
import time
import json

API_URL = "http://localhost:8000"

def test_query_caching():
    question = "How many customers are in the database?"
    
    # First attempt
    print(f"\n1. First attempt for: '{question}'")
    start = time.time()
    response = requests.post(f"{API_URL}/api/query", json={"question": question})
    end = time.time()
    print(f"Status: {response.status_code}")
    print(f"Time: {end - start:.2f}s")
    
    # Second attempt (should be cached)
    print(f"\n2. Second attempt for: '{question}'")
    start = time.time()
    response = requests.post(f"{API_URL}/api/query", json={"question": question})
    end = time.time()
    print(f"Status: {response.status_code}")
    print(f"Time: {end - start:.2f}s")
    
    if (end - start) < 0.1:
        print("✅ SUCCESS: Query was successfully cached!")
    else:
        print("❌ FAILURE: Query was not cached.")

def test_metrics():
    print("\n3. Testing Metrics Endpoint")
    response = requests.get(f"{API_URL}/api/metrics")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        metrics = response.json()
        print(f"Metrics: {json.dumps(metrics, indent=2)}")
        if metrics.get("total_queries", 0) > 0:
            print("✅ SUCCESS: Metrics are being collected.")
        else:
            print("❌ FAILURE: Metrics count is 0.")

def test_schema_enrichment():
    print("\n4. Testing Schema Enrichment (SQLite performance check)")
    start = time.time()
    response = requests.get(f"{API_URL}/api/schema")
    end = time.time()
    print(f"Status: {response.status_code}")
    print(f"Time: {end - start:.2f}s")
    
    if response.status_code == 200:
        schema = response.json()
        # Look for [Values: ...] in schema summary
        if "[Values:" in schema.get("schema_summary", ""):
            print("✅ SUCCESS: Schema enrichment (categorical values) is working.")
        else:
            print("⚠️ WARNING: No categorical values found in schema (check if tables have data).")

if __name__ == "__main__":
    try:
        test_query_caching()
        test_metrics()
        test_schema_enrichment()
    except Exception as e:
        print(f"Error during verification: {e}")
