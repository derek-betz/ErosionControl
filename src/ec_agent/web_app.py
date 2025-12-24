"""Local web UI for EC Agent."""

from __future__ import annotations

import json
import textwrap
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import yaml

from ec_agent.io_utils import parse_project_text, parse_rules_text, resolve_api_key
from ec_agent.llm_adapter import MockLLMAdapter, OpenAIAdapter
from ec_agent.rules_engine import RulesEngine

INDEX_HTML = textwrap.dedent(
    """\
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>EC Agent Web UI</title>
        <style>
          :root {
            --ink: #13261f;
            --pine: #2e5f4b;
            --moss: #6d8a7a;
            --clay: #8a5a3b;
            --sand: #efe6d6;
            --sky: #cfe6f5;
            --sun: #f3c266;
            --paper: #f9f4ea;
            --accent: #d67a4a;
            --line: rgba(19, 38, 31, 0.14);
            --shadow: 0 22px 50px rgba(19, 38, 31, 0.18);
          }

          * {
            box-sizing: border-box;
          }

          body {
            margin: 0;
            color: var(--ink);
            font-family: "Georgia", "Times New Roman", serif;
            background:
              radial-gradient(circle at 10% 20%, rgba(243, 194, 102, 0.35), transparent 45%),
              radial-gradient(circle at 85% 10%, rgba(207, 230, 245, 0.6), transparent 50%),
              linear-gradient(120deg, #f2e9d8 0%, #f7f1e6 55%, #e8f1f7 100%);
            min-height: 100vh;
          }

          body::before {
            content: "";
            position: fixed;
            inset: -20% 0 auto 0;
            height: 40%;
            background: linear-gradient(130deg, rgba(46, 95, 75, 0.18), transparent 70%);
            pointer-events: none;
          }

          header {
            padding: 48px 24px 32px;
            max-width: 1200px;
            margin: 0 auto;
            animation: rise 0.8s ease;
          }

          .badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 14px;
            border-radius: 999px;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.7);
            font-family: "Trebuchet MS", "Lucida Grande", sans-serif;
            text-transform: uppercase;
            letter-spacing: 0.2em;
            font-size: 11px;
            font-weight: 700;
          }

          h1 {
            margin: 18px 0 10px;
            font-family: "Trebuchet MS", "Lucida Grande", sans-serif;
            font-size: clamp(2rem, 4vw, 3.2rem);
            letter-spacing: -0.02em;
          }

          .hero {
            font-size: 1.05rem;
            max-width: 720px;
            color: #344f42;
          }

          main {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 24px 64px;
          }

          .layout {
            display: grid;
            gap: 24px;
            grid-template-columns: minmax(320px, 1fr) minmax(320px, 1.1fr);
          }

          .card {
            background: var(--paper);
            border-radius: 24px;
            padding: 24px;
            box-shadow: var(--shadow);
            border: 1px solid rgba(19, 38, 31, 0.08);
            animation: rise 0.7s ease;
          }

          .card h2 {
            margin: 0 0 16px;
            font-family: "Trebuchet MS", "Lucida Grande", sans-serif;
          }

          .card p {
            margin: 0 0 16px;
            color: #3b5a4d;
          }

          label {
            font-family: "Trebuchet MS", "Lucida Grande", sans-serif;
            font-size: 0.9rem;
            letter-spacing: 0.02em;
            display: block;
            margin-bottom: 8px;
          }

          textarea,
          input,
          select {
            width: 100%;
            border-radius: 12px;
            border: 1px solid var(--line);
            padding: 12px;
            font-size: 0.95rem;
            font-family: "Courier New", Courier, monospace;
            background: rgba(255, 255, 255, 0.9);
          }

          textarea {
            min-height: 180px;
            resize: vertical;
          }

          .field {
            margin-bottom: 16px;
          }

          .row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
          }

          .actions {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            align-items: center;
          }

          button {
            border: none;
            border-radius: 999px;
            padding: 12px 22px;
            font-family: "Trebuchet MS", "Lucida Grande", sans-serif;
            font-weight: 700;
            letter-spacing: 0.04em;
            cursor: pointer;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
          }

          button.primary {
            background: var(--pine);
            color: #fff;
            box-shadow: 0 14px 30px rgba(46, 95, 75, 0.3);
          }

          button.secondary {
            background: #ffffff;
            color: var(--ink);
            border: 1px solid var(--line);
          }

          button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
          }

          button:hover:not(:disabled) {
            transform: translateY(-2px);
          }

          .status {
            margin-top: 14px;
            font-size: 0.95rem;
          }

          .status.error {
            color: #9b2b1f;
          }

          .status.success {
            color: #2e5f4b;
          }

          .pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 999px;
            background: rgba(214, 122, 74, 0.14);
            color: #7a3c22;
            font-size: 0.8rem;
            margin-left: 8px;
          }

          .results {
            display: none;
            flex-direction: column;
            gap: 16px;
          }

          .results.visible {
            display: flex;
          }

          table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.92rem;
          }

          th,
          td {
            text-align: left;
            padding: 10px 8px;
            border-bottom: 1px solid var(--line);
          }

          th {
            font-family: "Trebuchet MS", "Lucida Grande", sans-serif;
            color: #3a5a4b;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
          }

          .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 12px;
          }

          #project-meta p {
            margin: 0 0 12px;
            font-size: 1rem;
            color: #2e5f4b;
          }

          .summary-card {
            padding: 14px 16px;
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.8);
            border: 1px solid var(--line);
          }

          .summary-card span {
            display: block;
            font-size: 0.8rem;
            color: #5b776a;
            text-transform: uppercase;
            letter-spacing: 0.08em;
          }

          .summary-card strong {
            font-size: 1.2rem;
          }

          .raw-output textarea {
            min-height: 140px;
            font-family: "Courier New", Courier, monospace;
          }

          .spinner {
            display: none;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            border: 2px solid rgba(255, 255, 255, 0.4);
            border-top-color: #fff;
            animation: spin 1s linear infinite;
          }

          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }

          @keyframes rise {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
          }

          @media (max-width: 960px) {
            .layout {
              grid-template-columns: 1fr;
            }
          }

          @media (prefers-reduced-motion: reduce) {
            * {
              animation-duration: 0.001ms !important;
              animation-iteration-count: 1 !important;
              transition-duration: 0.001ms !important;
            }
          }
        </style>
      </head>
      <body>
        <header>
          <span class="badge">EC Agent</span>
          <h1>Erosion control recommendations in a web workspace</h1>
          <p class="hero">
            Drop in project YAML or JSON, run the rules engine, and review practices,
            pay items, and cost summaries in one place. Everything runs locally.
          </p>
        </header>
        <main>
          <div class="layout">
            <section class="card">
              <h2>Project input</h2>
              <p>Paste project data or load a file. The app never leaves your machine.</p>
              <form id="project-form">
                <div class="field">
                  <label for="project-file">Project file (YAML or JSON)</label>
                  <input id="project-file" type="file" accept=".yaml,.yml,.json">
                </div>
                <div class="field">
                  <label for="project-format">Project format</label>
                  <select id="project-format">
                    <option value="auto">Auto detect</option>
                    <option value="yaml">YAML</option>
                    <option value="json">JSON</option>
                  </select>
                </div>
                <div class="field">
                  <label for="project-text">Project input</label>
                  <textarea id="project-text"></textarea>
                </div>
                <div class="field">
                  <label for="rules-file">Custom rules file (optional)</label>
                  <input id="rules-file" type="file" accept=".yaml,.yml">
                </div>
                <div class="field">
                  <label for="rules-text">Custom rules YAML (optional)</label>
                  <textarea id="rules-text" placeholder="Paste custom rules YAML here"></textarea>
                </div>
                <div class="row">
                  <div class="field">
                    <label for="llm-toggle">LLM enhancement</label>
                    <select id="llm-toggle">
                      <option value="false">Off</option>
                      <option value="true">On</option>
                    </select>
                  </div>
                  <div class="field">
                    <label for="llm-key">OpenAI API key (optional)</label>
                    <input id="llm-key" type="password" placeholder="sk-...">
                  </div>
                </div>
                <div class="actions">
                  <button class="primary" id="run-btn" type="submit">
                    Run analysis
                    <span class="spinner" id="run-spinner"></span>
                  </button>
                  <button class="secondary" id="load-example" type="button">Load example</button>
                  <button class="secondary" id="clear-all" type="button">Clear</button>
                </div>
                <div id="status" class="status"></div>
              </form>
            </section>
            <section class="card">
              <h2>Results</h2>
              <div id="results" class="results">
                <div id="project-meta"></div>
                <div>
                  <h3>Summary</h3>
                  <div class="summary-grid" id="summary-grid"></div>
                </div>
                <div id="llm-section"></div>
                <div id="temp-practices"></div>
                <div id="perm-practices"></div>
                <div id="pay-items"></div>
                <div class="raw-output">
                  <h3>Raw output</h3>
                  <div class="actions">
                    <button class="secondary" id="download-json" type="button">
                      Download JSON
                    </button>
                    <button class="secondary" id="download-yaml" type="button">
                      Download YAML
                    </button>
                  </div>
                  <div class="field">
                    <label for="raw-json">JSON</label>
                    <textarea id="raw-json" readonly></textarea>
                  </div>
                  <div class="field">
                    <label for="raw-yaml">YAML</label>
                    <textarea id="raw-yaml" readonly></textarea>
                  </div>
                </div>
              </div>
              <p id="results-placeholder">
                Results will appear here after you run the analysis.
              </p>
            </section>
          </div>
        </main>
        <script>
          const SAMPLE_PROJECT = `project_name: Highway 101 Widening Project
    jurisdiction: California Department of Transportation (Caltrans)
    total_disturbed_acres: 5.2
    predominant_soil: clay
    predominant_slope: moderate
    average_slope_percent: 18.5

    drainage_features:
      - id: INLET-001
        type: inlet
        location: Station 10+50, North side
        drainage_area_acres: 2.3
        additional_properties:
          inlet_type: curb_inlet
          grate_size: 24x36
      - id: INLET-002
        type: inlet
        location: Station 15+75, South side
        drainage_area_acres: 1.8
        additional_properties:
          inlet_type: curb_inlet
          grate_size: 24x36
      - id: OUTFALL-001
        type: outfall
        location: Station 20+00, West side
        drainage_area_acres: 4.1
        additional_properties:
          outfall_pipe_diameter: 36

    phases:
      - phase_id: PHASE-1
        name: Clearing and Grubbing
        duration_days: 15
        disturbed_acres: 5.2
        description: Initial site preparation and vegetation removal
      - phase_id: PHASE-2
        name: Grading and Excavation
        duration_days: 45
        disturbed_acres: 5.2
        description: Cut and fill operations, slope shaping
      - phase_id: PHASE-3
        name: Paving and Finishing
        duration_days: 30
        disturbed_acres: 3.0
        description: Asphalt paving, final grading, and permanent EC measures

    metadata:
      project_engineer: Jane Smith, PE
      contractor: ABC Construction Inc.
      estimated_start_date: "2024-03-01"
      regulatory_permit: NPDES Permit CA0123456
    `;

          const projectFileInput = document.getElementById("project-file");
          const projectText = document.getElementById("project-text");
          const projectFormat = document.getElementById("project-format");
          const rulesFileInput = document.getElementById("rules-file");
          const rulesText = document.getElementById("rules-text");
          const llmToggle = document.getElementById("llm-toggle");
          const llmKey = document.getElementById("llm-key");
          const statusEl = document.getElementById("status");
          const resultsEl = document.getElementById("results");
          const resultsPlaceholder = document.getElementById("results-placeholder");
          const projectMeta = document.getElementById("project-meta");
          const summaryGrid = document.getElementById("summary-grid");
          const tempPractices = document.getElementById("temp-practices");
          const permPractices = document.getElementById("perm-practices");
          const payItems = document.getElementById("pay-items");
          const llmSection = document.getElementById("llm-section");
          const rawJson = document.getElementById("raw-json");
          const rawYaml = document.getElementById("raw-yaml");
          const runBtn = document.getElementById("run-btn");
          const runSpinner = document.getElementById("run-spinner");

          let lastOutput = null;
          let lastOutputYaml = "";

          function setStatus(message, kind) {
            statusEl.textContent = message || "";
            statusEl.className = "status";
            if (kind) {
              statusEl.classList.add(kind);
            }
          }

          function setBusy(isBusy) {
            runBtn.disabled = isBusy;
            runSpinner.style.display = isBusy ? "inline-flex" : "none";
          }

          function escapeHtml(value) {
            return String(value)
              .replace(/&/g, "&amp;")
              .replace(/</g, "&lt;")
              .replace(/>/g, "&gt;")
              .replace(/"/g, "&quot;")
              .replace(/'/g, "&#39;");
          }

          async function readFileAsText(file) {
            if (!file) {
              return "";
            }
            return new Promise((resolve, reject) => {
              const reader = new FileReader();
              reader.onload = () => resolve(reader.result || "");
              reader.onerror = () => reject(reader.error);
              reader.readAsText(file);
            });
          }

          function buildTable(title, columns, rows) {
            if (!rows.length) {
              return "";
            }
            const head = columns
              .map((col) => `<th>${escapeHtml(col)}</th>`)
              .join("");
            const body = rows
              .map((row) => {
                const cells = row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("");
                return `<tr>${cells}</tr>`;
              })
              .join("");
            return `
              <div class="table-block">
                <h3>${escapeHtml(title)}</h3>
                <table>
                  <thead><tr>${head}</tr></thead>
                  <tbody>${body}</tbody>
                </table>
              </div>
            `;
          }

          function renderSummary(summary) {
            summaryGrid.innerHTML = "";
            const entries = Object.entries(summary).filter(
              ([key]) => key !== "llm_insights" && key !== "llm_error" && key !== "llm_notice"
            );
            entries.forEach(([key, value]) => {
              const card = document.createElement("div");
              card.className = "summary-card";
              card.innerHTML = `<span>${escapeHtml(key.replace(/_/g, " "))}</span>
                <strong>${escapeHtml(value)}</strong>`;
              summaryGrid.appendChild(card);
            });
          }

          function renderLLM(summary) {
            const notice = summary.llm_notice;
            const insights = summary.llm_insights;
            const error = summary.llm_error;
            if (!notice && !insights && !error) {
              llmSection.innerHTML = "";
              return;
            }
            const parts = [];
            if (notice) {
              parts.push(`<p><span class="pill">Notice</span> ${escapeHtml(notice)}</p>`);
            }
            if (error) {
              parts.push(`<p><span class="pill">Error</span> ${escapeHtml(error)}</p>`);
            }
            if (insights) {
              parts.push(`<p>${escapeHtml(insights)}</p>`);
            }
            llmSection.innerHTML = `<div>
              <h3>LLM insights</h3>
              ${parts.join("")}
            </div>`;
          }

          function renderOutput(output) {
            const projectName = output.project_name || "Unnamed project";
            const timestamp = output.timestamp || "";
            projectMeta.innerHTML = `<p><strong>${escapeHtml(projectName)}</strong> ${
              timestamp ? `<span class="pill">Generated ${escapeHtml(timestamp)}</span>` : ""
            }</p>`;
            renderSummary(output.summary || {});
            renderLLM(output.summary || {});
            tempPractices.innerHTML = buildTable(
              "Temporary practices",
              ["Practice", "Quantity", "Unit", "Rule"],
              (output.temporary_practices || []).map((item) => [
                item.practice_type,
                item.quantity,
                item.unit,
                item.rule_id,
              ])
            );
            permPractices.innerHTML = buildTable(
              "Permanent practices",
              ["Practice", "Quantity", "Unit", "Rule"],
              (output.permanent_practices || []).map((item) => [
                item.practice_type,
                item.quantity,
                item.unit,
                item.rule_id,
              ])
            );
            payItems.innerHTML = buildTable(
              "Pay items",
              ["Item", "Description", "Quantity", "Unit", "Est cost"],
              (output.pay_items || []).map((item) => [
                item.item_number,
                item.description,
                item.quantity,
                item.unit,
                item.estimated_unit_cost
                  ? `$${(item.estimated_unit_cost * item.quantity).toFixed(2)}`
                  : "N/A",
              ])
            );
          }

          function toggleResults(show) {
            resultsEl.classList.toggle("visible", show);
            resultsPlaceholder.style.display = show ? "none" : "block";
          }

          function downloadContent(filename, content, mime) {
            const blob = new Blob([content], { type: mime });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
          }

          document.getElementById("load-example").addEventListener("click", () => {
            projectText.value = SAMPLE_PROJECT;
            projectFormat.value = "yaml";
            setStatus("Loaded example project.", "success");
          });

          document.getElementById("clear-all").addEventListener("click", () => {
            projectText.value = "";
            rulesText.value = "";
            projectFileInput.value = "";
            rulesFileInput.value = "";
            llmKey.value = "";
            llmToggle.value = "false";
            setStatus("", "");
            toggleResults(false);
          });

          projectFileInput.addEventListener("change", async () => {
            try {
              const text = await readFileAsText(projectFileInput.files[0]);
              projectText.value = text;
              setStatus("Loaded project file.", "success");
            } catch (error) {
              setStatus("Unable to read project file.", "error");
            }
          });

          rulesFileInput.addEventListener("change", async () => {
            try {
              const text = await readFileAsText(rulesFileInput.files[0]);
              rulesText.value = text;
              setStatus("Loaded rules file.", "success");
            } catch (error) {
              setStatus("Unable to read rules file.", "error");
            }
          });

          document.getElementById("project-form").addEventListener("submit", async (event) => {
            event.preventDefault();
            setStatus("", "");
            setBusy(true);
            toggleResults(false);

            const payload = {
              project_text: projectText.value,
              project_format: projectFormat.value,
              rules_text: rulesText.value,
              use_llm: llmToggle.value === "true",
              llm_api_key: llmKey.value,
            };

            try {
              const response = await fetch("/api/process", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
              });
              const data = await response.json();
              if (!response.ok || !data.ok) {
                throw new Error(data.error || "Unable to process the project.");
              }
              lastOutput = data.output;
              lastOutputYaml = data.output_yaml || "";
              renderOutput(lastOutput);
              rawJson.value = JSON.stringify(lastOutput, null, 2);
              rawYaml.value = lastOutputYaml;
              toggleResults(true);
              setStatus("Analysis complete.", "success");
            } catch (error) {
              setStatus(error.message || "Unexpected error.", "error");
            } finally {
              setBusy(false);
            }
          });

          document.getElementById("download-json").addEventListener("click", () => {
            if (!lastOutput) {
              setStatus("Run an analysis before downloading.", "error");
              return;
            }
            downloadContent(
              "ec-agent-output.json",
              JSON.stringify(lastOutput, null, 2),
              "application/json"
            );
          });

          document.getElementById("download-yaml").addEventListener("click", () => {
            if (!lastOutputYaml) {
              setStatus("Run an analysis before downloading.", "error");
              return;
            }
            downloadContent("ec-agent-output.yaml", lastOutputYaml, "text/yaml");
          });
        </script>
      </body>
    </html>
    """
)


class WebRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler for the EC Agent web UI."""

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            self._send_html(INDEX_HTML)
            return
        if self.path == "/health":
            self._send_json(HTTPStatus.OK, {"ok": True})
            return
        if self.path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Not found."})

    def do_POST(self) -> None:
        if self.path != "/api/process":
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Not found."})
            return

        try:
            payload = self._read_json()
            if payload is None:
                raise ValueError("Missing request body.")

            output_dict, output_yaml = process_request(payload)
            self._send_json(
                HTTPStatus.OK,
                {"ok": True, "output": output_dict, "output_yaml": output_yaml},
            )
        except Exception as exc:
            self._send_json(
                HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc) or "Request failed."}
            )

    def _read_json(self) -> dict[str, Any] | None:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            return None
        body = self.rfile.read(content_length).decode("utf-8")
        return json.loads(body)

    def _send_html(self, html: str) -> None:
        data = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: Any) -> None:
        return


def process_request(payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Process a web request payload and return output dict plus YAML."""
    project_text = payload.get("project_text", "")
    project_format = payload.get("project_format", "auto")
    rules_text = payload.get("rules_text", "")
    use_llm = bool(payload.get("use_llm"))
    llm_api_key = payload.get("llm_api_key") or None

    project = parse_project_text(project_text, project_format)

    engine = RulesEngine()
    custom_rules = parse_rules_text(rules_text)
    if custom_rules:
        engine.rules = custom_rules

    output = engine.process_project(project)

    if use_llm:
        llm_notice = None
        try:
            api_key = resolve_api_key(llm_api_key)
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
    output_yaml = yaml.safe_dump(output_dict, default_flow_style=False, sort_keys=False)
    return output_dict, output_yaml


def run(host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True) -> None:
    """Run the EC Agent web UI server."""
    server = ThreadingHTTPServer((host, port), WebRequestHandler)
    display_host = "127.0.0.1" if host == "0.0.0.0" else host
    url = f"http://{display_host}:{port}/"
    print(f"EC Agent Web UI running at {url} (Ctrl+C to stop)")
    if open_browser:
        # Avoid opening the 0.0.0.0 host in browsers.
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down EC Agent Web UI.")
    finally:
        server.server_close()
