const fileInput = document.getElementById("resumeFile");
const dropzone = document.getElementById("dropzone");
const dropTitle = document.getElementById("dropTitle");
const findBtn = document.getElementById("findBtn");
const btnText = document.getElementById("btnText");
const statusEl = document.getElementById("status");
const profileEl = document.getElementById("profile");
const resultsEl = document.getElementById("results");
const experienceInput = document.getElementById("experience");
const countryInput = document.getElementById("country");
const jobTitleInput = document.getElementById("jobTitle");

const LOADING_MESSAGES = [
  "Reading your resume...",
  "Finding your skills...",
  "Searching job boards...",
  "Ranking the best matches...",
  "Writing your AI analysis...",
];

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function tags(items, cssClass) {
  return (items || [])
    .map((item) => `<span class="tag ${cssClass}">${escapeHtml(item)}</span>`)
    .join("");
}

function bulletList(items) {
  return "<ul>" + (items || []).map((i) => `<li>${escapeHtml(i)}</li>`).join("") + "</ul>";
}

/* ---------- File selection (click or drag and drop) ---------- */
function showFileName() {
  const file = fileInput.files[0];
  if (file) {
    dropTitle.textContent = file.name;
    dropzone.classList.add("has-file");
  } else {
    dropTitle.textContent = "Drop your resume here or click to browse";
    dropzone.classList.remove("has-file");
  }
}

fileInput.addEventListener("change", showFileName);

["dragenter", "dragover"].forEach((name) =>
  dropzone.addEventListener(name, (event) => {
    event.preventDefault();
    dropzone.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((name) =>
  dropzone.addEventListener(name, (event) => {
    event.preventDefault();
    dropzone.classList.remove("dragover");
  })
);
dropzone.addEventListener("drop", (event) => {
  if (event.dataTransfer.files.length) {
    fileInput.files = event.dataTransfer.files;
    showFileName();
  }
});

/* ---------- Rendering ---------- */
function renderProfile(profile) {
  const skills = tags(profile.skills, "skill");
  profileEl.innerHTML = `
    <h2>Your profile</h2>
    <p class="email">${escapeHtml(profile.email || "No email found")}</p>
    <div class="section-title">Skills found in your resume</div>
    <div>${skills}</div>`;
  profileEl.classList.remove("hidden");
}

function renderAnalysis(analysis) {
  if (!analysis) {
    return `<p class="note">AI analysis is available for the top 5 matches.</p>`;
  }
  if (analysis.error) {
    return `<p class="note">${escapeHtml(analysis.error)}</p>`;
  }
  return `
    <details class="ai">
      <summary>AI analysis: why you fit, gaps and tips</summary>
      <div class="section-title">Why you fit</div>
      <p class="explain">${escapeHtml(analysis.why_fit)}</p>
      <div class="section-title">Skill gaps</div>
      <div>${tags(analysis.skill_gaps, "gap") || '<span class="note">No major gaps</span>'}</div>
      <div class="section-title">Resume tips</div>
      ${bulletList(analysis.resume_tips)}
    </details>`;
}

function renderJob(job, index) {
  const percent = Math.round(job.match_score * 100);
  const level = percent >= 60 ? "high" : percent >= 40 ? "mid" : "low";
  const expBadge =
    job.required_years !== null && job.required_years !== undefined
      ? `<span class="exp-badge">${job.required_years}+ yrs experience</span>`
      : "";

  return `
    <article class="job-card ${index === 0 ? "best" : ""}">
      ${index === 0 ? '<span class="best-label">Best match</span>' : ""}
      <div class="job-top">
        <div class="job-info">
          <h3>${escapeHtml(job.title)}</h3>
          <div class="meta">
            <span>${escapeHtml(job.company || "Company not listed")}</span>
            <span>${escapeHtml(job.location || "Location not listed")}</span>
            <span class="source">${escapeHtml(job.source)}</span>
            ${expBadge}
          </div>
        </div>
        <div>
          <div class="ring ${level}" style="--p:${percent}"><span>${percent}%</span></div>
          <div class="ring-label">match</div>
        </div>
      </div>

      <div class="section-title">Matched skills</div>
      <div>${tags(job.matched_skills, "match") || '<span class="note">No listed skills matched directly</span>'}</div>

      ${renderAnalysis(job.analysis)}

      <div class="actions">
        <a class="apply" href="${escapeHtml(job.url)}" target="_blank" rel="noopener noreferrer">Apply now</a>
      </div>
    </article>`;
}

function renderResults(data) {
  if (!data.top_jobs.length) {
    resultsEl.innerHTML = `<div class="empty">No jobs found. Try a different job title or country.</div>`;
    return;
  }
  resultsEl.innerHTML = `
    <div class="results-head">
      <h2>Your top matches</h2>
      <p>Searched for "${escapeHtml(data.search_query)}" &middot; ${data.total_jobs} jobs found</p>
    </div>
    ${data.top_jobs.map(renderJob).join("")}`;
}

/* ---------- Loading and status ---------- */
let loadingTimer = null;

function startLoading() {
  let step = 0;
  findBtn.disabled = true;
  findBtn.classList.add("loading");
  btnText.textContent = LOADING_MESSAGES[0];
  loadingTimer = setInterval(() => {
    step = Math.min(step + 1, LOADING_MESSAGES.length - 1);
    btnText.textContent = LOADING_MESSAGES[step];
  }, 5000);
}

function stopLoading() {
  clearInterval(loadingTimer);
  findBtn.disabled = false;
  findBtn.classList.remove("loading");
  btnText.textContent = "Find my jobs";
}

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.classList.toggle("error", isError);
}

/* ---------- Main action ---------- */
findBtn.addEventListener("click", async () => {
  const file = fileInput.files[0];
  if (!file) {
    setStatus("Please choose your resume first.", true);
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  formData.append("experience", experienceInput.value || 0);
  formData.append("country", countryInput.value);
  formData.append("job_title", jobTitleInput.value);

  setStatus("This can take up to 40 seconds.");
  profileEl.classList.add("hidden");
  resultsEl.innerHTML = "";
  startLoading();

  try {
    const response = await fetch("/match-jobs", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) {
      setStatus(data.detail || "Something went wrong.", true);
      return;
    }
    setStatus("");
    renderProfile(data.profile);
    renderResults(data);
    profileEl.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    setStatus("Could not reach the server. Is it running?", true);
  } finally {
    stopLoading();
  }
});
