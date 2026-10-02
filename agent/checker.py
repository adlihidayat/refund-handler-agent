import os
import sqlite3
import requests

class ResultChecker:
    def __init__(self, db_path="shop/shop.db", base_url="http://127.0.0.1:5000"):
        self.db_path = db_path
        self.base_url = base_url

    def verify(self, finish_args, case_notes, outputs_dir):
        summary = finish_args.get("summary", "")
        verify_url = finish_args.get("verify_url", "")
        expected_facts = finish_args.get("expected", [])
        if isinstance(expected_facts, str):
            expected_facts = [expected_facts]

        if verify_url and not verify_url.startswith("http://") and not verify_url.startswith("https://"):
            verify_url = self.base_url.rstrip("/") + "/" + verify_url.lstrip("/")

        decision = (case_notes.data.get("decision") or "").lower()
        order_id = case_notes.data.get("order_id")

        errors = []

        if "refund" in decision or "update_address" in decision:
            # 1. Fresh page load verification via HTTP session
            if not verify_url:
                errors.append("Missing verify_url for verification.")
            else:
                try:
                    session = requests.Session()
                    # Perform fresh login
                    login_url = self.base_url.rstrip("/") + "/login"
                    session.post(login_url, data={"username": "admin", "password": "password123"})
                    
                    # Fetch verification URL
                    res = session.get(verify_url)
                    if res.status_code != 200:
                        errors.append(f"Verify URL returned HTTP status {res.status_code}.")
                    else:
                        page_text = res.text.lower()
                        for fact in expected_facts:
                            fact_str = str(fact).lower()
                            if fact_str not in page_text:
                                errors.append(f"Expected fact '{fact}' not found on verified page ({verify_url}).")
                except Exception as e:
                    errors.append(f"Failed fresh page load verification: {str(e)}")

            # 2. Database verification
            if order_id and "refund" in decision:
                try:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT SUM(amount) FROM refunds WHERE order_id = ?", (order_id,))
                    refund_total = cursor.fetchone()[0] or 0.0
                    conn.close()
                    if refund_total <= 0:
                        errors.append(f"Database check failed: No refund record found in shop.db for order #{order_id}.")
                except Exception as e:
                    errors.append(f"Database query error: {str(e)}")

        elif "deny" in decision or "ask" in decision or "no_refund" in decision:
            reply_file = os.path.join(outputs_dir, "reply.txt")
            if not os.path.exists(reply_file) or os.path.getsize(reply_file) == 0:
                errors.append(f"Verification failed: Outcome '{decision}' requires a saved reply draft in outputs/reply.txt.")

        if errors:
            return False, "Checker failed:\n" + "\n".join(errors)
        return True, "Verification PASSED: All shop records and outputs confirmed."
