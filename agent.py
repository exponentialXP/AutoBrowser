import os
import json
import asyncio
import datetime
from playwright.async_api import async_playwright
import google.generativeai as genai
from utils import resize_image, add_grid, mark_click, SYSTEM_PROMPT
from dotenv import load_dotenv

# Silence GRPC and ABSL logs to prevent confusing error messages
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GLOG_minloglevel"] = "2"

class WebAgent:
    def __init__(self, api_key=None, model_name="gemini-3-flash-preview", logger=None): 
        self.api_key = api_key
        self.model_name = model_name
        self.model = None
        self.history = []
        self.user_data_dir = os.path.join(os.getcwd(), "browser_profile")
        self.session_file = os.path.join(self.user_data_dir, "last_url.txt")
        self.logger = logger # Callback for status updates
        self.paused = False
        self.stopped = False
        
        # Debug setup
        self.run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.debug_dir = os.path.join(os.getcwd(), "debug", f"run_{self.run_id}")
        os.makedirs(self.debug_dir, exist_ok=True)
        self._init_html_report()

        # Browser state
        self.playwright = None
        self.context = None
        self.page = None

    def log(self, message, type="info"):
        if self.logger:
            asyncio.create_task(self.logger(message, type))
        print(f"[{type.upper()}] {message}")

    def _init_html_report(self):
        report_path = os.path.join(self.debug_dir, "report.html")
        html = """
        <html>
        <head>
            <title>Web Agent Debug Report</title>
            <style>
                body { font-family: sans-serif; background: #1a1a1a; color: #eee; padding: 20px; }
                .step { border: 1px solid #444; margin-bottom: 30px; padding: 15px; border-radius: 8px; background: #2a2a2a; }
                .thought { font-style: italic; color: #aaa; margin-bottom: 15px; }
                .views { display: flex; gap: 20px; }
                .view { flex: 1; }
                img { width: 100%; border-radius: 4px; border: 1px solid #555; }
                h3 { margin-top: 0; color: #00d4ff; }
                .label { font-weight: bold; margin-bottom: 5px; }
            </style>
        </head>
        <body>
            <h1>Agent Run: """ + self.run_id + """</h1>
            <div id="steps"></div>
        </body>
        </html>
        """
        with open(report_path, "w") as f:
            f.write(html)

    def _add_to_report(self, step, thought, ai_view_path, action_results=None):
        report_path = os.path.join(self.debug_dir, "report.html")
        with open(report_path, "r") as f:
            content = f.read()
        
        actions_html = ""
        if action_results:
            for i, res_path in enumerate(action_results):
                actions_html += f'<div class="view"><div class="label">Action {i} Verification</div><img src="{os.path.basename(res_path)}"></div>'

        new_step = f"""
        <div class="step">
            <h3>Step {step}</h3>
            <div class="thought"><b>Thought:</b> {thought}</div>
            <div class="views">
                <div class="view"><div class="label">AI View (Grid Version)</div><img src="{os.path.basename(ai_view_path)}"></div>
                {actions_html}
            </div>
        </div>
        """
        content = content.replace('<div id="steps"></div>', new_step + '<div id="steps"></div>')
        with open(report_path, "w") as f:
            f.write(content)

    async def start_browser(self, url=None):
        """Initializes the browser and persists the context."""
        if self.page:
            return

        if not url:
            if os.path.exists(self.session_file):
                with open(self.session_file, "r") as f:
                    url = f.read().strip()
            
            if not url or not url.startswith("http"):
                url = "https://www.google.com"

        self.log(f"Starting browser at {url}...")
        
        self.playwright = await async_playwright().start()
        self.context = await self.playwright.chromium.launch_persistent_context(
            self.user_data_dir,
            channel="msedge",
            headless=False,
            viewport={'width': 1280, 'height': 720}
        )
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        await self.page.goto(url)
        self.log("Browser ready. Agent taking over.")

    async def stop_browser(self):
        """Stops the browser and playwright."""
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        self.page = None
        self.context = None
        self.playwright = None

    async def run(self, task, api_key=None):
        # Configure API key and model if provided or if not already set
        current_key = api_key or self.api_key
        if not current_key:
            self.log("No API key provided. Please enter your Gemini API key.", "error")
            return

        if current_key != self.api_key or not self.model:
            self.api_key = current_key
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)

        # Ensure browser is started
        if not self.page:
            await self.start_browser()

        self.log(f"Starting task: {task}")
        
        try:
            for step in range(30): # Increased steps for longer tasks if needed
                # Wait loop if paused
                while self.paused and not self.stopped:
                    await asyncio.sleep(0.5)
                
                if self.stopped:
                    self.log("Agent stopped by user.", "warning")
                    self.stopped = False # Reset for next time
                    break

                if self.page.is_closed():
                    # Try to find another page if this one was closed
                    if self.context.pages:
                        self.page = self.context.pages[0]
                        if self.page.is_closed(): break
                    else:
                        self.log("All browser pages were closed. Exiting.", "error")
                        break

                try:
                    # 1. Take a screenshot
                    self.log(f"Step {step}: Analyzing screen...")
                    raw_screenshot = await self.page.screenshot()
                    
                    # Process for AI (Resize + Grid)
                    resized_screenshot = resize_image(raw_screenshot)
                    grid_screenshot = add_grid(resized_screenshot)
                    
                    # Save original resized for marking
                    debug_img = resized_screenshot
                    
                    prompt = [
                        SYSTEM_PROMPT,
                        f"User Task: {task}",
                        f"History: {json.dumps(self.history[-3:])}", # Only send last 3 steps to save tokens
                        {
                            "mime_type": "image/jpeg",
                            "data": grid_screenshot
                        },
                        "Respond in JSON. Be precise with coordinates using the grid."
                    ]

                    # 3. Get response from Gemini with Retry logic
                    response = None
                    max_retries = 10
                    empty_retries = 0
                    for attempt in range(max_retries):
                        try:
                            response = self.model.generate_content(prompt)
                            
                            # Check for empty response
                            if not response or not response.candidates or not response.candidates[0].content.parts:
                                if empty_retries < 2:
                                    empty_retries += 1
                                    self.log(f"Empty response received. Retrying ({empty_retries}/2)...", "warning")
                                    await asyncio.sleep(2)
                                    continue
                                else:
                                    self.log("AI returned empty content after retries.", "error")
                                    break
                            
                            break
                        except Exception as e:
                            if "429" in str(e) or "ResourceExhausted" in str(e):
                                wait_time = (2 ** attempt) + 3 # 4, 5, 7, 11, 19...
                                self.log(f"Rate limit reached. Trying again in {wait_time}s", "warning")
                                await asyncio.sleep(wait_time)
                            else:
                                raise e
                    
                    if not response or not response.candidates or not response.candidates[0].content.parts:
                        if not self.stopped:
                            self.log("Fatal Error: Could not get valid AI response. Stopping agent.", "error")
                        break
                        
                    text = response.text.strip()
                    if "```json" in text:
                        text = text.split("```json")[-1].split("```")[0].strip()
                    elif "```" in text:
                        text = text.split("```")[-1].split("```")[0].strip()
                    
                    res_json = json.loads(text)
                    self.history.append(res_json)
                    self.history = self.history[-10:] # Keep only last 10 steps
                    thought = res_json.get("thought", "None")
                    self.log(f"AI Thought: {thought}")
                    
                    # Save session state (last URL)
                    try:
                        current_url = self.page.url
                        with open(self.session_file, "w") as f:
                            f.write(current_url)
                    except:
                        pass
                    
                    # Save what the AI SAW
                    ai_view_path = os.path.join(self.debug_dir, f"step_{step}_ai.jpg")
                    with open(ai_view_path, "wb") as f:
                        f.write(grid_screenshot)

                    # Handle both single 'action' and multiple 'actions'
                    actions = res_json.get("actions", [])
                    if not actions and res_json.get("action"):
                        actions = [{"action": res_json.get("action"), "params": res_json.get("params", [])}]

                    action_results = []
                    for i, act_obj in enumerate(actions):
                        if self.paused or self.stopped: 
                            break
                        
                        if self.page.is_closed(): break
                        
                        action = act_obj.get("action")
                        params = act_obj.get("params", [])

                        if action == "click" or action == "type" or action == "paste":
                            if action == "click":
                                x_pct, y_pct = params[0], params[1]
                            else:
                                x_pct, y_pct = params[1], params[2]

                            # Save debug image
                            marked_img = mark_click(debug_img, x_pct, y_pct)
                            click_view_path = os.path.join(self.debug_dir, f"step_{step}_click_{i}.jpg")
                            with open(click_view_path, "wb") as f:
                                f.write(marked_img)
                            action_results.append(click_view_path)
                            self.log(f"Performing {action} at ({x_pct}, {y_pct}).")
                            
                            # Perform action
                            await self.page.mouse.click(x_pct * 1280 / 1000, y_pct * 720 / 1000)
                            if action == "type":
                                await self.page.keyboard.type(params[0])
                                await self.page.keyboard.press("Enter")
                            elif action == "paste":
                                await self.page.keyboard.insert_text(params[0])
                                await self.page.keyboard.press("Enter")
                        
                        elif action == "scroll":
                            direction = params[0]
                            self.log(f"Scrolling {direction}...")
                            await self.page.focus("body")
                            await self.page.keyboard.press("PageDown" if direction == "down" else "PageUp")
                        elif action == "ask_user":
                            self.log(f"ASKING USER: {params[0]}", "warning")
                            # In the new UI mode, we should ideally wait for a message back.
                            # For now, we'll just log it and pause the loop in a non-blocking way if possible.
                            # But standard async agentic flow often skips standard input.
                            break 
                        elif action == "wait":
                            self.log("Waiting for page to load...")
                            await asyncio.sleep(2)
                        elif action == "finish":
                            self.log("Task finished successfully!", "success")
                            self._add_to_report(step, thought, ai_view_path, action_results)
                            return
                        
                        await asyncio.sleep(1.5)
                    
                    # Add step to HTML report
                    self._add_to_report(step, thought, ai_view_path, action_results)
                except json.JSONDecodeError as je:
                    self.log(f"AI response format error: {je}", "error")
                    break
                except Exception as e:
                    if "Target page, context or browser has been closed" in str(e):
                        self.log("Browser window closed unexpectedly.", "error")
                    else:
                        self.log(f"Error: {e}", "error")
                        import traceback
                        traceback.print_exc()
                    break
        except Exception as e:
            self.log(f"Critical loop error: {e}", "error")
        # Removed context.close() from finally to keep browser open

if __name__ == "__main__":
    import sys
    task = "Find the best place to live in the world"
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    
    agent = WebAgent()
    asyncio.run(agent.run(task))
