"""Kanban-доска задач (tkinter + SQLite).

Возможности:
  - три колонки: К выполнению / В работе / Готово
  - добавление, редактирование, удаление задач (двойной клик = изменить)
  - перемещение задач между колонками кнопками или клавишами
  - приоритеты и сроки, просроченные задачи подсвечиваются красным
  - поиск по тексту и фильтр по приоритету
  - окно статистики с диаграммой
  - экспорт в CSV
Данные хранятся в файле kanban.db рядом с программой.
"""

from __future__ import annotations

import csv
import sqlite3
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

DB_FILE = Path(__file__).with_name("kanban.db")

STATUSES = [("todo", "К выполнению"), ("doing", "В работе"), ("done", "Готово")]
PRIORITIES = {1: "Высокий", 2: "Средний", 3: "Низкий"}
STATUS_COLORS = {"todo": "#4a90d9", "doing": "#f5a623", "done": "#5cb85c"}


# ---------- вспомогательные функции ----------
def parse_date(text: str) -> str:
    """ДД.ММ.ГГГГ -> ГГГГ-ММ-ДД (бросает ValueError при ошибке)."""
    return datetime.strptime(text.strip(), "%d.%m.%Y").strftime("%Y-%m-%d")


def fmt_date(iso) -> str:
    if not iso:
        return "—"
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%d.%m.%Y")


def today_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d")


# ---------- слой данных ----------
class TaskDB:
    """Вся работа с базой данных (без графики)."""

    def __init__(self, path=DB_FILE):
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS tasks (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   title TEXT NOT NULL,
                   description TEXT NOT NULL DEFAULT '',
                   priority INTEGER NOT NULL DEFAULT 2,
                   status TEXT NOT NULL DEFAULT 'todo',
                   deadline TEXT,
                   created TEXT NOT NULL
               )"""
        )
        self.conn.commit()

    def add(self, title, description, priority, deadline) -> int:
        cur = self.conn.execute(
            "INSERT INTO tasks (title, description, priority, deadline, created)"
            " VALUES (?, ?, ?, ?, ?)",
            (title, description, priority, deadline, today_iso()),
        )
        self.conn.commit()
        return cur.lastrowid

    def update(self, task_id, title, description, priority, deadline) -> None:
        self.conn.execute(
            "UPDATE tasks SET title=?, description=?, priority=?, deadline=?"
            " WHERE id=?",
            (title, description, priority, deadline, task_id),
        )
        self.conn.commit()

    def set_status(self, task_id, status) -> None:
        self.conn.execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))
        self.conn.commit()

    def delete(self, task_id) -> None:
        self.conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        self.conn.commit()

    def get(self, task_id):
        return self.conn.execute(
            "SELECT * FROM tasks WHERE id=?", (task_id,)
        ).fetchone()

    def search(self, text="", priority=None) -> list:
        # Фильтруем в Python: SQL-LIKE в SQLite не умеет игнорировать
        # регистр у русских букв.
        rows = self.conn.execute(
            "SELECT * FROM tasks ORDER BY priority, deadline IS NULL, deadline, id"
        ).fetchall()
        text = text.strip().lower()
        result = []
        for r in rows:
            if priority and r["priority"] != priority:
                continue
            if text and text not in r["title"].lower() \
                    and text not in r["description"].lower():
                continue
            result.append(r)
        return result

    def is_overdue(self, row) -> bool:
        return bool(row["deadline"]) and row["deadline"] < today_iso() \
            and row["status"] != "done"

    def stats(self) -> dict:
        rows = self.conn.execute("SELECT * FROM tasks").fetchall()
        counts = {key: 0 for key, _ in STATUSES}
        for r in rows:
            counts[r["status"]] += 1
        return {
            "counts": counts,
            "total": len(rows),
            "overdue": sum(1 for r in rows if self.is_overdue(r)),
        }

    def export_csv(self, path) -> None:
        names = dict(STATUSES)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["ID", "Название", "Описание", "Приоритет",
                             "Статус", "Срок", "Создана"])
            for r in self.search():
                writer.writerow([r["id"], r["title"], r["description"],
                                 PRIORITIES[r["priority"]], names[r["status"]],
                                 fmt_date(r["deadline"]), fmt_date(r["created"])])


# ---------- диалог добавления / редактирования ----------
class TaskDialog(tk.Toplevel):
    def __init__(self, parent, task=None):
        super().__init__(parent)
        self.title("Изменить задачу" if task else "Новая задача")
        self.resizable(False, False)
        self.result = None
        pad = {"padx": 8, "pady": 5}

        ttk.Label(self, text="Название:").grid(row=0, column=0, sticky="w", **pad)
        self.title_var = tk.StringVar(value=task["title"] if task else "")
        entry = ttk.Entry(self, textvariable=self.title_var, width=42)
        entry.grid(row=0, column=1, **pad)

        ttk.Label(self, text="Описание:").grid(row=1, column=0, sticky="nw", **pad)
        self.desc = tk.Text(self, width=42, height=5, wrap="word")
        self.desc.grid(row=1, column=1, **pad)
        if task:
            self.desc.insert("1.0", task["description"])

        ttk.Label(self, text="Приоритет:").grid(row=2, column=0, sticky="w", **pad)
        self.prio = ttk.Combobox(self, values=list(PRIORITIES.values()),
                                 state="readonly", width=20)
        self.prio.current((task["priority"] if task else 2) - 1)
        self.prio.grid(row=2, column=1, sticky="w", **pad)

        ttk.Label(self, text="Срок:").grid(row=3, column=0, sticky="w", **pad)
        self.deadline_var = tk.StringVar(
            value=fmt_date(task["deadline"]) if task and task["deadline"] else "")
        row = ttk.Frame(self)
        row.grid(row=3, column=1, sticky="w", **pad)
        ttk.Entry(row, textvariable=self.deadline_var, width=14).pack(side="left")
        ttk.Label(row, text="  ДД.ММ.ГГГГ (можно пусто)").pack(side="left")

        buttons = ttk.Frame(self)
        buttons.grid(row=4, column=0, columnspan=2, pady=8)
        ttk.Button(buttons, text="Сохранить", command=self.on_ok).pack(side="left", padx=5)
        ttk.Button(buttons, text="Отмена", command=self.destroy).pack(side="left", padx=5)

        entry.bind("<Return>", lambda e: self.on_ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.transient(parent)
        self.grab_set()
        entry.focus_set()
        self.wait_window(self)

    def on_ok(self):
        title = self.title_var.get().strip()
        if not title:
            messagebox.showerror("Ошибка", "Введите название задачи", parent=self)
            return
        deadline = None
        raw = self.deadline_var.get().strip()
        if raw:
            try:
                deadline = parse_date(raw)
            except ValueError:
                messagebox.showerror("Ошибка",
                                     "Неверная дата. Пример: 25.12.2026", parent=self)
                return
        self.result = {
            "title": title,
            "description": self.desc.get("1.0", "end").strip(),
            "priority": self.prio.current() + 1,
            "deadline": deadline,
        }
        self.destroy()


# ---------- главное окно ----------
class KanbanApp:
    def __init__(self, root):
        self.root = root
        self.db = TaskDB()
        root.title("Kanban-доска")
        root.geometry("1000x560")
        root.minsize(800, 420)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())

        self.build_toolbar()
        self.build_columns()
        self.build_buttons()

        root.bind("<Delete>", lambda e: self.delete_task())
        root.bind("<Control-n>", lambda e: self.add_task())
        self.refresh()

    # --- построение интерфейса ---
    def build_toolbar(self):
        bar = ttk.Frame(self.root, padding=8)
        bar.pack(fill="x")
        ttk.Label(bar, text="Поиск:").pack(side="left")
        ttk.Entry(bar, textvariable=self.search_var, width=30).pack(side="left", padx=6)
        ttk.Label(bar, text="Приоритет:").pack(side="left", padx=(12, 0))
        self.prio_filter = ttk.Combobox(
            bar, values=["Все"] + list(PRIORITIES.values()),
            state="readonly", width=12)
        self.prio_filter.current(0)
        self.prio_filter.pack(side="left", padx=6)
        self.prio_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh())

    def build_columns(self):
        frame = ttk.Frame(self.root, padding=(8, 0))
        frame.pack(fill="both", expand=True)
        self.trees = {}
        self.boxes = {}
        for i, (key, name) in enumerate(STATUSES):
            frame.columnconfigure(i, weight=1, uniform="col")
            box = ttk.LabelFrame(frame, text=name, padding=4)
            box.grid(row=0, column=i, sticky="nsew", padx=4)
            frame.rowconfigure(0, weight=1)
            tree = ttk.Treeview(box, columns=("title", "prio", "deadline"),
                                show="headings", selectmode="browse")
            tree.heading("title", text="Задача")
            tree.heading("prio", text="Приоритет")
            tree.heading("deadline", text="Срок")
            tree.column("title", width=150)
            tree.column("prio", width=70, anchor="center")
            tree.column("deadline", width=80, anchor="center")
            tree.tag_configure("overdue", foreground="#c0392b")
            tree.tag_configure("done", foreground="#888888")
            tree.pack(fill="both", expand=True)
            tree.bind("<<TreeviewSelect>>", self.on_select)
            tree.bind("<Double-1>", lambda e: self.edit_task())
            self.trees[key] = tree
            self.boxes[key] = box

    def build_buttons(self):
        bar = ttk.Frame(self.root, padding=8)
        bar.pack(fill="x")
        items = [
            ("Добавить", self.add_task), ("Изменить", self.edit_task),
            ("Удалить", self.delete_task), ("←", lambda: self.move(-1)),
            ("→", lambda: self.move(1)), ("Статистика", self.show_stats),
            ("Экспорт CSV", self.export),
        ]
        for text, cmd in items:
            width = 4 if text in ("←", "→") else 13
            ttk.Button(bar, text=text, command=cmd, width=width).pack(side="left", padx=3)

    # --- выбор и обновление ---
    def on_select(self, event):
        tree = event.widget
        if tree.selection():
            for other in self.trees.values():
                if other is not tree and other.selection():
                    other.selection_remove(other.selection())

    def selected_id(self):
        for tree in self.trees.values():
            if tree.selection():
                return int(tree.selection()[0])
        return None

    def refresh(self):
        keep = self.selected_id()
        for tree in self.trees.values():
            tree.delete(*tree.get_children())

        prio = None
        if self.prio_filter.current() > 0:
            prio = self.prio_filter.current()
        rows = self.db.search(self.search_var.get(), prio)

        counts = {key: 0 for key, _ in STATUSES}
        for r in rows:
            tags = []
            if r["status"] == "done":
                tags.append("done")
            elif self.db.is_overdue(r):
                tags.append("overdue")
            self.trees[r["status"]].insert(
                "", "end", iid=str(r["id"]),
                values=(r["title"], PRIORITIES[r["priority"]], fmt_date(r["deadline"])),
                tags=tags)
            counts[r["status"]] += 1

        for key, name in STATUSES:
            self.boxes[key].config(text=f"{name} ({counts[key]})")

        if keep is not None:
            for tree in self.trees.values():
                if tree.exists(str(keep)):
                    tree.selection_set(str(keep))

    # --- действия ---
    def add_task(self):
        dialog = TaskDialog(self.root)
        if dialog.result:
            self.db.add(**dialog.result)
            self.refresh()

    def edit_task(self):
        task_id = self.selected_id()
        if task_id is None:
            messagebox.showinfo("Подсказка", "Сначала выберите задачу")
            return
        dialog = TaskDialog(self.root, self.db.get(task_id))
        if dialog.result:
            self.db.update(task_id, **dialog.result)
            self.refresh()

    def delete_task(self):
        task_id = self.selected_id()
        if task_id is None:
            return
        task = self.db.get(task_id)
        if messagebox.askyesno("Удаление", f"Удалить задачу «{task['title']}»?"):
            self.db.delete(task_id)
            self.refresh()

    def move(self, direction):
        task_id = self.selected_id()
        if task_id is None:
            messagebox.showinfo("Подсказка", "Сначала выберите задачу")
            return
        keys = [key for key, _ in STATUSES]
        new_index = keys.index(self.db.get(task_id)["status"]) + direction
        if 0 <= new_index < len(keys):
            self.db.set_status(task_id, keys[new_index])
            self.refresh()

    def export(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", initialfile="tasks.csv",
            filetypes=[("CSV файл", "*.csv")])
        if path:
            self.db.export_csv(path)
            messagebox.showinfo("Готово", f"Задачи сохранены:\n{path}")

    def show_stats(self):
        data = self.db.stats()
        win = tk.Toplevel(self.root)
        win.title("Статистика")
        win.resizable(False, False)
        canvas = tk.Canvas(win, width=420, height=250, bg="white", highlightthickness=0)
        canvas.pack(padx=10, pady=10)

        biggest = max(data["counts"].values()) or 1
        base_y = 200
        for i, (key, name) in enumerate(STATUSES):
            count = data["counts"][key]
            height = count / biggest * 150
            x0 = 40 + i * 125
            canvas.create_rectangle(x0, base_y - height, x0 + 80, base_y,
                                    fill=STATUS_COLORS[key], outline="")
            canvas.create_text(x0 + 40, base_y - height - 12, text=str(count),
                               font=("Arial", 12, "bold"))
            canvas.create_text(x0 + 40, base_y + 18, text=name, font=("Arial", 10))
        canvas.create_line(25, base_y, 395, base_y, fill="#999999")

        done = data["counts"]["done"]
        percent = round(done / data["total"] * 100) if data["total"] else 0
        summary = (f"Всего задач: {data['total']}   |   "
                   f"Выполнено: {percent}%   |   Просрочено: {data['overdue']}")
        ttk.Label(win, text=summary).pack(pady=(0, 10))


def main():
    root = tk.Tk()
    KanbanApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
