import json
import os
import sys
import urllib.request
import urllib.error

def check_staging_health(base_url="http://localhost"):
    health_url = f"{base_url.rstrip('/')}/api/v1/health/"
    print(f"=== EazyDoc Staging Operational Health Check ===")
    print(f"Target Health Endpoint: {health_url}")

    try:
        req = urllib.request.Request(
            health_url,
            headers={"User-Agent": "EazyDoc-Staging-HealthCheck/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            status_code = response.getcode()
            body = response.read().decode("utf-8")
            data = json.loads(body)

            print(f"HTTP Status: {status_code} OK")
            print(f"Service Status: {data.get('status', 'unknown')}")
            print(f"Database: {data.get('database', 'unknown')}")
            print(f"Redis Cache: {data.get('redis', 'unknown')}")

            if data.get("status") == "ok" and data.get("database") == "ok":
                print("\n[SUCCESS] Staging core application and backing stores are fully operational.")
                return 0
            else:
                print("\n[WARNING] Staging service reported degraded health.")
                return 1
    except urllib.error.URLError as e:
        print(f"\n[ERROR] Health check request failed: {e}")
        print("Ensure staging containers (Nginx, Daphne/backend, Postgres, Redis) are running.")
        return 2
    except Exception as e:
        print(f"\n[ERROR] Unexpected error during staging health check: {e}")
        return 3

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "http://localhost"
    sys.exit(check_staging_health(target))

