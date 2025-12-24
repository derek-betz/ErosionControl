"""Desktop UI for EC Agent."""

from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import yaml

from ec_agent.io_utils import parse_project_text, parse_rules_text, resolve_api_key
from ec_agent.llm_adapter import MockLLMAdapter, OpenAIAdapter
from ec_agent.rules_engine import RulesEngine


class DesktopApp:
    """Tkinter-based desktop UI for EC Agent."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("EC Agent Desktop")
        self.root.geometry("1200x820")
        self.root.minsize(1000, 720)

        self.output_json: str | None = None
        self.output_yaml: str | None = None

        self.project_placeholder = "Paste project YAML or JSON."
        self.rules_placeholder = "Paste custom rules YAML (optional)."

        self.project_format = tk.StringVar(value="auto")
        self.use_llm = tk.BooleanVar(value=False)
        self.api_key_var = tk.StringVar(value="")
        self.summary_var = tk.StringVar(value="Run analysis to see summary.")
        self.status_var = tk.StringVar(value="")

        self._build_ui()

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self.root, padding=8)
        toolbar.pack(fill="x")

        ttk.Button(toolbar, text="Load Project", command=self.load_project_file).pack(
            side="left", padx=4
        )
        ttk.Button(toolbar, text="Load Rules", command=self.load_rules_file).pack(
            side="left", padx=4
        )
        ttk.Button(toolbar, text="Load Example", command=self.load_example).pack(
            side="left", padx=4
        )
        ttk.Button(toolbar, text="Run Analysis", command=self.run_analysis).pack(
            side="left", padx=4
        )
        ttk.Button(toolbar, text="Save JSON", command=self.save_json).pack(
            side="left", padx=4
        )
        ttk.Button(toolbar, text="Save YAML", command=self.save_yaml).pack(
            side="left", padx=4
        )
        ttk.Button(toolbar, text="Clear", command=self.clear_all).pack(side="left", padx=4)

        options = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        options.pack(fill="x")

        ttk.Label(options, text="Project format:").pack(side="left")
        format_box = ttk.Combobox(
            options,
            textvariable=self.project_format,
            values=["auto", "yaml", "json"],
            state="readonly",
            width=10,
        )
        format_box.pack(side="left", padx=6)

        ttk.Checkbutton(options, text="LLM enhancement", variable=self.use_llm).pack(
            side="left", padx=8
        )
        ttk.Label(options, text="OpenAI API key (optional):").pack(side="left", padx=6)
        ttk.Entry(options, textvariable=self.api_key_var, show="*", width=28).pack(
            side="left", padx=4
        )

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        project_tab = ttk.Frame(notebook, padding=8)
        rules_tab = ttk.Frame(notebook, padding=8)
        output_tab = ttk.Frame(notebook, padding=8)
        notebook.add(project_tab, text="Project Input")
        notebook.add(rules_tab, text="Custom Rules")
        notebook.add(output_tab, text="Output")

        self.project_text = self._add_text_area(project_tab, self.project_placeholder)
        self.rules_text = self._add_text_area(rules_tab, self.rules_placeholder)

        summary_label = ttk.Label(
            output_tab, textvariable=self.summary_var, wraplength=900, justify="left"
        )
        summary_label.pack(anchor="w", pady=(0, 8))

        self.output_text = tk.Text(output_tab, wrap="word", height=24)
        output_scroll = ttk.Scrollbar(output_tab, orient="vertical", command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=output_scroll.set, state="disabled")
        self.output_text.pack(side="left", fill="both", expand=True)
        output_scroll.pack(side="right", fill="y")

        status_bar = ttk.Frame(self.root, padding=6)
        status_bar.pack(fill="x")
        ttk.Label(status_bar, textvariable=self.status_var).pack(anchor="w")

    def _add_text_area(self, parent: ttk.Frame, placeholder: str) -> tk.Text:
        text_widget = tk.Text(parent, wrap="word", height=24)
        scroll = ttk.Scrollbar(parent, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scroll.set)
        text_widget.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        text_widget.insert("1.0", placeholder)
        return text_widget

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)

    def _set_output(self, output_json: str, output_yaml: str, summary_text: str) -> None:
        self.output_json = output_json
        self.output_yaml = output_yaml
        self.summary_var.set(summary_text)
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", output_json)
        self.output_text.insert("end", "\n\n--- YAML ---\n\n")
        self.output_text.insert("end", output_yaml)
        self.output_text.configure(state="disabled")

    def _load_file(self, title: str, filetypes: list[tuple[str, str]]) -> str | None:
        path = filedialog.askopenfilename(title=title, filetypes=filetypes)
        if not path:
            return None
        return Path(path).read_text(encoding="utf-8")

    def load_project_file(self) -> None:
        text = self._load_file(
            "Open project file", [("YAML files", "*.yaml *.yml"), ("JSON files", "*.json")]
        )
        if text is None:
            return
        self.project_text.delete("1.0", "end")
        self.project_text.insert("1.0", text)
        self._set_status("Loaded project file.")

    def load_rules_file(self) -> None:
        text = self._load_file("Open rules file", [("YAML files", "*.yaml *.yml")])
        if text is None:
            return
        self.rules_text.delete("1.0", "end")
        self.rules_text.insert("1.0", text)
        self._set_status("Loaded rules file.")

    def load_example(self) -> None:
        example_path = Path("examples") / "highway_project.yaml"
        if not example_path.exists():
            messagebox.showerror("Example not found", "examples/highway_project.yaml not found.")
            return
        self.project_text.delete("1.0", "end")
        self.project_text.insert("1.0", example_path.read_text(encoding="utf-8"))
        self.project_format.set("yaml")
        self._set_status("Loaded example project.")

    def clear_all(self) -> None:
        self.project_text.delete("1.0", "end")
        self.rules_text.delete("1.0", "end")
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.configure(state="disabled")
        self.output_json = None
        self.output_yaml = None
        self.summary_var.set("Run analysis to see summary.")
        self._set_status("Cleared.")

    def run_analysis(self) -> None:
        project_text = self.project_text.get("1.0", "end").strip()
        rules_text = self.rules_text.get("1.0", "end").strip()
        if project_text == self.project_placeholder:
            project_text = ""
        if rules_text == self.rules_placeholder:
            rules_text = ""
        try:
            project = parse_project_text(project_text, self.project_format.get())
            engine = RulesEngine()
            custom_rules = parse_rules_text(rules_text)
            if custom_rules:
                engine.rules = custom_rules

            output = engine.process_project(project)
            if self.use_llm.get():
                llm_notice = None
                try:
                    api_key = resolve_api_key(self.api_key_var.get() or None)
                    if api_key:
                        adapter = OpenAIAdapter(api_key=api_key)
                    else:
                        llm_notice = "OpenAI API key not found. Using mock LLM adapter."
                        adapter = MockLLMAdapter()
                    output = adapter.enhance_recommendations(project, output)
                except ImportError:
                    llm_notice = "OpenAI package not installed. Using mock LLM adapter."
                    adapter = MockLLMAdapter()
                    output = adapter.enhance_recommendations(project, output)
                if llm_notice:
                    output.summary["llm_notice"] = llm_notice

            output_dict = output.model_dump(mode="json")
            output_json = json.dumps(output_dict, indent=2)
            output_yaml = yaml.safe_dump(output_dict, default_flow_style=False, sort_keys=False)

            summary_lines = [
                f"Project: {output.project_name}",
                f"Generated: {output.timestamp}",
                f"Temporary practices: {output.summary.get('total_temporary_practices', 0)}",
                f"Permanent practices: {output.summary.get('total_permanent_practices', 0)}",
                f"Pay items: {output.summary.get('total_pay_items', 0)}",
                f"Estimated cost: {output.summary.get('total_estimated_cost', 0)}",
            ]
            if output.summary.get("llm_notice"):
                summary_lines.append(f"LLM notice: {output.summary['llm_notice']}")
            if output.summary.get("llm_error"):
                summary_lines.append(f"LLM error: {output.summary['llm_error']}")

            self._set_output(output_json, output_yaml, "\n".join(summary_lines))
            self._set_status("Analysis complete.")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            self._set_status("Error during analysis.")

    def save_json(self) -> None:
        if not self.output_json:
            messagebox.showinfo("No output", "Run the analysis before saving.")
            return
        path = filedialog.asksaveasfilename(
            title="Save JSON output",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return
        Path(path).write_text(self.output_json, encoding="utf-8")
        self._set_status(f"Saved JSON to {path}")

    def save_yaml(self) -> None:
        if not self.output_yaml:
            messagebox.showinfo("No output", "Run the analysis before saving.")
            return
        path = filedialog.asksaveasfilename(
            title="Save YAML output",
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml *.yml")],
        )
        if not path:
            return
        Path(path).write_text(self.output_yaml, encoding="utf-8")
        self._set_status(f"Saved YAML to {path}")


def run() -> None:
    """Launch the desktop UI."""
    root = tk.Tk()
    app = DesktopApp(root)
    root.mainloop()
