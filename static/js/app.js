let CURRENT_SHORTS = [];

function selectVideo(path) {
  document.getElementById("videoPathInput").value = path;
}

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.innerText = message;
  toast.classList.remove("hidden");
  setTimeout(() => {
    toast.classList.add("hidden");
  }, 2500);
}

function copyText(text, successMsg = "Copied!") {
  if (!text) return;
  navigator.clipboard.writeText(text).then(() => {
    showToast(successMsg);
  }).catch(() => {
    // Fallback for older browsers
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
    showToast(successMsg);
  });
}

document.getElementById("scanBtn").addEventListener("click", async () => {
  const videoPath = document.getElementById("videoPathInput").value.trim();
  const apiKey = document.getElementById("apiKeyInput").value.trim();
  const scanBtn = document.getElementById("scanBtn");
  
  if (!videoPath) {
    alert("Please enter or select a video path first!");
    return;
  }
  
  scanBtn.disabled = true;
  scanBtn.innerText = "⏳ Scanning Video...";
  
  try {
    const res = await fetch("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        video_path: videoPath,
        api_key: apiKey,
        target_duration: document.getElementById("durationSelect") ? document.getElementById("durationSelect").value : 30.0,
        hook_duration: document.getElementById("hookDurationSelect") ? document.getElementById("hookDurationSelect").value : 3.5
      })
    });
    
    const data = await res.json();
    if (data.success && data.manifest) {
      displayEstimation(data.manifest);
    } else {
      alert("Scan failed: " + (data.error || "Unknown error"));
    }
  } catch (err) {
    alert("Request error: " + err.message);
  } finally {
    scanBtn.disabled = false;
    scanBtn.innerText = "🔍 Scan & Estimate Shorts";
  }
});

function displayEstimation(manifest) {
  const section = document.getElementById("estimationSection");
  section.classList.remove("hidden");
  
  CURRENT_SHORTS = manifest.shorts || [];
  
  document.getElementById("statTotalShorts").innerText = manifest.total_shorts_possible;
  document.getElementById("statHighViral").innerText = manifest.high_virality_count;
  document.getElementById("statMediumViral").innerText = manifest.medium_virality_count;
  
  const durSec = manifest.video_info.duration || 0;
  const mins = Math.floor(durSec / 60);
  const secs = Math.floor(durSec % 60);
  document.getElementById("statDuration").innerText = `${mins}m ${secs}s`;
  
  const container = document.getElementById("candidatesList");
  container.innerHTML = "";
  
  CURRENT_SHORTS.forEach((short) => {
    const card = document.createElement("div");
    card.className = "candidate-card";
    
    const isHigh = short.viral_score >= 80;
    const scoreClass = isHigh ? "score-high" : "score-medium";
    
    card.innerHTML = `
      <div class="score-circle ${scoreClass}">
        <span class="score-val">${short.viral_score}%</span>
        <span class="score-lbl">Viral</span>
      </div>
      <div class="candidate-info">
        <h3>Short #${short.short_id}: ${short.highlight_title}</h3>
        <div class="meta-tags">
          <span>⏱️ ${short.start}s - ${short.end}s (${short.duration}s)</span>
          <span>${short.badge}</span>
        </div>
        <div>
          <span class="hook-preview">🎣 Hook: ${short.hook_text}</span>
        </div>
        <p style="font-size: 13px; color: #8b949e; margin-top: 6px;">
          <strong>Suggested Title:</strong> ${short.titles ? short.titles[0] : 'N/A'}
        </p>
      </div>
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <button class="btn btn-sm btn-primary" onclick="renderSingleShort(${short.short_id})">⚡ Render Short</button>
        <button class="btn btn-sm btn-opencut" onclick="exportToOpenCut(${short.short_id})">✂️ OpenCut Project</button>
      </div>
    `;
    container.appendChild(card);
  });
  
  section.scrollIntoView({ behavior: "smooth" });
}

async function renderShortsBatch(selectedIds = null) {
  const statusEl = document.getElementById("renderStatus");
  const renderAllBtn = document.getElementById("renderAllBtn");
  const renderTopBtn = document.getElementById("renderTopBtn");
  const layoutMode = document.getElementById("layoutModeSelect").value;
  
  renderAllBtn.disabled = true;
  renderTopBtn.disabled = true;
  statusEl.innerText = "⏳ Rendering 9:16 Shorts with FFmpeg GPU (NVENC)...";
  
  try {
    const res = await fetch("/api/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        selected_ids: selectedIds,
        layout_mode: layoutMode
      })
    });
    
    const data = await res.json();
    if (data.success) {
      statusEl.innerText = "🎉 All shorts rendered successfully!";
      showToast("Rendering complete! Refreshing library...");
      setTimeout(() => {
        window.location.reload();
      }, 1500);
    } else {
      statusEl.innerText = "❌ Render error: " + (data.error || "Failed");
      alert("Error: " + data.error);
    }
  } catch (err) {
    statusEl.innerText = "❌ Request error: " + err.message;
  } finally {
    renderAllBtn.disabled = false;
    renderTopBtn.disabled = false;
  }
}

document.getElementById("renderAllBtn").addEventListener("click", () => {
  renderShortsBatch(null);
});

document.getElementById("renderTopBtn").addEventListener("click", () => {
  if (CURRENT_SHORTS.length === 0) return;
  const top3Ids = CURRENT_SHORTS.slice(0, 3).map(s => s.short_id);
  renderShortsBatch(top3Ids);
});

function renderSingleShort(shortId) {
  renderShortsBatch([shortId]);
}

async function exportToOpenCut(shortId) {
  showToast("⏳ Preparing OpenCut CapCut-compatible project...");
  try {
    const res = await fetch("/api/opencut/export_candidate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ short_id: shortId })
    });
    const data = await res.json();
    if (data.success && data.download_url) {
      showToast("🎉 OpenCut Project Ready! Downloading...");
      window.location.href = data.download_url;
    } else {
      alert("OpenCut export error: " + (data.error || "Failed"));
    }
  } catch (err) {
    alert("Request error: " + err.message);
  }
}

async function cleanOldShorts(deleteAll = false) {
  const currentVideo = document.getElementById("videoPathInput") ? document.getElementById("videoPathInput").value.trim() : "";
  const confirmMsg = deleteAll 
    ? "Are you sure you want to delete ALL rendered shorts from storage?" 
    : "Kya aap purani long videos ke saare shorts delete karke disk memory clean karna chahte hain?";
  
  if (!confirm(confirmMsg)) return;
  
  showToast("⏳ Cleaning old video shorts and cache...");
  try {
    const res = await fetch("/api/cleanup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        current_video: currentVideo,
        delete_all: deleteAll
      })
    });
    const data = await res.json();
    if (data.success) {
      const freed = data.cleanup.freed_mb || 0;
      const count = data.cleanup.deleted_count || 0;
      showToast(`🧹 Cleaned ${count} old folder(s)! Freed ${freed} MB disk space.`);
      setTimeout(() => {
        window.location.reload();
      }, 1200);
    } else {
      alert("Cleanup error: " + (data.error || "Failed"));
    }
  } catch (err) {
    alert("Request error: " + err.message);
  }
}
