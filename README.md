Markdown


# Python Kanban Board

A lightweight, feature-rich desktop Kanban task manager written in **pure Python** using **Tkinter** for the user interface and **SQLite** for persistent local storage.

---

## ⚡ Key Features

* **📋 Three-Column Workflow:** Organize tasks seamlessly across **To Do**, **In Progress**, and **Done**.
* **🚀 Quick Task Management:** Add, edit, or delete tasks with ease (double-click a task to quickly edit it).
* **↔️ Easy Task Movement:** Shift tasks between columns using intuitive UI buttons or shortcut keys.
* **⏰ Priorities & Deadlines:** Set high, medium, or low priorities and assign deadlines. Overdue tasks are automatically highlighted in red.
* **🔍 Search & Filter:** Live text search through task titles and descriptions, alongside filtering by priority.
* **📊 Analytics & Charts:** Built-in statistics window featuring a custom canvas bar chart showing task distributions, completion percentage, and overdue counts.
* **💾 Data Persistence & Export:** Automatically saves all data locally to `kanban.db` and supports exporting your task board to Excel-ready CSV files.
* **🌐 Zero Dependencies:** Built strictly with standard Python libraries. No `pip install` required!

---

## 🖥️ Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Ctrl + N` | Create a new task |
| `Delete` | Delete the currently selected task |
| `Double Click` | Edit selected task |
| `Escape` | Close active dialog window |

---

## 🚀 Quick Start

### Prerequisites
* Python **3.8+** installed (Tkinter usually comes pre-installed with Python on Windows/macOS).

### How to Run

1. Clone or download this repository.
2. Run the application directly:

```bash
python kanban_board.py
🛠️ Built With
Tkinter: Standard GUI library for Python.

SQLite3: Embedded relational database engine.

CSV Module: For UTF-8 encoded data exports.

📄 License
This project is open-source and available under the MIT License.
