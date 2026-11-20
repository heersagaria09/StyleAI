const API = "/api";

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
let personImage = null;
let personImageUrl = null;
let photoWasUploaded = false;
let photoRecommendationsAvailable = false;

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
  if (photoWasUploaded) {
    if (photoRecommendationsAvailable) {
      document.getElementById("photoRecommendations").scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    } else {
      document.getElementById("uploadStatus").textContent =
        "No reliable face features were detected. Try a clear, front-facing photo with one person.";
    }
    return;
  }
  await getFullProfileRecommendations();
}

async function getFullProfileRecommendations() {
  const btn = document.getElementById("getStyleBtn");
  const profileBtn = document.getElementById("getFullProfileBtn");
  const submitButton = photoWasUploaded ? profileBtn : btn;

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
    save_to_mongodb: document.getElementById("saveToMongo").checked,
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

  await fetchAndRender(payload, submitButton);
}

// ── Shared fetch + render (used by both main button and occasion switch) ───
async function fetchAndRender(payload, btn) {
  const originalButtonHtml = btn ? btn.innerHTML : "";
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

    let data;
    try {
      data = await res.json();
    } catch {
      throw new Error("The server returned an invalid response.");
    }
    if (!res.ok) throw new Error(data.error || "Server error");
    lastPayload = payload;
    renderResults(data);

  } catch (err) {
    alert(`Error: ${err.message}\n\nOpen StyleAI at the Flask URL shown in the server terminal.`);
  } finally {
    if (btn) {
      btn.disabled  = false;
      btn.innerHTML = originalButtonHtml;
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

// ── Render all results ─────────────────────────────────────────────────────
function renderResults(data) {
  const recommendations = data.recommendations;
  const guide = data.styling_guide;
  const stats = data.user_stats;
  const saveStatus = document.getElementById("saveStatus");
  if (data.mongodb && data.mongodb.saved) {
    saveStatus.textContent = "✅ Profile and recommendations saved to MongoDB.";
  } else if (data.mongodb && data.mongodb.error) {
    saveStatus.textContent = `Recommendations were generated, but MongoDB could not save them: ${data.mongodb.error}`;
  } else {
    saveStatus.textContent = "";
  }

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
  const styleScoreCard = document.getElementById("styleScoreCard");
  styleScoreCard.innerHTML = `
    <span class="score-label">Style match</span>
    <div class="match-score">
      <span class="match-score-value" id="matchScoreValue">—</span>
      <span class="match-score-denominator">out of 100</span>
    </div>
    <span class="match-score-caption" id="matchScoreCaption">Rate the suggestions to see your score</span>
    <div class="match-feedback" role="group" aria-labelledby="matchFeedbackLabel">
      <span class="match-feedback-label" id="matchFeedbackLabel">How well do these suggestions fit your style?</span>
      <div class="match-rating-buttons" id="matchRatingButtons"></div>
      <div class="match-feedback-endpoints"><span>Not at all</span><span>Very well</span></div>
      <span class="match-feedback-status" id="matchFeedbackStatus" aria-live="polite">Not rated yet</span>
      <small class="match-feedback-note">This score reflects your feedback, not model accuracy.</small>
    </div>
  `;
  const ratingLabels = ["Not at all", "A little", "Somewhat", "Mostly", "Very well"];
  const ratingButtons = styleScoreCard.querySelector("#matchRatingButtons");
  ratingLabels.forEach((label, index) => {
    const rating = index + 1;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "match-rating-button";
    button.textContent = String(rating);
    button.setAttribute("aria-label", `${rating} out of 5: ${label}`);
    button.setAttribute("aria-pressed", "false");
    button.addEventListener("click", () => {
      ratingButtons.querySelectorAll(".match-rating-button").forEach((item) => {
        item.classList.remove("selected");
        item.setAttribute("aria-pressed", "false");
      });
      button.classList.add("selected");
      button.setAttribute("aria-pressed", "true");
      styleScoreCard.querySelector("#matchScoreValue").textContent = String(rating * 20);
      styleScoreCard.querySelector("#matchScoreCaption").textContent =
        `Based on your ${rating}/5 rating`;
      styleScoreCard.querySelector("#matchFeedbackStatus").textContent =
        `Your rating: ${rating}/5 — ${label}.`;
    });
    ratingButtons.appendChild(button);
  });

  // ── Occasion switch buttons ─────────────────────────────────────────────
  renderOccasionButtons(document.getElementById("occasion").value);

  // ── Outfit ───────────────────────────────────────────────────────────────
  document.getElementById("outfitText").textContent = recommendations.outfit.recommendation;
  setConfBadge("outfitConf", recommendations.outfit.basis);
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
  document.getElementById("hairstyleText").textContent = recommendations.hairstyle.recommendation;
  setConfBadge("hairstyleConf", recommendations.hairstyle.basis);

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
      <div class="ji-value">${recommendations.earrings.recommendation}</div>
      <div class="ji-tip">${j.earrings}</div>
    </div>
    <div class="jewelry-item">
      <div class="ji-label">📿 Necklace</div>
      <div class="ji-value">${recommendations.necklace.recommendation}</div>
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
  const recommendations = data.recommendations;
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
        <h4>About these suggestions</h4>
        <p>Experimental recommendations; accuracy has not been measured.</p>
      </div>
    </div>

    <div class="print-row">
      <div class="print-item">
        <h4>👗 Outfit</h4>
        <p>${recommendations.outfit.recommendation}</p>
        <small>${recommendations.outfit.basis} recommendation</small>
      </div>
      <div class="print-item">
        <h4>🎨 Color Palette</h4>
        <p>${(guide.colors_to_wear || []).slice(0, 4).join(", ")}</p>
      </div>
    </div>

    <div class="print-row">
      <div class="print-item">
        <h4>💇 Hairstyle</h4>
        <p>${recommendations.hairstyle.recommendation}</p>
        <small>${recommendations.hairstyle.basis} recommendation</small>
      </div>
      <div class="print-item">
        <h4>💍 Jewelry</h4>
        <p>${recommendations.earrings.recommendation} · ${recommendations.necklace.recommendation}</p>
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
  photoInput.addEventListener("change", (event) => processPhotoFile(event.target.files[0]));
  document.getElementById("startCameraBtn").addEventListener("click", startCamera);
  document.getElementById("capturePhotoBtn").addEventListener("click", captureCameraPhoto);
  document.getElementById("stopCameraBtn").addEventListener("click", stopCamera);
  window.addEventListener("pagehide", stopCamera);
});

let cameraStream = null;

async function startCamera() {
  const status = document.getElementById("cameraStatus");
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    status.textContent = "Camera access requires localhost or HTTPS. You can upload a photo instead.";
    return;
  }

  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "user" } },
      audio: false,
    });
    const video = document.getElementById("cameraPreview");
    video.srcObject = cameraStream;
    await video.play();
    video.classList.remove("hidden");
    document.getElementById("capturePhotoBtn").disabled = false;
    document.getElementById("startCameraBtn").disabled = true;
    document.getElementById("stopCameraBtn").classList.remove("hidden");
    status.textContent = "Camera ready. Center your face and capture a photo.";
  } catch (error) {
    stopCamera();
    status.textContent = error.name === "NotAllowedError" || error.name === "SecurityError"
      ? "Camera permission was denied or blocked. Allow access in your browser, or upload a photo."
      : error.name === "NotFoundError"
        ? "No camera was found. Connect a camera or upload a photo."
        : `Could not access the camera: ${error.message}`;
  }
}

function stopCamera() {
  if (cameraStream) {
    cameraStream.getTracks().forEach((track) => track.stop());
    cameraStream = null;
  }
  const video = document.getElementById("cameraPreview");
  if (video) video.srcObject = null;
  if (video) video.classList.add("hidden");
  const captureButton = document.getElementById("capturePhotoBtn");
  if (captureButton) captureButton.disabled = true;
  const startButton = document.getElementById("startCameraBtn");
  if (startButton) startButton.disabled = false;
  const stopButton = document.getElementById("stopCameraBtn");
  if (stopButton) stopButton.classList.add("hidden");
}

async function captureCameraPhoto() {
  const video = document.getElementById("cameraPreview");
  if (!cameraStream || !video.videoWidth || !video.videoHeight) {
    document.getElementById("cameraStatus").textContent =
      "The camera is not ready yet. Wait for the preview or upload a photo.";
    return;
  }

  const canvas = document.createElement("canvas");
  const scale = Math.min(1, 1024 / Math.max(video.videoWidth, video.videoHeight));
  canvas.width = Math.round(video.videoWidth * scale);
  canvas.height = Math.round(video.videoHeight * scale);
  const context = canvas.getContext("2d");
  if (!context) {
    document.getElementById("cameraStatus").textContent =
      "Could not capture from the camera. You can upload a photo instead.";
    return;
  }
  context.drawImage(video, 0, 0, canvas.width, canvas.height);

  try {
    const blob = await new Promise((resolve, reject) => {
      canvas.toBlob((result) => {
        if (result) resolve(result);
        else reject(new Error("The camera image could not be encoded."));
      }, "image/jpeg", 0.92);
    });
    const file = new File([blob], "camera-capture.jpg", { type: "image/jpeg" });
    stopCamera();
    document.getElementById("cameraStatus").textContent = "Captured. Analyzing your photo…";
    await processPhotoFile(file);
  } catch (error) {
    document.getElementById("cameraStatus").textContent = error.message;
  }
}

async function processPhotoFile(file) {
  const uploadStatus = document.getElementById("uploadStatus");
  if (!file) return;
  document.getElementById("photoRecommendations").classList.add("hidden");
  document.getElementById("photoRecommendationsContent").replaceChildren();
  setPhotoRecommendationMode(false, false);
  if (!isSupportedLocalImage(file)) {
    uploadStatus.textContent = "Choose a JPG, PNG, or WEBP image smaller than 10 MB.";
    return;
  }

  if (personImageUrl) URL.revokeObjectURL(personImageUrl);
  personImage = null;
  personImageUrl = null;
  document.getElementById("analysisPreview").classList.add("hidden");
  uploadStatus.textContent = "Loading photo…";

  try {
    const loaded = await loadLocalImage(file);
    personImage = loaded.image;
    personImageUrl = loaded.url;
    drawAnalysisPreview([]);
  } catch {
    uploadStatus.textContent = "Could not preview this image. You can still select the categories manually.";
    return;
  }

  uploadStatus.textContent = "Uploading and analyzing…";
  const form = new FormData();
  form.append("photo", file);

  try {
    const res = await fetch(`${API}/upload`, { method: "POST", body: form });
    const responseText = await res.text();
    let data;
    try {
      data = JSON.parse(responseText);
    } catch {
      const serverHint = res.status >= 500
        ? " Check the Flask terminal and restart with the project virtual environment."
        : "";
      throw new Error(`Photo analysis returned an invalid response (HTTP ${res.status}).${serverHint}`);
    }
    if (!res.ok) throw new Error(data.error || "Image upload failed.");

    if (data.detected) {
      const d = data.detected;
      const detectedItems = [];
      if (d.face_shape && d.face_shape !== "Unknown") {
        document.getElementById("face_shape").value = d.face_shape;
        detectedItems.push(`estimated face shape: ${d.face_shape}`);
      }
      if (d.skin_tone && d.skin_tone !== "Unknown") {
        document.getElementById("skin_tone").value = d.skin_tone;
        detectedItems.push(`skin tone: ${d.skin_tone}`);
      }
      if (data.face_landmarks && data.face_landmarks.length) {
        drawAnalysisPreview(data.face_landmarks);
      }
      uploadStatus.textContent = detectedItems.length
        ? `Photo analyzed — ${detectedItems.join(" · ")}. ${data.analysis_note || ""}`
        : `Photo uploaded. ${data.analysis_note || "Continue with manual category selection."}`;
    } else {
      uploadStatus.textContent = "✅ Photo uploaded. Categories are available for manual selection.";
    }
    renderPhotoRecommendations(data.photo_recommendations);
    setPhotoRecommendationMode(true, Boolean(data.photo_recommendations && data.photo_recommendations.available));
  } catch (error) {
    uploadStatus.textContent = `${error.message} You can still use the local preview and choose categories manually.`;
  }
}

function isSupportedLocalImage(file) {
  return ["image/jpeg", "image/png", "image/webp"].includes(file.type)
    && file.size > 0
    && file.size <= 10 * 1024 * 1024;
}

function loadLocalImage(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      if (image.naturalWidth * image.naturalHeight > 25_000_000) {
        URL.revokeObjectURL(url);
        reject(new Error("Image dimensions exceed the preview limit."));
        return;
      }
      resolve({ image, url });
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Image could not be decoded."));
    };
    image.src = url;
  });
}

function canvasSizeFor(image) {
  const scale = Math.min(1, 1024 / Math.max(image.naturalWidth, image.naturalHeight));
  return {
    width: Math.max(1, Math.round(image.naturalWidth * scale)),
    height: Math.max(1, Math.round(image.naturalHeight * scale)),
  };
}

function drawAnalysisPreview(landmarks) {
  if (!personImage) return;
  const preview = document.getElementById("analysisPreview");
  const note = document.getElementById("analysisPreviewNote");
  const canvas = document.getElementById("analysisCanvas");
  const size = canvasSizeFor(personImage);
  canvas.width = size.width;
  canvas.height = size.height;
  const context = canvas.getContext("2d");
  context.drawImage(personImage, 0, 0, size.width, size.height);

  if (landmarks.length > 2) {
    note.textContent =
      "Face outline landmarks are shown for an approximate estimate. Verify or change the face-shape selection above.";
    context.beginPath();
    landmarks.forEach((point, index) => {
      const x = point.x * size.width;
      const y = point.y * size.height;
      if (index === 0) context.moveTo(x, y);
      else context.lineTo(x, y);
    });
    context.closePath();
    context.strokeStyle = "#ffcc55";
    context.lineWidth = Math.max(2, size.width / 300);
    context.stroke();
  } else {
    note.textContent =
      "No face landmarks were detected. Continue with manual face-shape selection.";
  }
  preview.classList.remove("hidden");
}

function renderPhotoRecommendations(data) {
  const panel = document.getElementById("photoRecommendations");
  const note = document.getElementById("photoRecommendationsNote");
  const content = document.getElementById("photoRecommendationsContent");
  content.replaceChildren();
  if (!data) return;

  note.textContent = data.note;
  for (const [style, colors] of Object.entries(data.color_palettes || {})) {
    const palette = document.createElement("section");
    palette.className = "photo-palette-group";
    const title = document.createElement("h4");
    title.textContent = `${style} palette`;
    const swatches = document.createElement("div");
    swatches.className = "swatches";

    colors.forEach((name) => {
      const swatch = document.createElement("div");
      swatch.className = "swatch";
      const circle = document.createElement("div");
      circle.className = "swatch-circle";
      circle.style.background = COLOR_HEX[name] || "#cccccc";
      const label = document.createElement("span");
      label.className = "swatch-label";
      label.textContent = name;
      swatch.append(circle, label);
      swatches.appendChild(swatch);
    });

    palette.append(title, swatches);
    content.appendChild(palette);
  }

  if (data.colors_to_avoid && data.colors_to_avoid.length) {
    const avoid = document.createElement("p");
    avoid.className = "photo-recommendation-detail";
    avoid.textContent = `Colors to avoid: ${data.colors_to_avoid.join(", ")}`;
    content.appendChild(avoid);
  }

  if (data.hairstyle || data.jewelry) {
    const faceSuggestions = document.createElement("section");
    faceSuggestions.className = "photo-face-suggestions";
    const title = document.createElement("h4");
    title.textContent = "Face-shape suggestions";
    faceSuggestions.appendChild(title);

    if (data.hairstyle) {
      const hairstyle = document.createElement("p");
      hairstyle.className = "photo-recommendation-detail";
      hairstyle.textContent = `Hairstyle: ${data.hairstyle.recommendation}`;
      faceSuggestions.appendChild(hairstyle);
    }
    if (data.jewelry) {
      const jewelry = document.createElement("p");
      jewelry.className = "photo-recommendation-detail";
      jewelry.textContent =
        `Accessories: ${data.jewelry.earrings}; ${data.jewelry.necklace}.`;
      faceSuggestions.appendChild(jewelry);
    }
    content.appendChild(faceSuggestions);
  }

  panel.classList.remove("hidden");
}

function setPhotoRecommendationMode(uploaded, available) {
  photoWasUploaded = uploaded;
  photoRecommendationsAvailable = available;
  const photoButton = document.getElementById("getStyleBtn");
  const profileButton = document.getElementById("getFullProfileBtn");

  if (!uploaded) {
    photoButton.innerHTML = '<span class="btn-icon">✦</span> Get my style recommendations';
    profileButton.classList.add("hidden");
    return;
  }

  photoButton.innerHTML = available
    ? '<span class="btn-icon">✦</span> View photo-only suggestions'
    : '<span class="btn-icon">✦</span> Photo suggestions unavailable';
  profileButton.classList.remove("hidden");
}

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
  document.getElementById("saveToMongo").checked = false;
  document.getElementById("saveStatus").textContent = "";
  document.getElementById("photoInput").value = "";
  stopCamera();
  document.getElementById("cameraStatus").textContent = "";
  document.getElementById("analysisPreview").classList.add("hidden");
  document.getElementById("photoRecommendations").classList.add("hidden");
  document.getElementById("photoRecommendationsContent").replaceChildren();
  setPhotoRecommendationMode(false, false);
  if (personImageUrl) URL.revokeObjectURL(personImageUrl);
  personImage = null;
  personImageUrl = null;
  lastPayload = null;
  window.scrollTo({ top: 0, behavior: "smooth" });
}