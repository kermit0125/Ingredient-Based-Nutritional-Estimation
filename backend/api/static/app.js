const state = {
  chartType: "pie",
  selectedFile: null,
  classes: [],
  result: null,
};

const MACROS = [
  { key: "carbs_g", label: "Carbs", color: "#B85042" },
  { key: "protein_g", label: "Protein", color: "#287271" },
  { key: "fat_g", label: "Fat", color: "#D9A441" },
];

const els = {
  uploadForm: document.getElementById("uploadForm"),
  imageInput: document.getElementById("imageInput"),
  dropzone: document.getElementById("dropzone"),
  analyzeBtn: document.getElementById("analyzeBtn"),
  resetBtn: document.getElementById("resetBtn"),
  feedback: document.getElementById("feedback"),
  healthBadge: document.getElementById("healthBadge"),
  classesSummary: document.getElementById("classesSummary"),
  previewImage: document.getElementById("previewImage"),
  previewEmpty: document.getElementById("previewEmpty"),
  resultImage: document.getElementById("resultImage"),
  resultEmpty: document.getElementById("resultEmpty"),
  totalCalories: document.getElementById("totalCalories"),
  totalCarbs: document.getElementById("totalCarbs"),
  totalProtein: document.getElementById("totalProtein"),
  totalFat: document.getElementById("totalFat"),
  macroChart: document.getElementById("macroChart"),
  chartLegend: document.getElementById("chartLegend"),
  resultsTableBody: document.getElementById("resultsTableBody"),
  chartButtons: Array.from(document.querySelectorAll(".chart-toggle-btn")),
};

function setFeedback(message, type = "info") {
  if (!message) {
    els.feedback.hidden = true;
    els.feedback.textContent = "";
    els.feedback.classList.remove("error");
    return;
  }
  els.feedback.hidden = false;
  els.feedback.textContent = message;
  els.feedback.classList.toggle("error", type === "error");
}

function formatNumber(value, digits = 1) {
  return Number(value || 0).toFixed(digits);
}

function titleize(value) {
  return String(value || "")
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function setImage(cardImage, emptyEl, src) {
  const card = cardImage.closest(".image-card");
  if (src) {
    cardImage.src = src;
    card.classList.add("has-image");
    return;
  }
  cardImage.removeAttribute("src");
  card.classList.remove("has-image");
  emptyEl.hidden = false;
}

function previewFile(file) {
  const reader = new FileReader();
  reader.onload = () => setImage(els.previewImage, els.previewEmpty, reader.result);
  reader.readAsDataURL(file);
}

function resetTotals() {
  els.totalCalories.textContent = "0";
  els.totalCarbs.textContent = "0";
  els.totalProtein.textContent = "0";
  els.totalFat.textContent = "0";
}

function resetTable() {
  els.resultsTableBody.innerHTML = `
    <tr class="empty-row">
      <td colspan="8">Run an image through the model to populate the table.</td>
    </tr>
  `;
}

function renderTable(ingredients) {
  if (!ingredients.length) {
    resetTable();
    return;
  }

  els.resultsTableBody.innerHTML = ingredients
    .map((item) => {
      return `
        <tr>
          <td>${titleize(item.class)}</td>
          <td class="mono">${formatNumber(item.confidence, 3)}</td>
          <td class="mono">${formatNumber(item.estimated_weight_g, 2)}</td>
          <td class="mono">${formatNumber(item.calories, 1)}</td>
          <td class="mono">${formatNumber(item.carbs_g, 2)}</td>
          <td class="mono">${formatNumber(item.protein_g, 2)}</td>
          <td class="mono">${formatNumber(item.fat_g, 2)}</td>
          <td class="mono">${formatNumber(item.mask_area_ratio, 4)}</td>
        </tr>
      `;
    })
    .join("");
}

function polarToCartesian(cx, cy, r, angleDeg) {
  const angle = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
}

function describeArc(cx, cy, r, startAngle, endAngle) {
  const start = polarToCartesian(cx, cy, r, endAngle);
  const end = polarToCartesian(cx, cy, r, startAngle);
  const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
  return `M ${cx} ${cy} L ${start.x} ${start.y} A ${r} ${r} 0 ${largeArcFlag} 0 ${end.x} ${end.y} Z`;
}

function renderLegend(parts) {
  els.chartLegend.innerHTML = parts
    .map(
      (part) => `
        <div class="legend-item">
          <span class="legend-swatch" style="background:${part.color}"></span>
          <span>${part.label}</span>
          <strong class="mono">${part.percent}%</strong>
        </div>
      `
    )
    .join("");
}

function renderPieChart(parts) {
  const cx = 110;
  const cy = 120;
  const r = 72;
  let currentAngle = 0;

  const slices = parts
    .map((part) => {
      const startAngle = currentAngle;
      const angle = (part.value / 100) * 360;
      currentAngle += angle;
      return `<path d="${describeArc(cx, cy, r, startAngle, currentAngle)}" fill="${part.color}"></path>`;
    })
    .join("");

  els.macroChart.innerHTML = `
    <rect x="0" y="0" width="320" height="240" rx="22" fill="rgba(255,255,255,0.18)"></rect>
    ${slices}
    <circle cx="${cx}" cy="${cy}" r="38" fill="#fff8ef"></circle>
    <text x="${cx}" y="116" text-anchor="middle" font-size="12" fill="#6A6359" font-family="IBM Plex Mono, monospace">Macro</text>
    <text x="${cx}" y="136" text-anchor="middle" font-size="18" fill="#1D1B18" font-weight="700" font-family="Space Grotesk, sans-serif">Ratio</text>
    <text x="224" y="78" font-size="12" fill="#6A6359" font-family="IBM Plex Mono, monospace">Detected</text>
    <text x="224" y="102" font-size="28" fill="#1D1B18" font-weight="700" font-family="Space Grotesk, sans-serif">${state.result.ingredients.length}</text>
    <text x="224" y="124" font-size="12" fill="#6A6359" font-family="IBM Plex Mono, monospace">items</text>
  `;
}

function renderBarChart(parts) {
  const maxValue = Math.max(...parts.map((part) => part.value), 1);
  const bars = parts
    .map((part, index) => {
      const barHeight = (part.value / maxValue) * 108;
      const x = 46 + index * 88;
      const y = 172 - barHeight;
      return `
        <rect x="${x}" y="${y}" width="42" height="${barHeight}" rx="16" fill="${part.color}"></rect>
        <text x="${x + 21}" y="190" text-anchor="middle" font-size="12" fill="#6A6359" font-family="IBM Plex Mono, monospace">${part.label}</text>
        <text x="${x + 21}" y="${y - 10}" text-anchor="middle" font-size="12" fill="#1D1B18" font-family="IBM Plex Mono, monospace">${part.percent}%</text>
      `;
    })
    .join("");

  els.macroChart.innerHTML = `
    <rect x="0" y="0" width="320" height="240" rx="22" fill="rgba(255,255,255,0.18)"></rect>
    <line x1="34" y1="172" x2="286" y2="172" stroke="rgba(29,27,24,0.2)" stroke-width="1.2"></line>
    ${bars}
  `;
}

function renderChart(totals) {
  const rawParts = MACROS.map((macro) => ({
    ...macro,
    grams: Number(totals?.[macro.key] || 0),
  }));

  const totalGrams = rawParts.reduce((sum, part) => sum + part.grams, 0);
  const parts =
    totalGrams > 0
      ? rawParts.map((part) => ({
          ...part,
          value: (part.grams / totalGrams) * 100,
          percent: ((part.grams / totalGrams) * 100).toFixed(1),
        }))
      : rawParts.map((part) => ({
          ...part,
          value: 100 / rawParts.length,
          percent: "0.0",
        }));

  renderLegend(parts);
  if (state.chartType === "bar") {
    renderBarChart(parts);
  } else {
    renderPieChart(parts);
  }
}

function renderResult(data) {
  state.result = data;
  const totals = data.totals || {};
  els.totalCalories.textContent = formatNumber(totals.calories, 1);
  els.totalCarbs.textContent = formatNumber(totals.carbs_g, 2);
  els.totalProtein.textContent = formatNumber(totals.protein_g, 2);
  els.totalFat.textContent = formatNumber(totals.fat_g, 2);
  renderTable(data.ingredients || []);
  renderChart(totals);

  const annotatedSrc = data.annotated_image_base64
    ? `data:image/jpeg;base64,${data.annotated_image_base64}`
    : "";
  setImage(els.resultImage, els.resultEmpty, annotatedSrc);

  if (data.message) {
    setFeedback(data.message, "info");
  } else {
    setFeedback(`Analysis complete. Detected ${data.ingredients.length} ingredient instance(s).`);
  }
}

function resetAll() {
  state.selectedFile = null;
  state.result = null;
  els.uploadForm.reset();
  setImage(els.previewImage, els.previewEmpty, "");
  setImage(els.resultImage, els.resultEmpty, "");
  resetTotals();
  resetTable();
  renderChart({});
  setFeedback("");
}

async function fetchClasses() {
  try {
    const [healthRes, classesRes] = await Promise.all([fetch("/health"), fetch("/classes")]);
    if (!healthRes.ok) {
      throw new Error("Health check failed");
    }
    const health = await healthRes.json();
    const classesData = classesRes.ok ? await classesRes.json() : { classes: [] };
    state.classes = classesData.classes || [];
    els.healthBadge.textContent = health.status === "ok" ? "API Ready" : "API Offline";
    els.classesSummary.textContent = state.classes.length
      ? `${state.classes.length} supported ingredient classes loaded`
      : "Class list unavailable";
  } catch (error) {
    els.healthBadge.textContent = "API Unavailable";
    els.classesSummary.textContent = "Check whether the FastAPI service is running correctly.";
  }
}

async function analyzeImage(event) {
  event.preventDefault();

  if (!state.selectedFile) {
    setFeedback("Select an ingredient image before running analysis.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("image", state.selectedFile);

  els.analyzeBtn.disabled = true;
  els.analyzeBtn.textContent = "Analyzing...";
  setFeedback("Uploading image to the backend and waiting for inference...");

  try {
    const response = await fetch("/predict", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || "Request failed");
    }
    renderResult(payload);
  } catch (error) {
    setFeedback(error.message || "Inference failed.", "error");
  } finally {
    els.analyzeBtn.disabled = false;
    els.analyzeBtn.textContent = "Analyze Image";
  }
}

function onFileSelected(file) {
  if (!file) {
    return;
  }
  state.selectedFile = file;
  previewFile(file);
  setFeedback(`Selected ${file.name}. Ready to send to /predict.`);
}

els.imageInput.addEventListener("change", (event) => {
  const [file] = event.target.files || [];
  onFileSelected(file);
});

["dragenter", "dragover"].forEach((eventName) => {
  els.dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    els.dropzone.classList.add("dragover");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  els.dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    els.dropzone.classList.remove("dragover");
  });
});

els.dropzone.addEventListener("drop", (event) => {
  const [file] = event.dataTransfer?.files || [];
  if (file) {
    els.imageInput.files = event.dataTransfer.files;
    onFileSelected(file);
  }
});

els.uploadForm.addEventListener("submit", analyzeImage);
els.resetBtn.addEventListener("click", resetAll);

els.chartButtons.forEach((button) => {
  button.addEventListener("click", () => {
    state.chartType = button.dataset.chart;
    els.chartButtons.forEach((candidate) => {
      candidate.classList.toggle("active", candidate === button);
    });
    renderChart(state.result?.totals || {});
  });
});

resetAll();
fetchClasses();
