/* LazHelper Stage L — portable organisation plans. Import is always preview-only. */
(() => {
  const main = document.querySelector("main");
  if (!main || document.getElementById("stage-l-portable-plans")) return;
  const el = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  };
  const card = el("section", undefined, "workspace-card fk-card");
  card.id = "stage-l-portable-plans";
  card.append(el("p", "STAGE L · PORTABLE ORGANISATION PLANS", "eyebrow"));
  card.append(el("h2", "Take an organisation plan with you."));
  card.append(el("p", "Export a reviewable plan as JSON or CSV, or import a plan created on another machine. Imports are checked against the current workspace and never move files."));
  const grid = el("div", undefined, "fk-grid");
  const exportPanel = el("div", undefined, "fk-panel");
  exportPanel.append(el("h3", "Export a plan"));
  exportPanel.append(el("p", "Enter one or more workspace-relative file paths, one per line. LazHelper builds a fresh plan using your current category rules."));
  const pathsLabel = el("label", "Workspace-relative paths (one per line)");
  pathsLabel.htmlFor = "stage-l-paths";
  const paths = el("textarea"); paths.id = "stage-l-paths"; paths.placeholder = "notes.txt\nAssignments/lab.pdf"; paths.rows = 5;
  paths.setAttribute("autocomplete", "off");
  const formatLabel = el("label", "Export format"); formatLabel.htmlFor = "stage-l-export-format";
  const format = el("select"); format.id = "stage-l-export-format";
  for (const value of ["json", "csv"]) { const option = el("option", value.toUpperCase()); option.value = value; format.append(option); }
  const exportButton = el("button", "Build and download plan", "secondary-button"); exportButton.type = "button";
  exportPanel.append(pathsLabel, paths, formatLabel, format, exportButton);
  const importPanel = el("div", undefined, "fk-panel");
  importPanel.append(el("h3", "Import and validate a plan"));
  importPanel.append(el("p", "Choose a LazHelper JSON or CSV plan. Validation checks source paths, source changes and destination collisions. It does not apply the plan."));
  const fileLabel = el("label", "Plan file"); fileLabel.htmlFor = "stage-l-file";
  const file = el("input"); file.type = "file"; file.id = "stage-l-file"; file.accept = ".json,.csv,application/json,text/csv";
  const importFormatLabel = el("label", "File format"); importFormatLabel.htmlFor = "stage-l-import-format";
  const importFormat = el("select"); importFormat.id = "stage-l-import-format";
  for (const value of ["json", "csv"]) { const option = el("option", value.toUpperCase()); option.value = value; importFormat.append(option); }
  const importButton = el("button", "Validate imported plan", "secondary-button"); importButton.type = "button";
  importPanel.append(fileLabel, file, importFormatLabel, importFormat, importButton);
  grid.append(exportPanel, importPanel);
  const status = el("p", "Plans are previews. Each move still requires explicit approval.", "status-line"); status.id = "stage-l-status"; status.setAttribute("role", "status");
  const output = el("div", undefined, "fk-output"); output.id = "stage-l-output"; output.setAttribute("aria-live", "polite");
  card.append(grid, status, output);
  const footer = main.querySelector("footer");
  if (footer) main.insertBefore(card, footer); else main.append(card);

  const show = (message, error = false) => { status.textContent = message; status.classList.toggle("error", error); };
  const renderPreview = data => {
    output.replaceChildren();
    const summary = el("article", undefined, "fk-result");
    summary.append(el("h3", "Import validation summary"));
    summary.append(el("p", `Valid: ${data.valid_count} · Errors: ${data.error_count} · Stale: ${data.stale_count} · Conflicts: ${data.conflict_count}`));
    summary.append(el("p", data.message));
    output.append(summary);
    for (const item of data.items || []) {
      const row = el("article", undefined, "fk-result");
      row.append(el("h3", item.source));
      row.append(el("p", `Destination: ${item.destination} · Status: ${item.status} · Confidence: ${item.confidence}`));
      row.append(el("p", item.reason));
      row.append(el("p", `Source changed: ${item.source_changed ? "yes" : "no"} · Destination exists: ${item.destination_exists ? "yes" : "no"}`));
      output.append(row);
    }
    for (const item of data.errors || []) {
      const row = el("article", undefined, "fk-result");
      row.append(el("h3", `Item ${item.item}: invalid`)); row.append(el("p", item.reason)); output.append(row);
    }
  };
  exportButton.addEventListener("click", async () => {
    const relative_paths = paths.value.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
    if (!relative_paths.length) return show("Enter at least one file path.", true);
    exportButton.disabled = true;
    try {
      const response = await fetch("/api/plans/export", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({relative_paths, export_format:format.value})});
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not export plan.");
      const blob = new Blob([data.content], {type:data.content_type});
      const url = URL.createObjectURL(blob);
      const link = el("a"); link.href = url; link.download = data.filename; link.click(); URL.revokeObjectURL(url);
      show(`Exported ${data.item_count} plan item(s). No workspace files were changed.`);
    } catch (error) { show(error.message || "Export failed.", true); }
    finally { exportButton.disabled = false; }
  });
  importButton.addEventListener("click", async () => {
    const selected = file.files?.[0];
    if (!selected) return show("Choose a JSON or CSV plan file first.", true);
    if (selected.size > 2_000_000) return show("Plan file exceeds the 2 MB limit.", true);
    importButton.disabled = true;
    try {
      const content = await selected.text();
      const response = await fetch("/api/plans/import", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({content, import_format:importFormat.value})});
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not validate plan.");
      renderPreview(data);
      show("Import validated as a preview only. No files were changed; approve moves separately.", false);
    } catch (error) { show(error.message || "Import failed.", true); }
    finally { importButton.disabled = false; }
  });
})();
