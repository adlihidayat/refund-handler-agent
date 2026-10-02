import os
import sys

class ToolHandler:
    def __init__(self, browser_wrapper, case_notes, guard_engine, checker, outputs_dir):
        self.browser = browser_wrapper
        self.notes = case_notes
        self.guard = guard_engine
        self.checker = checker
        self.outputs_dir = outputs_dir

    def read_file(self, path):
        if not os.path.exists(path):
            return f"Error: File '{path}' not found."
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return f"--- Content of {path} ---\n{content}"
        except Exception as e:
            return f"Error reading file '{path}': {str(e)}"

    def browser_open(self, url):
        return self.browser.open(url)

    def browser_read(self):
        return self.browser.read()

    def browser_click(self, id):
        # Run Guard check first!
        blocked, action_type, prompt_msg = self.guard.evaluate_action(
            "browser_click", {"id": id}, self.browser, self.notes
        )
        if blocked:
            print(f"\n[GUARD INTERVENTION]: {prompt_msg}")
            raw_answer = input("Your answer > ").strip()
            self.notes.add_action(f"Guard ask_human: '{prompt_msg}' -> Answered: '{raw_answer}'")
            if raw_answer.lower() in ['a', 'approve', 'yes', 'y'] or "approve" in raw_answer.lower():
                print("[GUARD]: Human approved risky action. Proceeding with click...")
            else:
                self.notes.set("status", "blocked_by_human")
                return f"Guard blocked click on [{id}]: Human rejected or commented: '{raw_answer}'"

        return self.browser.click(id)

    def browser_type(self, id, text):
        return self.browser.type_text(id, text)

    def browser_screenshot(self, name):
        screenshots_dir = os.path.join(self.outputs_dir, "screenshots")
        return self.browser.screenshot(os.path.join(screenshots_dir, name))

    def save_note(self, key, value):
        self.notes.set(key, value)
        return f"Saved note: {key} = {value}"

    def ask_human(self, question, options=None):
        options_str = f" Options: {options}" if options else ""
        print(f"\n================ APPROVAL / HUMAN INPUT NEEDED ================")
        print(f"{question}{options_str}")
        print("===============================================================")
        response = input("Your answer > ").strip()
        self.notes.add_action(f"Asked human: '{question}' -> Answered: '{response}'")
        return f"Human response: {response}"

    def draft_reply(self, text):
        os.makedirs(self.outputs_dir, exist_ok=True)
        reply_path = os.path.join(self.outputs_dir, "reply.txt")
        with open(reply_path, 'w', encoding='utf-8') as f:
            f.write(text)
        self.notes.set("reply_draft", text)
        return f"Draft reply saved to {reply_path}"

    def finish(self, summary, verify_url=None, expected=None):
        finish_args = {
            "summary": summary,
            "verify_url": verify_url,
            "expected": expected or []
        }
        passed, msg = self.checker.verify(finish_args, self.notes, self.outputs_dir)
        if passed:
            self.notes.set("status", "completed")
            return f"FINISH_ACCEPTED: {summary}\n{msg}"
        else:
            return f"FINISH_REJECTED: {msg}\nPlease fix the issues and continue."
