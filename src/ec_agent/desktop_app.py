"""Desktop UI for EC Agent."""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
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

        self._palette = self._build_palette()
        self._configure_styles()
        self._build_ui()

    def _build_palette(self) -> dict[str, str]:
        return {
            "base": "#0d1117",
            "hero": "#0f1623",
            "card": "#151b23",
            "surface": "#1b222c",
            "surface_alt": "#1f2833",
            "field": "#0f141b",
            "field_hover": "#16202b",
            "field_active": "#1b2531",
            "outline": "#2b3645",
            "accent": "#2f81f7",
            "accent_active": "#3b8cff",
            "accent_pressed": "#1f6feb",
            "accent_dim": "#244a74",
            "success": "#2ea043",
            "warning": "#d29922",
            "error": "#f85149",
            "text": "#e6edf3",
            "muted": "#9aa7b2",
            "muted_alt": "#7d8590",
        }

    def _configure_styles(self) -> None:
        palette = self._palette
        self.root.configure(background=palette["base"])
        default_font = "{Segoe UI} 11"
        self.root.option_add("*Font", default_font)
        self.root.option_add("*TButton.Padding", 10)
        self.root.option_add("*TEntry*Font", default_font)
        self.root.option_add("*TCombobox*Listbox.font", default_font)

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Background.TFrame", background=palette["base"])
        style.configure("Header.TFrame", background=palette["hero"])
        style.configure("Card.TFrame", background=palette["card"])
        style.configure("CardBody.TFrame", background=palette["card"])
        style.configure("Glass.TFrame", background=palette["surface_alt"], relief=tk.FLAT)
        style.configure("Toolbar.TFrame", background=palette["card"])
        style.configure("StatusBar.TFrame", background=palette["surface_alt"])

        style.configure("TLabel", background=palette["card"], foreground=palette["text"])
        style.configure("Status.TLabel", background=palette["surface_alt"], foreground=palette["muted"])
        style.configure(
            "Heading.TLabel",
            background=palette["hero"],
            foreground=palette["text"],
            font=("Segoe UI Semibold", 20),
        )
        style.configure(
            "Subheading.TLabel",
            background=palette["hero"],
            foreground=palette["muted"],
            font=("Segoe UI", 11),
        )
        style.configure(
            "SectionHeading.TLabel",
            background=palette["card"],
            foreground=palette["text"],
            font=("Segoe UI Semibold", 13),
        )
        style.configure(
            "Body.TLabel",
            background=palette["surface_alt"],
            foreground=palette["text"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "Hint.TLabel",
            background=palette["surface_alt"],
            foreground=palette["muted"],
            font=("Segoe UI", 9),
        )

        style.configure(
            "Filled.TEntry",
            fieldbackground=palette["field"],
            foreground=palette["text"],
            bordercolor=palette["outline"],
            borderwidth=1,
            insertcolor=palette["text"],
        )
        style.map(
            "Filled.TEntry",
            fieldbackground=[("active", palette["field_hover"])],
            bordercolor=[("focus", palette["accent"])],
            foreground=[("disabled", palette["muted"])],
        )

        style.configure(
            "Filled.TCombobox",
            fieldbackground=palette["field"],
            foreground=palette["text"],
            background=palette["field"],
            bordercolor=palette["outline"],
            borderwidth=1,
            arrowcolor=palette["muted"],
        )
        style.map(
            "Filled.TCombobox",
            fieldbackground=[("readonly", palette["field"]), ("hover", palette["field_hover"])],
            bordercolor=[("focus", palette["accent"])],
            foreground=[("disabled", palette["muted"])],
        )

        style.configure(
            "Toggle.TCheckbutton",
            background=palette["card"],
            foreground=palette["text"],
            focuscolor=palette["accent"],
        )
        style.map(
            "Toggle.TCheckbutton",
            foreground=[("disabled", palette["muted"])],
            background=[("active", palette["field_hover"])],
        )

        style.configure(
            "Primary.TButton",
            background=palette["accent"],
            foreground=palette["text"],
            borderwidth=0,
            focusthickness=1,
            focuscolor=palette["accent_active"],
            padding=(18, 10),
        )
        style.map(
            "Primary.TButton",
            background=[
                ("disabled", palette["accent_dim"]),
                ("pressed", palette["accent_pressed"]),
                ("active", palette["accent_active"]),
            ],
            foreground=[("disabled", palette["muted"])],
        )

        style.configure(
            "Secondary.TButton",
            background=palette["surface_alt"],
            foreground=palette["text"],
            borderwidth=0,
            focusthickness=1,
            focuscolor=palette["accent"],
            padding=(14, 8),
        )
        style.map(
            "Secondary.TButton",
            background=[
                ("disabled", palette["surface"]),
                ("pressed", palette["field_active"]),
                ("active", palette["field_hover"]),
            ],
            foreground=[("disabled", palette["muted"])],
        )

        style.configure(
            "EC.TNotebook",
            background=palette["card"],
            borderwidth=0,
        )
        style.configure(
            "EC.TNotebook.Tab",
            background=palette["surface_alt"],
            foreground=palette["text"],
            padding=(12, 8),
        )
        style.map(
            "EC.TNotebook.Tab",
            background=[("selected", palette["card"])],
            foreground=[("selected", palette["text"]), ("disabled", palette["muted"])],
        )

        style.configure(
            "Modern.Vertical.TScrollbar",
            gripcount=0,
            background=palette["surface_alt"],
            troughcolor=palette["surface"],
            bordercolor=palette["surface"],
            lightcolor=palette["surface_alt"],
            darkcolor=palette["surface_alt"],
            arrowcolor=palette["muted"],
        )
        style.map(
            "Modern.Vertical.TScrollbar",
            background=[("active", palette["field_hover"])],
            arrowcolor=[("active", palette["text"])],
        )

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, style="Header.TFrame", padding=(24, 18))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="EC Agent", style="Heading.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text="Erosion control practices and pay items assistant",
            style="Subheading.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

        content = ttk.Frame(self.root, style="Background.TFrame", padding=(24, 16, 24, 16))
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1, uniform="content")
        content.columnconfigure(1, weight=1, uniform="content")
        content.rowconfigure(0, weight=1)

        left_col = ttk.Frame(content, style="Background.TFrame")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left_col.columnconfigure(0, weight=1)
        left_col.rowconfigure(0, weight=1)

        right_col = ttk.Frame(content, style="Background.TFrame")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        right_col.columnconfigure(0, weight=1)
        right_col.rowconfigure(0, weight=1)

        input_card = ttk.Frame(left_col, style="Card.TFrame", padding=(16, 16))
        input_card.grid(row=0, column=0, sticky="nsew")
        input_card.columnconfigure(0, weight=1)
        input_card.rowconfigure(2, weight=1)

        ttk.Label(input_card, text="Project Inputs", style="SectionHeading.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        input_toolbar = ttk.Frame(input_card, style="Toolbar.TFrame")
        input_toolbar.grid(row=1, column=0, sticky="ew", pady=(12, 12))
        ttk.Button(
            input_toolbar,
            text="Load Project",
            command=self.load_project_file,
            style="Secondary.TButton",
        ).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(
            input_toolbar,
            text="Load Rules",
            command=self.load_rules_file,
            style="Secondary.TButton",
        ).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(
            input_toolbar,
            text="Load Example",
            command=self.load_example,
            style="Secondary.TButton",
        ).grid(row=0, column=2)

        notebook = ttk.Notebook(input_card, style="EC.TNotebook")
        notebook.grid(row=2, column=0, sticky="nsew")

        project_tab = ttk.Frame(notebook, padding=10, style="CardBody.TFrame")
        rules_tab = ttk.Frame(notebook, padding=10, style="CardBody.TFrame")
        notebook.add(project_tab, text="Project Input")
        notebook.add(rules_tab, text="Custom Rules")

        self.project_text = self._add_text_area(project_tab, self.project_placeholder)
        self.rules_text = self._add_text_area(rules_tab, self.rules_placeholder)

        options_card = ttk.Frame(left_col, style="Card.TFrame", padding=(16, 16))
        options_card.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        options_card.columnconfigure(1, weight=1)

        ttk.Label(options_card, text="Options", style="SectionHeading.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )
        ttk.Label(options_card, text="Project format", style="Body.TLabel").grid(
            row=1, column=0, sticky="w", padx=(0, 12)
        )
        format_box = ttk.Combobox(
            options_card,
            textvariable=self.project_format,
            values=["auto", "yaml", "json"],
            state="readonly",
            width=12,
            style="Filled.TCombobox",
        )
        format_box.grid(row=1, column=1, sticky="ew")

        ttk.Checkbutton(
            options_card,
            text="Enable LLM enhancement",
            variable=self.use_llm,
            style="Toggle.TCheckbutton",
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))

        ttk.Label(options_card, text="OpenAI API key", style="Body.TLabel").grid(
            row=3, column=0, sticky="w", padx=(0, 12), pady=(10, 0)
        )
        ttk.Entry(
            options_card,
            textvariable=self.api_key_var,
            show="*",
            style="Filled.TEntry",
        ).grid(row=3, column=1, sticky="ew", pady=(10, 0))

        action_row = ttk.Frame(options_card, style="CardBody.TFrame")
        action_row.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        action_row.columnconfigure(0, weight=1)
        action_row.columnconfigure(1, weight=1)
        ttk.Button(
            action_row,
            text="Run Analysis",
            command=self.run_analysis,
            style="Primary.TButton",
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(
            action_row,
            text="Clear",
            command=self.clear_all,
            style="Secondary.TButton",
        ).grid(row=0, column=1, sticky="ew")

        output_card = ttk.Frame(right_col, style="Card.TFrame", padding=(16, 16))
        output_card.grid(row=0, column=0, sticky="nsew")
        output_card.columnconfigure(0, weight=1)
        output_card.rowconfigure(3, weight=1)

        ttk.Label(output_card, text="Results", style="SectionHeading.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        summary_card = ttk.Frame(output_card, style="Glass.TFrame", padding=(12, 10))
        summary_card.grid(row=1, column=0, sticky="ew", pady=(12, 12))
        summary_card.columnconfigure(0, weight=1)
        self.summary_label = ttk.Label(
            summary_card,
            textvariable=self.summary_var,
            style="Body.TLabel",
            wraplength=520,
            justify="left",
        )
        self.summary_label.grid(row=0, column=0, sticky="w")
        summary_card.bind("<Configure>", self._update_summary_wrap)

        output_toolbar = ttk.Frame(output_card, style="Toolbar.TFrame")
        output_toolbar.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        ttk.Button(
            output_toolbar,
            text="Save JSON",
            command=self.save_json,
            style="Secondary.TButton",
        ).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(
            output_toolbar,
            text="Save YAML",
            command=self.save_yaml,
            style="Secondary.TButton",
        ).grid(row=0, column=1)

        output_frame = ttk.Frame(output_card, style="CardBody.TFrame")
        output_frame.grid(row=3, column=0, sticky="nsew")
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

        self.output_text = tk.Text(output_frame, wrap="word", height=24)
        output_scroll = ttk.Scrollbar(
            output_frame,
            orient="vertical",
            command=self.output_text.yview,
            style="Modern.Vertical.TScrollbar",
        )
        self.output_text.configure(yscrollcommand=output_scroll.set)
        self._style_text_widget(self.output_text, read_only=True)
        self.output_text.grid(row=0, column=0, sticky="nsew")
        output_scroll.grid(row=0, column=1, sticky="ns")

        status_bar = ttk.Frame(self.root, style="StatusBar.TFrame", padding=(16, 8))
        status_bar.grid(row=2, column=0, sticky="ew")
        ttk.Label(status_bar, textvariable=self.status_var, style="Status.TLabel").grid(
            row=0, column=0, sticky="w"
        )

    def _add_text_area(self, parent: ttk.Frame, placeholder: str) -> tk.Text:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        text_widget = tk.Text(parent, wrap="word", height=24)
        scroll = ttk.Scrollbar(
            parent,
            orient="vertical",
            command=text_widget.yview,
            style="Modern.Vertical.TScrollbar",
        )
        text_widget.configure(yscrollcommand=scroll.set)
        self._style_text_widget(text_widget, read_only=False)
        text_widget.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        text_widget.insert("1.0", placeholder)
        return text_widget

    def _style_text_widget(self, widget: tk.Text, read_only: bool = False) -> None:
        palette = self._palette
        widget.configure(
            background=palette["field"],
            foreground=palette["text"],
            insertbackground=palette["text"],
            selectbackground=palette["accent"],
            selectforeground=palette["text"],
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=palette["outline"],
            highlightcolor=palette["accent"],
        )
        if read_only:
            widget.configure(state="disabled")

    def _update_summary_wrap(self, event: tk.Event) -> None:
        width = max(event.width - 24, 240)
        self.summary_label.configure(wraplength=width)

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
        self.project_text.insert("1.0", self.project_placeholder)
        self.rules_text.insert("1.0", self.rules_placeholder)
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
    DesktopApp(root)
    root.mainloop()
