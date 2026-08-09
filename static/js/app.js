(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);

  const filesTbody = $("files-tbody");
  const filesTable = $("files-table");
  const filesEmpty = $("files-empty");
  const btnOpen = $("btn-open");
  const btnDelete = $("btn-delete");
  const btnRefresh = $("btn-refresh");
  const filesStatus = $("files-status");

  let dataColumns = window.__DATA_COLUMNS__ || [];

  // ---------- helpers ----------

  function setStatus(el, msg, ok = true) {
    el.textContent = msg;
    el.className = "status " + (ok ? "status--ok" : "status--error");
  }

  async function postJSON(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });

    const contentType = res.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) {
      // Backend returned HTML (e.g. Flask debug traceback page or a 404/500
      // default error page) instead of JSON — surface something readable.
      const text = await res.text();
      console.error(`Non-JSON response from ${url} (status ${res.status}):`, text);
      throw new Error(`Erro ${res.status} no servidor (${url}). Veja o console/terminal do Flask.`);
    }

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro desconhecido");
    return data;
  }

  function selectedFiles() {
    return [...filesTbody.querySelectorAll(".file-check:checked")].map(
      (cb) => cb.closest("tr").dataset.file
    );
  }

  function refreshActionState() {
    const sel = selectedFiles();
    btnOpen.disabled = sel.length !== 1;
    btnDelete.disabled = sel.length === 0;
  }

  function renderFiles(files) {
    filesTbody.innerHTML = "";
    if (!files.length) {
      filesTable.hidden = true;
      filesEmpty.hidden = false;
      refreshActionState();
      return;
    }
    filesTable.hidden = false;
    filesEmpty.hidden = true;
    for (const f of files) {
      const tr = document.createElement("tr");
      tr.dataset.file = f.name;
      tr.innerHTML = `
        <td class="col-check"><input type="checkbox" class="file-check"></td>
        <td class="mono">${f.name}</td>
        <td class="col-num mono">${f.size_mb.toFixed(2)}</td>
        <td class="mono">${f.modified}</td>
      `;
      filesTbody.appendChild(tr);
    }
    refreshActionState();
  }

  async function loadFiles() {
    const data = await (await fetch("/api/files")).json();
    renderFiles(data.files);
  }

  // ---------- files table events ----------

  filesTbody.addEventListener("change", (e) => {
    if (e.target.classList.contains("file-check")) refreshActionState();
  });

  btnRefresh.addEventListener("click", () => loadFiles().catch((e) => setStatus(filesStatus, e.message, false)));

  btnOpen.addEventListener("click", async () => {
    const [file] = selectedFiles();
    try {
      const data = await postJSON("/api/files/open", { file });
      setStatus(filesStatus, `${file} carregado.`, true);
      onDataLoaded(data);
    } catch (e) {
      setStatus(filesStatus, e.message, false);
    }
  });

  btnDelete.addEventListener("click", () => {
    const sel = selectedFiles();
    if (!sel.length) return;
    showConfirm(
      `Confirma exclusão de: ${sel.join(", ")}?`,
      async () => {
        try {
          const data = await postJSON("/api/files/delete", { files: sel });
          renderFiles(data.files);
          setStatus(filesStatus, "Arquivo(s) excluído(s).", true);
        } catch (e) {
          setStatus(filesStatus, e.message, false);
        }
      }
    );
  });

  // ---------- confirm dialog ----------

  const overlay = $("confirm-overlay");
  const confirmText = $("confirm-text");
  const confirmYes = $("confirm-yes");
  const confirmNo = $("confirm-no");

  function showConfirm(text, onYes) {
    confirmText.textContent = text;
    overlay.hidden = false;
    const cleanup = () => {
      overlay.hidden = true;
      confirmYes.removeEventListener("click", yesHandler);
      confirmNo.removeEventListener("click", noHandler);
    };
    const yesHandler = () => { cleanup(); onYes(); };
    const noHandler = () => cleanup();
    confirmYes.addEventListener("click", yesHandler);
    confirmNo.addEventListener("click", noHandler);
  }

  // ---------- download ----------

  const downloadStatus = $("download-status");

  $("btn-download").addEventListener("click", async () => {
    const btn = $("btn-download");
    btn.disabled = true;
    setStatus(downloadStatus, "Baixando...", true);
    try {
      const data = await postJSON("/api/download", {
        uf: $("uf").value,
        year: $("year").value,
        month: $("month").value,
        system: $("system").value,
      });
      renderFiles(data.files);
      setStatus(downloadStatus, `Arquivo salvo em: ${data.path}`, true);
      onDataLoaded(data);
    } catch (e) {
      setStatus(downloadStatus, e.message, false);
    } finally {
      btn.disabled = false;
    }
  });

  // ---------- data / chart section ----------

  const dataSection = $("data-section");
  const dataSummary = $("data-summary");
  const chartType = $("chart-type");
  const chartColumn = $("chart-column");
  const chartX = $("chart-x");
  const chartY = $("chart-y");
  const chartColor = $("chart-color");
  const chartTopN = $("chart-topn");
  const topnValue = $("topn-value");
  const chartStatus = $("chart-status");

  const fieldColumn = $("field-column");
  const fieldX = $("field-x");
  const fieldY = $("field-y");
  const fieldColor = $("field-color");
  const fieldTopN = $("field-topn");

  function populateColumnSelects() {
    const opts = dataColumns.map((c) => `<option value="${c}">${c}</option>`).join("");
    chartColumn.innerHTML = opts;
    chartX.innerHTML = opts;
    chartY.innerHTML = opts;
    chartColor.innerHTML = `<option value="">(nenhum)</option>` + opts;
  }

  function syncFieldsForChartType() {
    const type = chartType.value;
    const isCategorical = type === "Barras" || type === "Pizza";
    const isHistogram = type === "Histograma";
    const isScatter = type === "Dispersão";

    fieldColumn.hidden = !(isCategorical || isHistogram);
    fieldX.hidden = !isScatter;
    fieldY.hidden = !isScatter;
    fieldColor.hidden = !isScatter;
    fieldTopN.hidden = !isCategorical;
  }

  chartType.addEventListener("change", () => {
    syncFieldsForChartType();
    renderChart();
  });
  chartColumn.addEventListener("change", renderChart);
  chartX.addEventListener("change", renderChart);
  chartY.addEventListener("change", renderChart);
  chartColor.addEventListener("change", renderChart);
  chartTopN.addEventListener("input", () => {
    topnValue.textContent = chartTopN.value;
  });
  chartTopN.addEventListener("change", renderChart);

  async function renderChart() {
    if (!dataColumns.length) return;
    const type = chartType.value;
    const payload = {
      chart_type: type,
      column: chartColumn.value,
      top_n: chartTopN.value,
      x: chartX.value,
      y: chartY.value,
      color: chartColor.value,
    };
    try {
      const data = await postJSON("/api/chart", payload);
      Plotly.newPlot("chart-container", data.figure.data, data.figure.layout, { responsive: true });
      setStatus(chartStatus, "", true);
    } catch (e) {
      setStatus(chartStatus, e.message, false);
    }
  }

  function updateQuickStats(stats) {
    if (!stats) return;
    $("stat-registros").textContent = stats.registros.display;
    $("stat-municipios").textContent = stats.municipios.display;
    $("stat-internacoes").textContent = stats.internacoes.display;
    $("stat-idade").textContent = stats.media_idade.display;
  }

  function onDataLoaded(data) {
    dataColumns = data.columns;
    dataSummary.textContent = `Registros: ${data.rows} | Colunas: ${data.cols}`;
    updateQuickStats(data.stats);
    dataSection.hidden = false;
    populateColumnSelects();
    syncFieldsForChartType();
    renderChart();
  }

  // ---------- init ----------

  if (dataColumns.length) {
    populateColumnSelects();
    syncFieldsForChartType();
    renderChart();
  }
})();