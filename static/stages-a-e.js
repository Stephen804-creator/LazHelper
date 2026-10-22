/* Stages A–E: local workspace intelligence controls. */
(() => {
  const $ = (id) => document.getElementById(id);
  const make = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  };

  const main = document.querySelector("main");
  const footer = main && main.querySelector("footer");
  if (!main) return;

  const section = make("section", undefined, "workspace-card intelligence-card");
  section.id = "workspace-intelligence";
  section.append(
    make("p", "STAGES A–E · WORKSPACE INTELLIGENCE", "eyebrow"),
    make("h2", "Understand how your files fit together."),
    make("p", "Find related files, review possible versions, search document content, explore a lightweight knowledge map, and check workspace health. Every action here is read-only.")
  );

  const searchForm = make("form", undefined, "intelligence-search");
  const searchLabel = make("label", "Search filenames and readable content");
  searchLabel.htmlFor = "intelligence-query";
  const query = make("input");
  query.id = "intelligence-query";
  query.type = "search";
  query.maxLength = 300;
  query.placeholder = "e.g. cloud computing, project report…";
  query.autocomplete = "off";
  const searchButton = make("button", "Search workspace");
  searchButton.type = "submit";
  searchForm.append(searchLabel, query, searchButton);
  section.append(searchForm);

  const actions = make("div", undefined, "intelligence-actions");
  const actionDefs = [
    ["relationships", "A · Related files", "GET", "/api/relationships"],
    ["duplicates", "B · Versions & duplicates", "POST", "/api/duplicates/insights"],
    ["map", "D · Knowledge map", "GET", "/api/knowledge-map"],
    ["health", "E · Workspace health", "GET", "/api/health-report"]
  ];
  actionDefs.forEach(([id, label]) => {
    const button = make("button", label, "secondary-button");
    button.type = "button";
    button.dataset.action = id;
    actions.append(button);
  });
  section.append(actions);

  const statusLine = make("p", "Choose an action to analyse the configured workspace.", "status-line");
  statusLine.id = "intelligence-status";
  statusLine.setAttribute("role", "status");
  const output = make("div", undefined, "intelligence-results");
  output.id = "intelligence-results";
  output.setAttribute("aria-live", "polite");
  section.append(statusLine, output);
  if (footer) main.insertBefore(section, footer); else main.append(section);

  function currentRoot() {
    return ($("relative-path")?.value || ".").trim() || ".";
  }
  function setStatus(text, error = false) {
    statusLine.textContent = text;
    statusLine.classList.toggle("error", error);
  }
  function addResult(title, description, details) {
    const card = make("article", undefined, "intelligence-result-card");
    card.append(make("h3", title));
    if (description) card.append(make("p", description));
    if (details && details.length) {
      const list = make("ul");
      details.slice(0, 80).forEach((detail) => list.append(make("li", detail)));
      card.append(list);
    }
    output.append(card);
  }
  function showData(action, data) {
    output.replaceChildren();
    if (action === "relationships") {
      addResult(
        `${data.relationship_count || 0} possible relationships`,
        data.message,
        (data.relationships || []).map((r) =>
          `${r.source} ↔ ${r.target} · ${r.relationship} · ${Math.round(r.score * 100)}% · ${r.evidence.join("; ")}`
        )
      );
    } else if (action === "duplicates") {
      addResult(`${data.exact_duplicate_files || 0} exact duplicate files`,
        "Exact groups are byte-for-byte matches. Version families and similar text are review hints only.",
        (data.exact_duplicate_groups || []).map((g) => `Exact match: ${g.files.map((f) => f.path).join(" · ")}`)
          .concat((data.version_families || []).map((g) => `Possible version family “${g.base_name}”: ${g.files.map((f) => f.path).join(" · ")}`))
          .concat((data.similar_content_pairs || []).map((g) => `Similar text (${Math.round(g.token_jaccard * 100)}%): ${g.files.join(" · ")}`))
          .concat((data.extraction_notes || []).map((g) => `Could not inspect ${g.path}: ${g.reason}`))
      );
    } else if (action === "search") {
      addResult(`${data.result_count || 0} search results`,
        `Searched ${data.files_considered || 0} files; inspected readable content in ${data.readable_files_inspected || 0}. ${data.message || ""}`,
        (data.results || []).map((r) => `${r.path} · ${r.match} · ${r.snippet}`)
      );
    } else if (action === "map") {
      const edges = (data.edges || []).map((e) => `${e.source} ↔ ${e.target} · ${e.label} · ${e.evidence.join("; ")}`);
      addResult(`${data.node_count || 0} nodes · ${data.edge_count || 0} relationship links`,
        "Folders and files are nodes. Links represent candidate relationships, not guaranteed semantic connections. " + data.message,
        edges.length ? edges : ["No relationships were detected in the selected folder."]
      );
    } else if (action === "health") {
      addResult(`${data.finding_count || 0} workspace review suggestions`,
        `${data.files_count || 0} files · ${data.total_bytes || 0} total bytes. ${data.message || ""}`,
        (data.findings || []).map((f) => `[${f.severity}] ${f.kind}: ${f.path || f.folder || f.pattern || ""} — ${f.reason} ${f.suggestion || ""}`)
      );
    }
  }
  async function run(action) {
    const button = section.querySelector(`[data-action="${action}"]`);
    if (button) button.disabled = true;
    setStatus("Analysing locally… No files will be changed.");
    try {
      const root = encodeURIComponent(currentRoot());
      let url = "";
      let options = {};
      if (action === "relationships") url = `/api/relationships?relative_path=${root}`;
      if (action === "duplicates") {
        url = "/api/duplicates/insights";
        options = {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({relative_path: currentRoot()})};
      }
      if (action === "map") url = `/api/knowledge-map?relative_path=${root}`;
      if (action === "health") url = `/api/health-report?relative_path=${root}`;
      if (action === "search") {
        const value = query.value.trim();
        if (!value) throw new Error("Enter a search phrase or keyword first.");
        url = `/api/search?query=${encodeURIComponent(value)}&relative_path=${root}`;
      }
      const response = await fetch(url, options);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Workspace analysis failed.");
      showData(action, data);
      setStatus((data.truncated ? "Analysis is bounded; results may be incomplete. " : "") + (data.message || "Analysis complete."));
    } catch (error) {
      output.replaceChildren();
      setStatus(error.message || "Workspace analysis failed.", true);
    } finally {
      if (button) button.disabled = false;
    }
  }
  actions.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-action]");
    if (button) run(button.dataset.action);
  });
  searchForm.addEventListener("submit", (event) => {
    event.preventDefault();
    run("search");
  });
})();
