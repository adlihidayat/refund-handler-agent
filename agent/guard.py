import json
import os

class GuardEngine:
    def __init__(self, guards_config_path="guards.json"):
        self.guards_config_path = guards_config_path
        self.rules = []
        self.load_rules()

    def load_rules(self):
        if os.path.exists(self.guards_config_path):
            try:
                with open(self.guards_config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.rules = data.get("rules", [])
            except Exception as e:
                print(f"Warning: Failed to load guards config: {e}")

    def evaluate_action(self, action_name, action_args, browser_wrapper, case_notes):
        """
        Evaluates an action before execution.
        Returns (is_blocked: bool, action_type: str, message: str)
        """
        if action_name != "browser_click":
            return False, None, None

        element_id = action_args.get("id") or action_args.get("element_id")
        try:
            elem_id = int(element_id)
        except (ValueError, TypeError):
            return False, None, None

        elem_info = browser_wrapper.elements_map.get(elem_id, {})
        is_refund_submit = elem_info.get("is_refund_submit", False)
        
        # Check DOM input value for refund amount or case_notes requested_amount
        refund_amount = 0.0
        try:
            if browser_wrapper.page:
                val = browser_wrapper.page.input_value("#refund-amount")
                if val:
                    refund_amount = float(val)
        except Exception:
            pass

        if not refund_amount and case_notes and case_notes.data.get("requested_amount"):
            try:
                refund_amount = float(case_notes.data.get("requested_amount"))
            except (ValueError, TypeError):
                pass

        for rule in self.rules:
            if rule.get("target_action") == "browser_click":
                cond = rule.get("conditions", {})
                if cond.get("is_refund_submit") and is_refund_submit:
                    threshold = cond.get("amount_gt", 100.0)
                    if refund_amount > threshold:
                        prompt_template = rule.get("prompt", "APPROVAL NEEDED: Refund ${amount} exceeds limit.")
                        prompt_msg = prompt_template.replace("${amount}", f"{refund_amount:.2f}")
                        return True, rule.get("action", "ask_human"), prompt_msg

        return False, None, None
