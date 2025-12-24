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
            --ink: #0f172a;
            --slate: #1f2937;
            --muted: #4b5563;
            --border: #e5e7eb;
            --panel: #ffffff;
            --canvas: #f4f6fb;
            --accent: #0ea5e9;
            --accent-2: #6366f1;
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #ef4444;
            --shadow-soft: 0 24px 60px rgba(15, 23, 42, 0.12);
            --shadow-strong: 0 18px 48px rgba(14, 165, 233, 0.18);
            --radius-lg: 18px;
            --radius-pill: 999px;
          }

          * {
            box-sizing: border-box;
          }

          body {
            margin: 0;
            color: var(--ink);
            font-family: "Inter", "Segoe UI", system-ui, -apple-system, sans-serif;
            background:
              radial-gradient(circle at 14% 18%, rgba(14, 165, 233, 0.18), transparent 32%),
              radial-gradient(circle at 84% 8%, rgba(99, 102, 241, 0.16), transparent 30%),
              linear-gradient(180deg, #f9fbff 0%, #f4f6fb 100%);
            min-height: 100vh;
          }

          a {
            color: inherit;
            text-decoration: none;
          }

          .app-shell {
            max-width: 1200px;
            margin: 0 auto;
            padding: 32px 20px 64px;
          }

          .app-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid var(--border);
            box-shadow: var(--shadow-soft);
            border-radius: 20px;
            padding: 18px 22px;
            position: sticky;
            top: 16px;
            backdrop-filter: blur(12px);
            z-index: 2;
          }

          .brand {
            display: flex;
            gap: 12px;
            align-items: center;
          }

          .eyebrow {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(14, 165, 233, 0.12);
            color: #0ea5e9;
            border: 1px solid rgba(14, 165, 233, 0.2);
            padding: 6px 10px;
            border-radius: var(--radius-pill);
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            font-size: 12px;
          }

          h1 {
            margin: 6px 0 4px;
            font-size: clamp(2rem, 4vw, 2.6rem);
            letter-spacing: -0.04em;
          }

          .subtitle {
            margin: 0;
            color: var(--muted);
            font-size: 1rem;
          }

          .bar-actions {
            display: flex;
            align-items: center;
            gap: 10px;
          }

          .ghost {
            background: transparent;
            color: var(--ink);
            border: 1px solid var(--border);
            border-radius: var(--radius-pill);
            padding: 10px 14px;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 8px;
          }

          .hero {
            margin: 22px 0 18px;
            padding: 18px;
            border-radius: var(--radius-lg);
            background: linear-gradient(120deg, rgba(14, 165, 233, 0.12), rgba(99, 102, 241, 0.08));
            border: 1px solid rgba(14, 165, 233, 0.18);
            box-shadow: var(--shadow-soft);
          }

          .hero p {
            margin: 6px 0 0;
            max-width: 880px;
            color: #0f172a;
            font-size: 1.02rem;
          }

          main {
            margin-top: 24px;
          }

          .layout {
            display: grid;
            grid-template-columns: minmax(360px, 1fr) minmax(420px, 1.1fr);
            gap: 20px;
          }

          .panel {
            background: var(--panel);
            border-radius: 22px;
            border: 1px solid var(--border);
            box-shadow: var(--shadow-soft);
            padding: 20px 20px 22px;
            display: flex;
            flex-direction: column;
            gap: 14px;
          }

          .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 8px;
          }

          .panel-header h2 {
            margin: 0;
            letter-spacing: -0.02em;
          }

          .panel-header p {
            margin: 0;
            color: var(--muted);
            font-size: 0.95rem;
          }

          label {
            font-size: 0.9rem;
            letter-spacing: 0.02em;
            display: block;
            margin-bottom: 8px;
            font-weight: 700;
            color: var(--ink);
          }

          textarea,
          input,
          select {
            width: 100%;
            border-radius: 12px;
            border: 1px solid var(--border);
            padding: 12px 12px;
            font-size: 0.97rem;
            font-family: "JetBrains Mono", "SFMono-Regular", ui-monospace, monospace;
            background: #f8fafc;
            transition: border 0.2s ease, box-shadow 0.2s ease;
            color: var(--ink);
          }

          textarea:focus,
          input:focus,
          select:focus {
            outline: none;
            border-color: rgba(14, 165, 233, 0.6);
            box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.12);
          }

          textarea {
            min-height: 170px;
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
            gap: 10px;
            align-items: center;
            margin-top: 4px;
          }

          button {
            border: none;
            border-radius: var(--radius-pill);
            padding: 12px 18px;
            font-family: "Inter", "Segoe UI", sans-serif;
            font-weight: 700;
            letter-spacing: 0.02em;
            cursor: pointer;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 8px;
          }

          button.primary {
            background: linear-gradient(120deg, var(--accent), var(--accent-2));
            color: #fff;
            box-shadow: var(--shadow-strong);
          }

          button.secondary {
            background: #ffffff;
            color: var(--ink);
            border: 1px solid var(--border);
          }

          button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
          }

          button:hover:not(:disabled) {
            transform: translateY(-2px);
          }

          .status {
            font-size: 0.95rem;
            padding: 12px 14px;
            border-radius: 14px;
            border: 1px dashed var(--border);
            background: #f8fafc;
            display: none;
            gap: 10px;
            align-items: center;
            margin-top: 8px;
          }

          .status.error {
            color: var(--danger);
            border-color: rgba(239, 68, 68, 0.5);
            background: rgba(239, 68, 68, 0.06);
          }

          .status.success {
            color: var(--success);
            border-color: rgba(34, 197, 94, 0.4);
            background: rgba(34, 197, 94, 0.06);
          }

          .callout {
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 10px 14px;
            padding: 12px 14px;
            border-radius: 14px;
            background: rgba(14, 165, 233, 0.08);
            border: 1px solid rgba(14, 165, 233, 0.2);
            color: #0ea5e9;
            font-weight: 600;
          }

          .pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 10px;
            border-radius: var(--radius-pill);
            background: rgba(99, 102, 241, 0.12);
            color: var(--accent-2);
            font-size: 0.82rem;
            margin-left: 8px;
            font-weight: 700;
          }

          .results {
            display: none;
            flex-direction: column;
            gap: 16px;
          }

          .results.visible {
            display: flex;
          }

          .results-grid {
            display: grid;
            gap: 16px;
          }

          .result-block {
            background: #f8fafc;
            border-radius: 16px;
            border: 1px solid var(--border);
            padding: 14px 16px;
          }

          .table-block + .table-block {
            margin-top: 12px;
          }

          .table-block h3 {
            margin: 0 0 10px;
          }

          table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.92rem;
            background: #fff;
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
          }

          th,
          td {
            text-align: left;
            padding: 10px 8px;
            border-bottom: 1px solid var(--border);
          }

          th {
            color: var(--muted);
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
          }

          .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 12px;
          }

          #project-meta p {
            margin: 0 0 12px;
            font-size: 1rem;
            color: var(--ink);
          }

          .summary-card {
            padding: 14px 16px;
            border-radius: 14px;
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid var(--border);
            box-shadow: 0 8px 20px rgba(15, 23, 42, 0.04);
          }

          .summary-card span {
            display: block;
            font-size: 0.8rem;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.08em;
          }

          .summary-card strong {
            font-size: 1.2rem;
          }

          .raw-output textarea {
            min-height: 140px;
            font-family: "JetBrains Mono", "SFMono-Regular", ui-monospace, monospace;
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

            .app-bar {
              position: static;
              flex-direction: column;
              align-items: flex-start;
              gap: 12px;
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
        <div class="app-shell">
          <div class="app-bar">
            <div class="brand">
              <span class="eyebrow">INDOT Field Tools</span>
              <div>
                <h1>Erosion Control Agent</h1>
                <p class="subtitle">Matching the Cost Estimate Generator workspace for a unified toolkit.</p>
              </div>
            </div>
            <div class="bar-actions">
              <span class="pill">Desktop-like experience</span>
              <button class="ghost" type="button" id="clear-all-top">Reset form</button>
            </div>
          </div>

          <div class="hero">
            <p>
              Keep the interaction model consistent across roadway tools: drop in project data,
              configure rules, and review outputs side-by-side with clear calls to action. Everything
              runs locally, mirroring the Cost Estimate Generator flow.
            </p>
          </div>

          <main>
            <div class="layout">
              <section class="panel">
                <div class="panel-header">
                  <div>
                    <h2>Project inputs</h2>
                    <p>Same entry flow as the estimator: files, formats, and toggles grouped together.</p>
                  </div>
                  <span class="pill">Step 1 of 2</span>
                </div>
                <form id="project-form">
                  <div class="callout">
                    <span>⇪</span>
                    <div>Load your JSON or YAML directly, or paste values below. Custom rules are optional.</div>
                  </div>
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
                    <textarea id="project-text" placeholder="Paste project YAML or JSON here"></textarea>
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
              <section class="panel">
                <div class="panel-header">
                  <div>
                    <h2>Results</h2>
                    <p>Unified output cards echo the estimator: summary tiles, tables, and export tools.</p>
                  </div>
                  <span class="pill">Step 2 of 2</span>
                </div>
                <div id="results" class="results results-grid">
                  <div id="project-meta"></div>
                  <div class="result-block">
                    <h3>Summary</h3>
                    <div class="summary-grid" id="summary-grid"></div>
                  </div>
                  <div class="result-block" id="llm-section"></div>
                  <div class="result-block" id="temp-practices"></div>
                  <div class="result-block" id="perm-practices"></div>
                  <div class="result-block" id="pay-items"></div>
                  <div class="raw-output result-block">
                    <h3>Raw output</h3>
                    <div class="actions">
                      <button class="secondary" id="download-json" type="button">Download JSON</button>
                      <button class="secondary" id="download-yaml" type="button">Download YAML</button>
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
        </div>
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
          llmSection.style.display = "none";

          let lastOutput = null;
          let lastOutputYaml = "";

          function setStatus(message, kind) {
            statusEl.textContent = message || "";
            statusEl.className = "status";
            statusEl.style.display = message ? "inline-flex" : "none";
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
              llmSection.style.display = "none";
              return;
            }
            llmSection.style.display = "block";
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
            const tempTable = buildTable(
              "Temporary practices",
              ["Practice", "Quantity", "Unit", "Rule"],
              (output.temporary_practices || []).map((item) => [
                item.practice_type,
                item.quantity,
                item.unit,
                item.rule_id,
              ])
            );
            tempPractices.innerHTML = tempTable;
            tempPractices.style.display = tempTable ? "block" : "none";

            const permTable = buildTable(
              "Permanent practices",
              ["Practice", "Quantity", "Unit", "Rule"],
              (output.permanent_practices || []).map((item) => [
                item.practice_type,
                item.quantity,
                item.unit,
                item.rule_id,
              ])
            );
            permPractices.innerHTML = permTable;
            permPractices.style.display = permTable ? "block" : "none";

            const payTable = buildTable(
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
            payItems.innerHTML = payTable;
            payItems.style.display = payTable ? "block" : "none";
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

          function clearAllInputs() {
            projectText.value = "";
            rulesText.value = "";
            projectFileInput.value = "";
            rulesFileInput.value = "";
            llmKey.value = "";
            llmToggle.value = "false";
            setStatus("", "");
            toggleResults(false);
          }

          document.getElementById("load-example").addEventListener("click", () => {
            projectText.value = SAMPLE_PROJECT;
            projectFormat.value = "yaml";
            setStatus("Loaded example project.", "success");
          });

          document.getElementById("clear-all").addEventListener("click", clearAllInputs);
          const clearAllTop = document.getElementById("clear-all-top");
          if (clearAllTop) {
            clearAllTop.addEventListener("click", clearAllInputs);
          }

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
