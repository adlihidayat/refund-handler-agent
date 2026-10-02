import os
import sys
import json
import time
import re
from rich.console import Console
from rich.panel import Panel

from agent.browser import BrowserWrapper
from agent.notes import CaseNotes
from agent.guard import GuardEngine
from agent.checker import ResultChecker
from agent.tools import ToolHandler

console = Console()

def load_env(env_path=".env"):
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

class AgentLoop:
    def __init__(self, complaint_path, policy_path="policy.md", guards_path="guards.json", base_url="http://127.0.0.1:5000", max_steps=40):
        load_env()
        self.complaint_path = complaint_path
        self.policy_path = policy_path
        self.guards_path = guards_path
        self.base_url = base_url
        self.max_steps = max_steps
        
        case_name = os.path.splitext(os.path.basename(complaint_path))[0]
        self.outputs_dir = os.path.join("outputs", case_name)
        os.makedirs(self.outputs_dir, exist_ok=True)

        self.notes = CaseNotes(os.path.join(self.outputs_dir, "case_notes.json"))
        self.browser = BrowserWrapper(base_url=base_url, screenshots_dir=os.path.join(self.outputs_dir, "screenshots"))
        self.guard = GuardEngine(guards_config_path=guards_path)
        self.checker = ResultChecker(db_path="shop/shop.db", base_url=base_url)
        self.tools = ToolHandler(self.browser, self.notes, self.guard, self.checker, self.outputs_dir)

        self.system_prompt = self._load_system_prompt()
        self.history = []
        self.action_retry_counts = {}

    def _load_system_prompt(self):
        prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "system.md")
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        return "You are a refund agent worker."

    def _find_elem(self, id_attr=None, name=None, is_submit=False):
        for k, v in self.browser.elements_map.items():
            if id_attr and v.get('id_attr') == id_attr:
                return k
            if name and v.get('name') == name:
                return k
            if is_submit and (v.get('id_attr') == 'submit-refund-button' or v.get('is_refund_submit')):
                return k
        return None

    def _call_llm(self, prompt):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise Exception("Cannot run due to no agent connected (GEMINI_API_KEY is missing)")

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            full_prompt = f"{self.system_prompt}\n\n=== CONVERSATION LOG & CURRENT STATE ===\n{prompt}\n\n=== YOUR NEXT ACTION ===\nReturn ONLY a JSON object with keys 'thought', 'tool', and 'args'."
            
            response = client.models.generate_content(
                model="gemini-2.8-flash-lite",
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return response.text
        except Exception as e:
            raise Exception(f"Live API call failed: {e}")

    def _parse_llm_json(self, response_text):
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if lines[-1].startswith("```") else "\n".join(lines[1:])
        text = text.strip()
        return json.loads(text)

    def execute_tool(self, tool_name, args):
        func = getattr(self.tools, tool_name, None)
        if not func:
            return f"Error: Tool '{tool_name}' does not exist."
        try:
            return func(**args)
        except TypeError as te:
            return f"Error: Incorrect arguments for tool '{tool_name}': {str(te)}"
        except Exception as e:
            return f"Error executing tool '{tool_name}': {str(e)}"

    def run(self):
        console.print(Panel.fit(f"[bold green]Starting Agent Run[/bold green]\nComplaint: [yellow]{self.complaint_path}[/yellow]\nOutputs: [cyan]{self.outputs_dir}[/cyan]"))
        
        context_msg = f"Task File: {self.complaint_path}\nPolicy File: {self.policy_path}\nShop Base URL: {self.base_url}\n\nInitial Step: Please read the policy file and complaint file using read_file tool to begin."
        self.history.append({"role": "user", "content": context_msg})

        step = 0
        while step < self.max_steps:
            step += 1
            console.print(f"\n[bold blue]--- Step {step} / {self.max_steps} ---[/bold blue]")

            history_str = ""
            for item in self.history[-10:]:
                history_str += f"\n[{item['role'].upper()}]: {item['content']}\n"
            
            case_notes_summary = self.notes.to_string()
            prompt = f"Case Notes Summary:\n{case_notes_summary}\n\nRecent History:\n{history_str}"

            try:
                raw_response = self._call_llm(prompt)
                parsed = self._parse_llm_json(raw_response)
            except Exception as e:
                console.print(f"[bold red]LLM Error:[/bold red] {e}")
                obs = f"LLM Error: {e}. Please try again."
                self.history.append({"role": "user", "content": obs})
                continue

            thought = parsed.get("thought", "")
            tool_name = parsed.get("tool", "")
            tool_args = parsed.get("args", {})

            console.print(f"[bold magenta]Thought:[/bold magenta] {thought}")
            console.print(f"[bold green]Tool Call:[/bold green] [cyan]{tool_name}[/cyan]({json.dumps(tool_args)})")

            action_key = f"{tool_name}:{json.dumps(tool_args)}"
            if tool_name != "finish" and self.action_retry_counts.get(action_key, 0) > 3:
                obs = f"Error: Action '{tool_name}' with args {tool_args} failed 3 times in a row. Please change your approach or ask human."
                console.print(f"[bold red]{obs}[/bold red]")
                self.history.append({"role": "assistant", "content": json.dumps(parsed)})
                self.history.append({"role": "user", "content": obs})
                continue

            obs = self.execute_tool(tool_name, tool_args)
            console.print(f"[bold yellow]Observation:[/bold yellow]\n{obs}")

            if obs.startswith("Error:") or "FINISH_REJECTED" in obs:
                self.action_retry_counts[action_key] = self.action_retry_counts.get(action_key, 0) + 1
            else:
                self.action_retry_counts[action_key] = 0

            self.history.append({"role": "assistant", "content": json.dumps(parsed)})
            self.history.append({"role": "user", "content": obs})

            if tool_name == "finish" and "FINISH_ACCEPTED" in obs:
                console.print(Panel.fit(f"[bold green]TASK COMPLETED SUCCESSFULLY AT STEP {step}[/bold green]\n{obs}"))
                self.browser.close()
                return True

            if self.notes.data.get("status") == "blocked_by_human":
                console.print(Panel.fit("[bold red]Task stopped by human refusal/comment.[/bold red]"))
                self.browser.close()
                return False

        console.print(Panel.fit(f"[bold red]Reached maximum step limit ({self.max_steps}). Task aborted.[/bold red]"))
        self.browser.close()
        return False
