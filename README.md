# 🤖 AutoBrowser - Intelligent AI Agent Overlay

> [!IMPORTANT]
> **Sleek. Modern. Powerful.** A premium glassmorphic desktop interface for Gemini-powered browser automation.

---

## 🌟 Overview
The **AI Agent Overlay** brings the power of **Large Language Models** directly to your desktop. It provides a transparent, floating chat interface that automates complex browser tasks in real-time, allowing you to watch the AI navigate, click, and type as it fulfills your requests.

---

## ✨ Features
- 💎 **Glassmorphic UI**: High-end aesthetic with frosted-glass effects and smooth transitions.
- 🛑 **Direct Control**: Instant Send/Stop toggle to start tasks or halt the AI immediately.
- 🔑 **API Key Persistence**: Your Gemini API key is securely saved to your browser's local storage—no more re-typing.
- 🌐 **Seamless Automation**: Powered by Playwright for robust and intelligent web interaction.
- 📜 **Live Logs**: Real-time feedback window showing the agent's thoughts and actions.

---

## 🛠 Prerequisites
Before you begin, ensure you have the following:
- **Python 3.8+**
- **Microsoft Edge** browser installed.
- **Gemini API Key** (Get one at [Google AI Studio](https://aistudio.google.com/))

---

## 📥 Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup Playwright**
   ```bash
   playwright install msedge
   ```

---

## 🚀 Usage

1. **Start the Application**
   ```bash
   python main.py
   ```

2. **Configure API Key**
   Paste your Gemini API key into the field at the bottom of the drawer. It will save automatically.

3. **Issue a Task**
   Type a request in the input field, for example:
   > *"Find the best-rated Italian restaurant in New York and show me the menu."*

4. **Monitor Progress**
   Watch the logs and the browser window as the agent executes your request. Use the **Stop** button if you need to end the task early.

---

## ⌨️ Controls

| Button | Action |
| :--- | :--- |
| **Send (Arrow)** | Dispatches the task to the AI agent. |
| **Stop (Square)** | Immediately halts current AI execution. |
| **Reset** | Clears the chat history and resets the agent state. |

> [!TIP]
> You can **drag** the overlay anywhere on your screen by clicking and holding any part of the chat drawer.
