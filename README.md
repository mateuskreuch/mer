# 🌊 Mer

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Built with Textual](https://img.shields.io/badge/Built%20with-Textual-ff00ff.svg)](https://textual.textualize.io/)

**Mer** is a lightweight, terminal-based process manager (TUI) designed for developers who need to manage multiple background tasks simultaneously. Inspired by the simplicity of a dashboard, Mer lets you start, stop, and monitor logs for all your processes in one place.

---

## ✨ Features

- 🚀 **Multi-process management**: Define your services in a simple YAML file.
- 📚 **Aggregated Logs**: View combined logs from multiple processes or focus on a single one.
- 🔗 **Dependency Support**: Automatically start prerequisite services before running a process.
- ⚡ **Quick Commands**: Run custom shell commands directly in a process's working directory.

---

## 🚀 Getting Started

### Installation

```bash
pip install mer-manager
```

### Usage

Run Mer from anywhere:
```bash
mer
```

---

## ⚙️ Configuration

Mer uses a `processes.yml` file to define your environment.

```yaml
frontend:
  run: "npm run dev"
  cwd: "./web"

backend:
  run: "python app.py"
  cwd: "C:/Documents/api"
  needs: ["database"]

database:
  run: "docker-compose up redis"
```

### Options:
- `run`: The command to execute.
- `cwd` (optional): The working directory for the process and where it'll be run.
- `needs` (optional): A list of process names that must be running before this one starts.

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
| :--- | :--- |
| `Enter` | Toggle the selected process (Start/Stop) |
| `Space` | Pin/Unpin the selected process's logs |
| `R` | Run a custom command in the process's `cwd` |
| `Q` | Quit Mer |
| `Esc` | Close input dialogs |

---

## 🛠️ Running Commands (`R`)

When you press `R` on a selected process, Mer opens an input dialog. This allows you to run ad-hoc commands (like `npm install`, `git status`, or custom scripts) in a separate shell window that opens directly in that process's working directory.

*Note: This feature requires a `cwd` to be configured for the process.*

---

## 📝 License

This project is licensed under the MIT License.
