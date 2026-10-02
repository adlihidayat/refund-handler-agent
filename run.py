import os
import sys
import time
import argparse
import subprocess
import urllib.request

def is_server_running(url="http://127.0.0.1:5000/login"):
    try:
        res = urllib.request.urlopen(url, timeout=2)
        return res.status in (200, 302, 404)
    except Exception:
        return False

def ensure_shop_server():
    if is_server_running():
        print("[System] Shop back office server is already running on http://127.0.0.1:5000")
        return None
    
    print("[System] Starting Shop back office server on http://127.0.0.1:5000...")
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    proc = subprocess.Popen([sys.executable, "shop/app.py"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Wait for server to start
    for _ in range(10):
        time.sleep(1)
        if is_server_running():
            print("[System] Shop server started successfully.")
            return proc
    print("[Warning] Server startup check timed out.")
    return proc

def main():
    parser = argparse.ArgumentParser(description="Refund Agent Terminal Prototype Runner")
    parser.add_argument("complaint", help="Path to customer complaint text file (e.g. complaints/01_broken_item.txt)")
    parser.add_argument("--policy", default="policy.md", help="Path to policy file (default: policy.md)")
    parser.add_argument("--guards", default="guards.json", help="Path to guards config file (default: guards.json)")
    parser.add_argument("--reset-db", action="store_true", help="Reset database to seed data before running")
    args = parser.parse_args()

    if not os.path.exists(args.complaint):
        print(f"Error: Complaint file '{args.complaint}' does not exist.")
        sys.exit(1)

    if args.reset_db or not os.path.exists("shop/shop.db"):
        print("[System] Resetting database...")
        env = os.environ.copy()
        env["PYTHONPATH"] = "."
        subprocess.run([sys.executable, "shop/reset_db.py"], env=env, check=True)

    server_proc = ensure_shop_server()

    try:
        from agent.loop import AgentLoop
        # Adapt policy path if generalization task provides relative path
        policy_path = args.policy
        if not os.path.exists(policy_path) and os.path.exists(os.path.join(os.path.dirname(args.complaint), "policy.md")):
            policy_path = os.path.join(os.path.dirname(args.complaint), "policy.md")

        agent = AgentLoop(
            complaint_path=args.complaint,
            policy_path=policy_path,
            guards_path=args.guards
        )
        success = agent.run()
        sys.exit(0 if success else 1)
    finally:
        if server_proc:
            print("[System] Stopping Shop back office server...")
            server_proc.terminate()
            server_proc.wait()

if __name__ == "__main__":
    main()
