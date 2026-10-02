import json
import os

class CaseNotes:
    def __init__(self, filepath):
        self.filepath = filepath
        self.data = {
            "order_id": None,
            "customer_email": None,
            "amount_paid": None,
            "requested_amount": None,
            "decision": None,  # refund / deny / ask
            "policy_line": None,
            "actions_tried": [],
            "status": "in_progress",
            "reply_draft": None,
            "custom_fields": {}
        }
        self.load()

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                    self.data["status"] = "in_progress"
            except Exception:
                pass

    def save(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2)

    def set(self, key, value):
        if key in self.data:
            self.data[key] = value
        else:
            self.data["custom_fields"][key] = value
        self.save()

    def add_action(self, action_summary):
        self.data["actions_tried"].append(action_summary)
        self.save()

    def to_string(self):
        lines = []
        for k, v in self.data.items():
            if k == "custom_fields" and v:
                for ck, cv in v.items():
                    lines.append(f"{ck}: {cv}")
            elif k != "custom_fields" and v is not None:
                lines.append(f"{k}: {v}")
        return "\n".join(lines) if lines else "No case notes recorded yet."
