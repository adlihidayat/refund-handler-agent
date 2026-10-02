import os
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

class BrowserWrapper:
    def __init__(self, base_url="http://127.0.0.1:5000", screenshots_dir=None):
        self.base_url = base_url
        self.screenshots_dir = screenshots_dir
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.elements_map = {}  # {id: selector_or_info}

    def start(self):
        if not self.playwright:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)
            self.context = self.browser.new_context()
            self.page = self.context.new_page()

    def close(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        self.playwright = None
        self.browser = None

    def auto_login_if_needed(self):
        # Checks if current page is login page and attempts login
        url = self.page.url
        content = self.page.content()
        if "/login" in url or "Admin Login" in content or "Username:" in content:
            # Re-login with default admin credentials
            try:
                if self.page.locator("#username").is_visible():
                    self.page.fill("#username", "admin")
                    self.page.fill("#password", "password123")
                    self.page.click("#submit-login")
                    self.page.wait_for_load_state("networkidle")
            except Exception:
                pass

    def open(self, url):
        self.start()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = self.base_url.rstrip("/") + "/" + url.lstrip("/")
        self.page.goto(url)
        self.page.wait_for_load_state("networkidle")
        self.auto_login_if_needed()
        return f"Navigated to {self.page.url}"

    def read(self):
        self.start()
        self.auto_login_if_needed()
        html = self.page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Clear old element map
        self.elements_map = {}
        element_counter = 1

        # We will parse the page to create a readable text representation with numbered elements
        # Identify interactive elements: a, button, input, select, textarea
        lines = []

        # Page title or main text
        page_url = self.page.url
        lines.append(f"URL: {page_url}")
        
        # Traverse DOM body
        body = soup.find('body')
        if not body:
            return "Empty page"

        def process_node(node):
            nonlocal element_counter
            if node.name in ['script', 'style']:
                return

            if node.name == 'a' and node.get('href'):
                text = node.get_text(strip=True) or node.get('id') or 'Link'
                elem_id = element_counter
                element_counter += 1
                href = node.get('href')
                self.elements_map[elem_id] = {
                    'tag': 'a',
                    'text': text,
                    'href': href,
                    'selector': f"a[href='{href}']" if "'" not in href else "a"
                }
                lines.append(f"[{elem_id}] Link: \"{text}\" (href: {href})")

            elif node.name == 'button' or (node.name == 'input' and node.get('type') in ['submit', 'button']):
                text = node.get_text(strip=True) or node.get('value') or node.get('id') or 'Button'
                elem_id = element_counter
                element_counter += 1
                node_id = node.get('id')
                selector = f"#{node_id}" if node_id else f"button:has-text('{text}')"
                self.elements_map[elem_id] = {
                    'tag': 'button',
                    'text': text,
                    'id_attr': node_id,
                    'selector': selector,
                    'is_refund_submit': (node_id == "submit-refund-button" or "Refund" in text)
                }
                lines.append(f"[{elem_id}] Button: \"{text}\"")

            elif node.name in ['input', 'textarea', 'select'] and node.get('type') not in ['submit', 'button', 'hidden']:
                field_type = node.get('type', node.name)
                name = node.get('name', '')
                node_id = node.get('id', '')
                placeholder = node.get('placeholder', '')
                value = node.get('value', '')
                
                elem_id = element_counter
                element_counter += 1
                selector = f"#{node_id}" if node_id else f"[name='{name}']"
                self.elements_map[elem_id] = {
                    'tag': field_type,
                    'name': name,
                    'id_attr': node_id,
                    'selector': selector
                }
                val_str = f" value='{value}'" if value else ""
                ph_str = f" placeholder='{placeholder}'" if placeholder else ""
                lines.append(f"[{elem_id}] Input ({name or node_id}): [{field_type}]{ph_str}{val_str}")

            elif hasattr(node, 'children'):
                # Process plain text in header/p/div or subnodes
                if node.name in ['h1', 'h2', 'h3', 'h4', 'p', 'div', 'li', 'td', 'th', 'span', 'strong']:
                    direct_text = "".join([c for c in node.contents if isinstance(c, str)]).strip()
                    if direct_text:
                        lines.append(direct_text)
                for child in node.children:
                    if hasattr(child, 'name'):
                        process_node(child)

        process_node(body)

        # Deduplicate sequential empty or duplicate lines
        clean_lines = []
        last_line = None
        for line in lines:
            line_str = line.strip()
            if line_str and line_str != last_line:
                clean_lines.append(line_str)
                last_line = line_str

        return "\n".join(clean_lines)

    def click(self, element_id):
        self.start()
        try:
            elem_id = int(element_id)
        except ValueError:
            return f"Error: Invalid element ID '{element_id}'"

        if elem_id not in self.elements_map:
            return f"Error: Element ID [{elem_id}] not found on current page. Please read the page again."

        info = self.elements_map[elem_id]
        selector = info['selector']

        try:
            # Attempt click
            if info.get('id_attr'):
                self.page.click(f"#{info['id_attr']}")
            else:
                self.page.click(selector)
            self.page.wait_for_load_state("networkidle")
            self.auto_login_if_needed()
            return f"Clicked [{elem_id}] {info.get('text', '')}"
        except Exception as e:
            return f"Error clicking element [{elem_id}]: {str(e)}"

    def type_text(self, element_id, text):
        self.start()
        try:
            elem_id = int(element_id)
        except ValueError:
            return f"Error: Invalid element ID '{element_id}'"

        if elem_id not in self.elements_map:
            return f"Error: Element ID [{elem_id}] not found on current page. Please read the page again."

        info = self.elements_map[elem_id]
        selector = info['selector']

        try:
            if info.get('id_attr'):
                self.page.fill(f"#{info['id_attr']}", str(text))
            else:
                self.page.fill(selector, str(text))
            return f"Typed '{text}' into [{elem_id}]"
        except Exception as e:
            return f"Error typing into element [{elem_id}]: {str(e)}"

    def screenshot(self, name):
        self.start()
        if not name.endswith(".png"):
            name += ".png"
        if self.screenshots_dir:
            os.makedirs(self.screenshots_dir, exist_ok=True)
            path = os.path.join(self.screenshots_dir, name)
        else:
            path = name
        self.page.screenshot(path=path)
        return f"Screenshot saved to {path}"
