const API = "http://localhost:8000/api";

const COLOR_HEX = {
  "Pastel Pink":      "#FFB5C8", "Baby Blue":        "#89CFF0",
  "Lavender":         "#E6E6FA", "Peach":            "#FFCBA4",
  "Mint Green":       "#98FF98", "Soft White":       "#FAF9F6",
  "Coral":            "#FF7F50", "Terracotta":       "#E2725B",
  "Teal":             "#008080", "Royal Blue":       "#4169E1",
  "Olive Green":      "#6B8E23", "Rust":             "#B7410E",
  "Warm Yellow":      "#FFD166", "Emerald Green":    "#50C878",
  "Navy Blue":        "#1B2A5E", "Burgundy":         "#800020",
  "Mustard":          "#FFDB58", "Magenta":          "#C2185B",
  "Deep Purple":      "#673AB7", "Maroon":           "#800000",
  "Gold":             "#FFD700", "Bright Orange":    "#FF5722",
  "Electric Blue":    "#00B0FF", "Hot Pink":         "#FF69B4",
  "Ivory":            "#FFFFF0", "Red":              "#E53935",
  "Bright Yellow":    "#FFEE58", "Neon Yellow":      "#FFFF00",
  "Ash Grey":         "#B2BEB5", "Pale Beige":       "#F5F5DC",
  "Muted Grey":       "#9E9E9E", "Pale Pastels":     "#E8EAF6",
  "Dark Navy":        "#1A237E", "Dark Brown":       "#3E2723",
  "Charcoal":         "#607D8B", "Washed-out Beige": "#E8E0D0",
};

const OCCASIONS = ["Casual", "College", "Office", "Wedding", "Party"];
let lastPayload = null;   // remembers the last submitted profile for occasion-switch

// ── Confidence badge ───────────────────────────────────────────────────────
function setConfBadge(id, val) {
  const el  = document.getElementById(id);
  const num = parseFloat(val);
  el.textContent = val;
  el.className   = "confidence-badge " + (num >= 90 ? "conf-high" : "conf-mid");
}

// ── BMI category class ──────────────────────────────────────────────────────
function getBmiClass(bmi) {
  if (bmi < 18.5) return "bmi-under";
  if (bmi < 25)   return "bmi-normal";
  if (bmi < 30)   return "bmi-over";
  return "bmi-obese";
}

// ── Body type guide modal ───────────────────────────────────────────────────
function openBodyGuide() {
  document.getElementById("bodyTypeModal").classList.remove("hidden");
}

function closeBodyGuide() {
  document.getElementById("bodyTypeModal").classList.add("hidden");
}

function selectBodyType(type) {
  document.getElementById("body_type").value = type;
  closeBodyGuide();
}

// Close modal when clicking outside the box
document.addEventListener("DOMContentLoaded", () => {
  const overlay = document.getElementById("bodyTypeModal");
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closeBodyGuide();
  });
});

// ── Main recommendation call ───────────────────────────────────────────────
async function getRecommendations() {
  const btn = document.getElementById("getStyleBtn");

  const ft     = parseInt(document.getElementById("height_ft").value || 0);
  const inches = parseInt(document.getElementById("height_in").value || 0);
  const totalInches = (ft * 12) + inches;

  const payload = {
    height_inches:   totalInches,
    weight_kg:       parseFloat(document.getElementById("weight").value),
    age:             parseInt(document.getElementById("age").value),
    body_type:       document.getElementById("body_type").value,
    skin_tone:       document.getElementById("skin_tone").value,
    face_shape:      document.getElementById("face_shape").value,
    occasion:        document.getElementById("occasion").value,
    preferred_style: document.getElementById("preferred_style").value,
    hair_length:     document.getElementById("hair_length").value,
    hair_texture:    document.getElementById("hair_texture").value,
  };

  // Validate
  const missing = [];
  if (!ft || isNaN(ft))                               missing.push("Height (feet)");
  if (!payload.weight_kg || isNaN(payload.weight_kg)) missing.push("Weight");
  if (!payload.age       || isNaN(payload.age))       missing.push("Age");
  if (!payload.body_type)    missing.push("Body type");
  if (!payload.skin_tone)    missing.push("Skin tone");
  if (!payload.face_shape)   missing.push("Face shape");

  if (missing.length > 0) {
    alert("Please fill in: " + missing.join(", "));
    return;
  }

  await fetchAndRender(payload, btn);
}

// ── Shared fetch + render (used by both main button and occasion switch) ───
async function fetchAndRender(payload, btn) {
  if (btn) {
    btn.disabled  = true;
    btn.innerHTML = '<span class="btn-icon">⟳</span> Analyzing...';
  }
  document.getElementById("results").classList.add("hidden");
  document.getElementById("divider").style.display = "none";
  document.getElementById("loading").classList.remove("hidden");

  try {
    const res = await fetch(`${API}/recommend`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || "Server error");
    }

    const data = await res.json();
    lastPayload = payload;
    renderResults(data);

  // NEW — matches your actual port
} catch (err) {
  alert("Error: " + err.message + "\n\nMake sure Flask is running on port 8000.");
} finally {
    if (btn) {
      btn.disabled  = false;
      btn.innerHTML = '<span class="btn-icon">✦</span> Get my style recommendations';
    }
    document.getElementById("loading").classList.add("hidden");
  }
}

// ── Occasion quick switch ───────────────────────────────────────────────────
function renderOccasionButtons(activeOccasion) {
  const container = document.getElementById("occasionBtns");
  container.innerHTML = "";

  OCCASIONS.forEach(occ => {
    const btn = document.createElement("button");
    btn.className   = "occ-btn" + (occ === activeOccasion ? " active" : "");
    btn.textContent  = occ;
    btn.onclick      = () => switchOccasion(occ);
    container.appendChild(btn);
  });
}

async function switchOccasion(newOccasion) {
  if (!lastPayload) return;
  const updated = { ...lastPayload, occasion: newOccasion };
  document.getElementById("occasion").value = newOccasion;
  await fetchAndRender(updated, null);
}

// ── Style match score ───────────────────────────────────────────────────────
function calcStyleScore(ml) {
  const scores = [
    ml.outfit.confidence, ml.color_palette.confidence,
    ml.hairstyle.confidence, ml.earrings.confidence, ml.necklace.confidence
  ].map(v => parseFloat(v));

  const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
  return Math.round(avg);
}

// ── Render all results ─────────────────────────────────────────────────────
function renderResults(data) {
  const ml    = data.ml_recommendations;
  const guide = data.styling_guide;
  const stats = data.user_stats;

  document.getElementById("divider").style.display = "block";

  // ── BMI bar ──────────────────────────────────────────────────────────────
  const bmiClass = getBmiClass(stats.bmi);
  document.getElementById("bmiBar").innerHTML = `
    <span style="font-size:22px;">⚖️</span>
    <div style="flex:1;">
      <span style="font-weight:600; color:#5C1632; font-size:15px;">BMI: ${stats.bmi}</span>
      <span class="bmi-category-pill ${bmiClass}" style="margin-left:10px;">
        ${stats.bmi_category}
      </span>
    </div>
    <span style="font-size:13px; color:#9D6070;">
      ${stats.height_inches}" · ${stats.weight_kg} kg
    </span>
  `;

  // ── Style score ──────────────────────────────────────────────────────────
  const score = calcStyleScore(ml);
  document.getElementById("styleScoreCard").innerHTML = `
    <span class="score-label">Style Match</span>
    <span class="score-number">${score}</span>
    <span class="score-max">out of 100</span>
  `;

  // ── Occasion switch buttons ─────────────────────────────────────────────
  renderOccasionButtons(document.getElementById("occasion").value);

  // ── Outfit ───────────────────────────────────────────────────────────────
  document.getElementById("outfitText").textContent = ml.outfit.recommendation;
  setConfBadge("outfitConf", ml.outfit.confidence);
  document.getElementById("outfitTip").textContent  = guide.outfit_tip || "";

  const wearTags = document.getElementById("wearTags");
  wearTags.innerHTML = "";
  (guide.what_to_wear || []).slice(0, 5).forEach(item => {
    const tag = document.createElement("span");
    tag.className   = "tag";
    tag.textContent = item;
    wearTags.appendChild(tag);
  });

  // ── Colors ───────────────────────────────────────────────────────────────
  renderSwatches("colorSwatches", guide.colors_to_wear,  false);
  renderSwatches("avoidSwatches", guide.colors_to_avoid, true);
  document.getElementById("colorTip").textContent = guide.color_tip || "";

  // ── Hairstyle ─────────────────────────────────────────────────────────────
  document.getElementById("hairstyleText").textContent = ml.hairstyle.recommendation;
  setConfBadge("hairstyleConf", ml.hairstyle.confidence);

  const bestDiv = document.getElementById("hairstyleBest");
  bestDiv.innerHTML = "";
  (guide.hairstyle_best || []).slice(0, 4).forEach(h => {
    const tag = document.createElement("span");
    tag.className   = "tag";
    tag.textContent = h;
    bestDiv.appendChild(tag);
  });

  const avoidHair = guide.hairstyle_avoid || [];
  document.getElementById("hairstyleAvoid").textContent =
    avoidHair.length > 0 ? "Avoid: " + avoidHair.join(", ") : "";
  document.getElementById("hairstyleTip").textContent = guide.hairstyle_tip || "";

  // ── Jewelry ───────────────────────────────────────────────────────────────
  const j = guide.jewelry;
  document.getElementById("jewelryList").innerHTML = `
    <div class="jewelry-item">
      <div class="ji-label">💫 Earrings</div>
      <div class="ji-value">${ml.earrings.recommendation}</div>
      <div class="ji-tip">${j.earrings}</div>
    </div>
    <div class="jewelry-item">
      <div class="ji-label">📿 Necklace</div>
      <div class="ji-value">${ml.necklace.recommendation}</div>
      <div class="ji-tip">${j.necklace}</div>
    </div>
    <div class="jewelry-item">
      <div class="ji-label">✨ Bangles</div>
      <div class="ji-value">${j.bangles}</div>
    </div>
    <div class="jewelry-item">
      <div class="ji-label">💍 Ring</div>
      <div class="ji-value">${j.ring}</div>
    </div>
  `;

  const accRow = document.getElementById("accessoriesList");
  accRow.innerHTML = "";
  (guide.accessories || []).forEach(item => {
    const tag = document.createElement("span");
    tag.className   = "tag";
    tag.textContent = "👜 " + item;
    accRow.appendChild(tag);
  });

  // ── Body type guide ───────────────────────────────────────────────────────
  document.getElementById("bodyGuide").innerHTML = `
    <div class="body-guide-section">
      <h4>✅ Recommended outfits</h4>
      <div class="tag-list">
        ${(guide.what_to_wear || []).map(w => `<span class="tag">${w}</span>`).join("")}
      </div>
    </div>
    <div class="body-guide-section">
      <h4>❌ What doesn't suit you</h4>
      <div class="tag-list avoid-tags">
        ${(guide.what_to_avoid || []).map(w => `<span class="tag">✗ ${w}</span>`).join("")}
      </div>
    </div>
  `;

  // ── Avoid list ────────────────────────────────────────────────────────────
  const avoidDiv = document.getElementById("avoidList");
  avoidDiv.innerHTML = "";
  (guide.what_to_avoid || []).forEach(item => {
    const tag = document.createElement("span");
    tag.className   = "tag";
    tag.textContent = "✗ " + item;
    avoidDiv.appendChild(tag);
  });

  // ── Build print report (for download) ───────────────────────────────────
  buildPrintReport(data);

  // Show results
  const resultsEl = document.getElementById("results");
  resultsEl.classList.remove("hidden");
  resultsEl.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ── Render color swatches ──────────────────────────────────────────────────
function renderSwatches(containerId, colors, isAvoid) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";
  if (!colors || colors.length === 0) return;

  colors.forEach(name => {
    const hex = COLOR_HEX[name] || "#cccccc";
    const div = document.createElement("div");
    div.className = "swatch" + (isAvoid ? " avoid" : "");
    div.innerHTML = `
      <div class="swatch-circle" style="background:${hex};"></div>
      <div class="swatch-tooltip">${name}</div>
      <span class="swatch-label">${name}</span>
    `;
    container.appendChild(div);
  });
}

// ── Download style report (print to PDF) ────────────────────────────────────
function buildPrintReport(data) {
  const ml    = data.ml_recommendations;
  const guide = data.styling_guide;
  const stats = data.user_stats;

  document.getElementById("printDate").textContent =
    "Generated on " + new Date().toLocaleDateString("en-IN", {
      year: "numeric", month: "long", day: "numeric"
    });

  document.getElementById("printContent").innerHTML = `
    <div class="print-row">
      <div class="print-item">
        <h4>BMI</h4>
        <p>${stats.bmi} — ${stats.bmi_category}</p>
        <small>${stats.height_inches}" · ${stats.weight_kg} kg</small>
      </div>
      <div class="print-item">
        <h4>Style Match Score</h4>
        <p>${calcStyleScore(ml)} / 100</p>
      </div>
    </div>

    <div class="print-row">
      <div class="print-item">
        <h4>👗 Outfit</h4>
        <p>${ml.outfit.recommendation}</p>
        <small>${ml.outfit.confidence} confidence</small>
      </div>
      <div class="print-item">
        <h4>🎨 Color Palette</h4>
        <p>${(guide.colors_to_wear || []).slice(0, 4).join(", ")}</p>
      </div>
    </div>

    <div class="print-row">
      <div class="print-item">
        <h4>💇 Hairstyle</h4>
        <p>${ml.hairstyle.recommendation}</p>
        <small>${ml.hairstyle.confidence} confidence</small>
      </div>
      <div class="print-item">
        <h4>💍 Jewelry</h4>
        <p>${ml.earrings.recommendation} · ${ml.necklace.recommendation}</p>
      </div>
    </div>

    <div class="print-row">
      <div class="print-item" style="flex:1 0 100%;">
        <h4>⚠️ What to avoid</h4>
        <p>${(guide.what_to_avoid || []).join(", ")}</p>
      </div>
    </div>
  `;
}

function downloadReport() {
  window.print();
}

// ── Photo upload ───────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const photoInput   = document.getElementById("photoInput");
  const uploadStatus = document.getElementById("uploadStatus");

  photoInput.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    uploadStatus.textContent = "⏳ Uploading...";
    const form = new FormData();
    form.append("photo", file);

    try {
      const res  = await fetch(`${API}/upload`, { method: "POST", body: form });
      const data = await res.json();

      if (data.detected) {
        const d = data.detected;
        if (d.face_shape && d.face_shape !== "Unknown") {
          document.getElementById("face_shape").value = d.face_shape;
        }
        if (d.skin_tone && d.skin_tone !== "Unknown") {
          document.getElementById("skin_tone").value = d.skin_tone;
        }
        uploadStatus.textContent =
          `✅ Detected — Face: ${d.face_shape} · Skin: ${d.skin_tone}`;
      } else {
        uploadStatus.textContent = "✅ Photo uploaded. Fill the form manually.";
      }
    } catch {
      uploadStatus.textContent = "📸 Photo saved. CV analysis coming soon.";
    }
  });
});

// ── Reset form ─────────────────────────────────────────────────────────────
function resetForm() {
  document.getElementById("results").classList.add("hidden");
  document.getElementById("divider").style.display = "none";
  document.getElementById("height_ft").value  = "";
  document.getElementById("height_in").value  = "";
  document.getElementById("weight").value     = "";
  document.getElementById("age").value        = "";
  document.getElementById("body_type").value  = "";
  document.getElementById("skin_tone").value  = "";
  document.getElementById("face_shape").value = "";
  document.getElementById("hair_texture").value = "Straight";
  document.getElementById("uploadStatus").textContent = "";
  lastPayload = null;
  window.scrollTo({ top: 0, behavior: "smooth" });
}