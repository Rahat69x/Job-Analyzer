// Job Analyzer — Global Job Discovery & Remote Job Platform Controller

let currentTaxonomy = { categories: [], industries: [] };
let selectedCategoryId = 8; // Default: IT/Telecommunication
let currentTab = "Functional";
let loadedJobs = [];

// Debounce utility for real-time search
function debounce(fn, delay = 400) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}
const debouncedLoadJobs = debounce(() => loadJobs(), 400);

document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  setupBookmarkletLink();
  loadTaxonomy();
  loadTrackedJobsCount();
  loadAlertsCount();
  loadJobs(); // Initial catalog load
});

function initEventListeners() {
  // Navigation Tabs (7 views)
  const navTabs = [
    { id: "nav-tab-explorer", view: "view-explorer", onOpen: null },
    { id: "nav-tab-remote", view: "view-remote", onOpen: loadRemoteJobsView },
    { id: "nav-tab-country", view: "view-country", onOpen: loadCountryExplorerView },
    { id: "nav-tab-recommended", view: "view-recommended", onOpen: loadRecommendedJobsView },
    { id: "nav-tab-tracker", view: "view-tracker", onOpen: loadTrackedJobsView },
    { id: "nav-tab-alerts", view: "view-alerts", onOpen: loadAlertsView },
    { id: "nav-tab-analytics", view: "view-analytics", onOpen: loadMarketAnalytics }
  ];

  navTabs.forEach(tab => {
    const btn = document.getElementById(tab.id);
    if (!btn) return;
    btn.addEventListener("click", () => {
      navTabs.forEach(t => {
        const el = document.getElementById(t.id);
        const v = document.getElementById(t.view);
        if (el) el.classList.toggle("active", t.id === tab.id);
        if (v) v.classList.toggle("active", t.id === tab.id);
      });
      if (tab.onOpen) tab.onOpen();
    });
  });

  // Global Hero Search
  document.getElementById("btn-global-search").addEventListener("click", () => {
    switchView("nav-tab-explorer", "view-explorer");
    loadJobs();
  });
  document.getElementById("global-search-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      switchView("nav-tab-explorer", "view-explorer");
      loadJobs();
    }
  });

  // Quick Trending Filter Chips
  document.querySelectorAll(".quick-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const q = chip.getAttribute("data-query");
      document.getElementById("global-search-input").value = q;
      switchView("nav-tab-explorer", "view-explorer");
      loadJobs();
    });
  });

  // Experience Slider
  const expSlider = document.getElementById("input-experience");
  const expLabel = document.getElementById("label-experience");
  const updateSliderFill = (val) => {
    const min = parseFloat(expSlider.min) || 0;
    const max = parseFloat(expSlider.max) || 15;
    const pct = ((val - min) / (max - min)) * 100;
    expSlider.style.background = `linear-gradient(to right, #6366f1 0%, #6366f1 ${pct}%, #e2e8f0 ${pct}%, #e2e8f0 100%)`;
  };
  updateSliderFill(expSlider.value);
  expSlider.addEventListener("input", (e) => {
    expLabel.textContent = `${e.target.value}y`;
    updateSliderFill(e.target.value);
  });
  expSlider.addEventListener("change", () => loadJobs());

  // Smart Job Role & Skills Autocomplete
  const skillsInput = document.getElementById("input-skills");
  if (window.SmartJobRoleAutocomplete && skillsInput) {
    const initialTags = skillsInput.value ? skillsInput.value.split(',').map(s => s.trim()).filter(Boolean) : [];
    window.skillAutocomplete = new SmartJobRoleAutocomplete({
      input: skillsInput,
      initialTags: initialTags,
      onTagsChange: (tags) => {
        loadJobs();
      }
    });
  } else if (skillsInput) {
    skillsInput.addEventListener("change", () => loadJobs());
  }

  // Candidate Origin selector
  const originSelect = document.getElementById("candidate-origin");
  if (originSelect) {
    originSelect.addEventListener("change", () => loadJobs());
  }

  // Country & Workplace filter dropdowns — real-time
  const countryFilter = document.getElementById("filter-country");
  if (countryFilter) countryFilter.addEventListener("change", () => loadJobs());
  const workplaceFilter = document.getElementById("filter-workplace");
  if (workplaceFilter) workplaceFilter.addEventListener("change", () => loadJobs());

  // Global search input — debounced real-time as user types
  const globalInput = document.getElementById("global-search-input");
  if (globalInput) globalInput.addEventListener("input", debouncedLoadJobs);

  // Filter Checkboxes
  ["check-partners", "filter-visa-only", "filter-intl-only", "filter-eligible-only"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("change", () => loadJobs());
  });

  // Category Tabs (Functional vs Special vs Global)
  document.getElementById("tab-functional").addEventListener("click", () => switchTab("Functional"));
  document.getElementById("tab-special").addEventListener("click", () => switchTab("Special Skilled"));
  const tabGlobal = document.getElementById("tab-global-sources");
  if (tabGlobal) {
    tabGlobal.addEventListener("click", () => switchTab("Global"));
  }

  // Category Search
  document.getElementById("category-search").addEventListener("input", (e) => {
    renderCategoryChips(e.target.value);
  });

  // Refresh Button
  document.getElementById("btn-refresh").addEventListener("click", () => loadJobs(true));

  // Export CSV
  document.getElementById("btn-export-csv").addEventListener("click", exportToCSV);

  // LinkedIn Modal
  const modal = document.getElementById("linkedin-modal");
  document.getElementById("btn-import-linkedin").addEventListener("click", () => {
    modal.classList.add("show");
  });
  document.getElementById("btn-close-modal").addEventListener("click", () => {
    modal.classList.remove("show");
  });
  document.getElementById("btn-cancel-paste").addEventListener("click", () => {
    modal.classList.remove("show");
  });
  document.getElementById("btn-submit-paste").addEventListener("click", handleLinkedInSubmit);

  // Bookmarklet Modal
  const bModal = document.getElementById("bookmarklet-modal");
  document.getElementById("btn-show-bookmarklet").addEventListener("click", () => {
    bModal.classList.add("show");
  });
  document.getElementById("btn-close-bookmarklet").addEventListener("click", () => {
    bModal.classList.remove("show");
  });

  // Track Modal
  const tModal = document.getElementById("track-modal");
  document.getElementById("btn-close-track-modal").addEventListener("click", () => tModal.classList.remove("show"));
  document.getElementById("btn-cancel-track").addEventListener("click", () => tModal.classList.remove("show"));
  document.getElementById("btn-save-track").addEventListener("click", handleSaveTrackStage);

  // Remote Regions Bar
  document.querySelectorAll(".region-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      document.querySelectorAll(".region-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      loadRemoteJobsView(btn.getAttribute("data-region"));
    });
  });

  // Create Alert
  const btnCreateAlert = document.getElementById("btn-create-alert");
  if (btnCreateAlert) {
    btnCreateAlert.addEventListener("click", handleCreateAlert);
  }
}

function switchView(tabId, viewId) {
  const tabs = ["nav-tab-explorer", "nav-tab-remote", "nav-tab-country", "nav-tab-recommended", "nav-tab-tracker", "nav-tab-alerts", "nav-tab-analytics"];
  const views = ["view-explorer", "view-remote", "view-country", "view-recommended", "view-tracker", "view-alerts", "view-analytics"];
  
  tabs.forEach(t => {
    const el = document.getElementById(t);
    if (el) el.classList.toggle("active", t === tabId);
  });
  views.forEach(v => {
    const el = document.getElementById(v);
    if (el) el.classList.toggle("active", v === viewId);
  });
}

// ==================== GLOBAL JOB SEARCH & EXPLORER ====================

async function loadJobs(refreshLive = false) {
  const tbody = document.getElementById("jobs-table-body");
  tbody.innerHTML = `<tr><td colspan="8" class="loading-container"><div class="loader-spinner"></div><p style="margin-top: 10px;">Aggregating and ranking opportunities across global & Bangladesh sources...</p></td></tr>`;

  const query = document.getElementById("global-search-input").value.trim();
  const country = document.getElementById("filter-country").value;
  const workplace = document.getElementById("filter-workplace").value;
  const candidateOrigin = document.getElementById("candidate-origin") ? document.getElementById("candidate-origin").value : "Bangladesh";
  const skills = document.getElementById("input-skills").value.trim();
  const exp = document.getElementById("input-experience").value;
  const visaOnly = document.getElementById("filter-visa-only") ? document.getElementById("filter-visa-only").checked : false;

  const params = new URLSearchParams();
  if (query) params.append("q", query);
  if (country && country !== "Worldwide") params.append("country", country);
  if (workplace && workplace !== "All") params.append("workplace_type", workplace);
  if (candidateOrigin) params.append("candidate_origin", candidateOrigin);
  if (skills) params.append("skills", skills);
  if (exp) params.append("experience", exp);
  if (visaOnly) params.append("visa_sponsorship", "true");
  if (refreshLive) params.append("refresh_live", "true");
  params.append("limit", "50");

  try {
    const res = await fetch(`/api/global/search?${params.toString()}`);
    const data = await res.json();
    let results = data.results || [];

    // Filter by candidate eligibility if checkbox is checked
    const eligibleOnly = document.getElementById("filter-eligible-only") ? document.getElementById("filter-eligible-only").checked : false;
    if (eligibleOnly) {
      results = results.filter(r => r.job.candidate_eligibility.is_eligible);
    }

    loadedJobs = results.map(r => r.job);
    document.getElementById("total-jobs-count").textContent = results.length;
    document.getElementById("current-scope-label").textContent = country === "Worldwide" ? "Worldwide & Bangladesh" : country;

    renderJobsTable(results);
  } catch (err) {
    console.error("Error loading jobs:", err);
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--accent-rose); padding: 30px;">Failed to load job listings. Please ensure server is running.</td></tr>`;
  }
}

function renderJobsTable(results) {
  const tbody = document.getElementById("jobs-table-body");
  if (!results.length) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 40px;">No matching opportunities found for current filters. Try relaxing your search criteria.</td></tr>`;
    return;
  }

  tbody.innerHTML = results.map(({ job, score }) => {
    const workplace = job.workplace_type || "On-site";
    const modeBadge = workplace === "Remote" 
      ? '<span class="ac-badge badge-role" style="background: rgba(99, 102, 241, 0.25); color: #c7d2fe;">Remote</span>'
      : (workplace === "Hybrid" ? '<span class="ac-badge" style="background: rgba(245, 158, 11, 0.2); color: #fcd34d;">Hybrid</span>' : '<span class="ac-badge" style="background: rgba(255, 255, 255, 0.08); color: var(--text-muted);">On-site</span>');

    // Candidate Eligibility badge
    let eligBadge = "";
    const elig = job.candidate_eligibility;
    if (elig.is_eligible) {
      if (job.remote_eligibility.policy === "Worldwide") {
        eligBadge = '<span class="badge-worldwide" title="' + escapeHtml(elig.reason) + '">🌍 Worldwide Remote</span>';
      } else if (job.remote_eligibility.visa_sponsorship) {
        eligBadge = '<span class="badge-visa" title="' + escapeHtml(elig.reason) + '">🛂 Visa Sponsorship</span>';
      } else {
        eligBadge = '<span class="badge-eligible" title="' + escapeHtml(elig.reason) + '">✓ Eligible</span>';
      }
    } else {
      eligBadge = '<span class="badge-ineligible" title="' + escapeHtml(elig.reason) + '">⚠ Ineligible</span>';
    }

    // Salary string with dual-currency display
    let salaryDisplay = `<span style="color: var(--text-muted);">Negotiable</span>`;
    if (job.salary.disclosed) {
      if (job.salary.currency === "USD") {
        salaryDisplay = `<strong>${job.salary.raw_text}</strong><div style="font-size: 11px; color: #818cf8;">~${formatBDT(job.salary.salary_bdt_min)} BDT</div>`;
      } else if (job.salary.currency === "BDT") {
        salaryDisplay = `<strong>${job.salary.raw_text}</strong><div style="font-size: 11px; color: #6ee7b7;">~$${formatUSD(job.salary.salary_usd_min)} USD</div>`;
      } else {
        salaryDisplay = `<strong>${job.salary.raw_text}</strong><div style="font-size: 11px; color: #818cf8;">~$${formatUSD(job.salary.salary_usd_min)} USD</div>`;
      }
    }

    // Provenance / source link
    const sourceLabel = job.source_reliability === "official_career_page" ? `⭐ ${job.source} (Official)` : job.source;

    return `
      <tr>
        <td>
          <div class="job-title">${escapeHtml(job.title)}</div>
          <div class="job-skills">${(job.skills_required || []).slice(0, 4).map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join("")}</div>
          <div style="font-size: 10px; color: var(--text-muted); margin-top: 4px;">Source: ${sourceLabel}</div>
        </td>
        <td>
          <div class="company-name">${escapeHtml(job.company.name)}</div>
          <span class="company-tier tier-${job.company.tier.toLowerCase().replace(/[^a-z]/g, '-')}">${job.company.tier}</span>
        </td>
        <td>
          <div>${escapeHtml(job.location || job.country)}</div>
          <div style="margin-top: 4px;">${modeBadge}</div>
        </td>
        <td>
          ${eligBadge}
          <div style="font-size: 10px; color: var(--text-muted); max-width: 140px; margin-top: 2px;">${escapeHtml(elig.reason)}</div>
        </td>
        <td>${salaryDisplay}</td>
        <td>
          <div class="score-pill">${Math.round(score.final_score * 100)}%</div>
        </td>
        <td>
          <a href="${job.apply_url}" target="_blank" rel="noopener noreferrer" class="apply-btn-direct" title="Open original job application on ${escapeHtml(job.source)}">
            Apply Now ↗
          </a>
        </td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="openTrackModal('${job.id}', '${escapeHtml(job.title).replace(/'/g, "\\'")}', '${escapeHtml(job.company.name).replace(/'/g, "\\'")}', ${score.final_score})">
            📌 Track
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

function formatBDT(amount) {
  if (!amount) return "0";
  if (amount >= 10000000) return (amount / 10000000).toFixed(1) + " Cr";
  if (amount >= 100000) return (amount / 100000).toFixed(1) + " Lakh";
  return amount.toLocaleString();
}

function formatUSD(amount) {
  if (!amount) return "0";
  if (amount >= 1000) return (amount / 1000).toFixed(0) + "K";
  return amount.toLocaleString();
}

// ==================== REMOTE-FIRST SECTION ====================

async function loadRemoteJobsView(region = "Worldwide") {
  const container = document.getElementById("remote-jobs-container");
  container.innerHTML = `<div class="loading-container" style="grid-column: 1/-1;"><div class="loader-spinner"></div><p style="margin-top: 10px;">Loading verified ${region} remote positions...</p></div>`;

  const candidateOrigin = document.getElementById("candidate-origin") ? document.getElementById("candidate-origin").value : "Bangladesh";
  try {
    const res = await fetch(`/api/global/remote?region=${encodeURIComponent(region)}&candidate_origin=${encodeURIComponent(candidateOrigin)}`);
    const data = await res.json();
    const results = data.results || [];

    if (!results.length) {
      container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 40px;">No remote positions found in this regional filter.</div>`;
      return;
    }

    container.innerHTML = results.map(({ job, score }) => `
      <div class="job-card">
        <div>
          <div class="job-card-header">
            <div>
              <div class="job-card-title">${escapeHtml(job.title)}</div>
              <div class="job-card-company">${escapeHtml(job.company.name)} · <span style="color: var(--accent-indigo);">${job.source}</span></div>
            </div>
            <div class="score-pill">${Math.round(score.final_score * 100)}%</div>
          </div>
          <div style="margin: 8px 0;">
            ${job.candidate_eligibility.is_eligible 
              ? '<span class="badge-worldwide">🌍 Worldwide / ' + escapeHtml(job.candidate_eligibility.reason) + '</span>'
              : '<span class="badge-ineligible">⚠ ' + escapeHtml(job.candidate_eligibility.reason) + '</span>'}
          </div>
          <div class="job-card-meta">
            ${(job.skills_required || []).map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join("")}
          </div>
        </div>
        <div class="job-card-footer">
          <div>
            <strong>${job.salary.raw_text}</strong>
            <div style="font-size: 11px; color: var(--text-muted);">${escapeHtml(job.location)}</div>
          </div>
          <a href="${job.apply_url}" target="_blank" rel="noopener noreferrer" class="apply-btn-direct">
            Apply Now ↗
          </a>
        </div>
      </div>
    `).join("");
  } catch (err) {
    container.innerHTML = `<div style="grid-column: 1/-1; color: var(--accent-rose); text-align: center;">Failed to load remote feed.</div>`;
  }
}

// ==================== COUNTRY EXPLORER ====================

async function loadCountryExplorerView() {
  const container = document.getElementById("country-cards-grid");
  container.innerHTML = `<div class="loading-container" style="grid-column: 1/-1;"><div class="loader-spinner"></div><p style="margin-top: 10px;">Aggregating worldwide market metrics...</p></div>`;

  const flagMap = {
    "Bangladesh": "🇧🇩",
    "United States": "🇺🇸",
    "Germany": "🇩🇪",
    "India": "🇮🇳",
    "Singapore": "🇸🇬",
    "United Kingdom": "🇬🇧",
    "Japan": "🇯🇵",
    "Canada": "🇨🇦",
    "Australia": "🇦🇺",
    "United Arab Emirates": "🇦🇪",
    "Netherlands": "🇳🇱",
    "Ireland": "🇮🇪",
    "France": "🇫🇷",
    "Sweden": "🇸🇪"
  };

  try {
    const res = await fetch("/api/global/countries");
    const data = await res.json();
    const countries = data.countries || [];

    if (!countries.length) {
      container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 40px;">No country statistics available.</div>`;
      return;
    }

    container.innerHTML = countries.map(c => {
      const flag = flagMap[c.country] || "🌐";
      return `
        <div class="country-card" onclick="filterByCountry('${escapeHtml(c.country)}')">
          <div class="country-card-header">
            <div class="country-name-group">
              <span style="font-size: 24px;">${flag}</span>
              <span>${escapeHtml(c.country)}</span>
            </div>
            <span class="country-vacancies-count">${c.total_jobs} Openings</span>
          </div>

          <div class="country-stats-row">
            <span>Remote Ratio:</span>
            <strong>${c.remote_pct}% (${c.remote_jobs} Remote)</strong>
          </div>
          <div class="country-progress-bar">
            <div class="country-progress-fill" style="width: ${c.remote_pct}%;"></div>
          </div>

          <div class="country-stats-row">
            <span>Visa Sponsorship:</span>
            <strong>${c.visa_sponsorship_jobs} Available</strong>
          </div>

          <div style="font-size: 11px; color: var(--text-muted); margin-top: 8px;">
            Top Hiring: ${escapeHtml((c.top_companies || []).join(", "))}
          </div>

          <div style="text-align: right; margin-top: 14px;">
            <button class="btn btn-secondary btn-sm" style="width: 100%;">Explore ${escapeHtml(c.country)} Jobs →</button>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    container.innerHTML = `<div style="grid-column: 1/-1; color: var(--accent-rose); text-align: center;">Failed to load country explorer.</div>`;
  }
}

function filterByCountry(countryName) {
  document.getElementById("filter-country").value = countryName;
  switchView("nav-tab-explorer", "view-explorer");
  loadJobs();
}

// ==================== RECOMMENDED FOR YOU ====================

async function loadRecommendedJobsView() {
  const container = document.getElementById("recommended-jobs-container");
  const profileBar = document.getElementById("recommendation-profile-bar");
  container.innerHTML = `<div class="loading-container" style="grid-column: 1/-1;"><div class="loader-spinner"></div><p style="margin-top: 10px;">Tailoring personalized recommendations...</p></div>`;

  const skills = document.getElementById("input-skills").value.trim() || "Python, React, C++";
  const exp = document.getElementById("input-experience").value;
  const origin = document.getElementById("candidate-origin") ? document.getElementById("candidate-origin").value : "Bangladesh";

  profileBar.innerHTML = `
    <span class="skill-tag" style="background: var(--accent-indigo); color: #fff;">Origin: ${origin}</span>
    <span class="skill-tag">Target Skills: ${skills}</span>
    <span class="skill-tag">Experience: ${exp}y</span>
  `;

  try {
    const res = await fetch(`/api/global/recommendations?skills=${encodeURIComponent(skills)}&experience=${exp}&candidate_origin=${encodeURIComponent(origin)}`);
    const data = await res.json();
    const results = data.results || [];

    if (!results.length) {
      container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 40px;">No recommendations found matching current profile.</div>`;
      return;
    }

    container.innerHTML = results.map(({ job, score }) => `
      <div class="job-card">
        <div>
          <div class="job-card-header">
            <div>
              <div class="job-card-title">${escapeHtml(job.title)}</div>
              <div class="job-card-company">${escapeHtml(job.company.name)} · <span>${escapeHtml(job.country)}</span></div>
            </div>
            <div class="score-pill">${Math.round(score.final_score * 100)}%</div>
          </div>
          <div style="font-size: 11px; color: #a5b4fc; margin: 6px 0;">
            ${job.experience_level} · ${job.workplace_type} · ${job.employment_type}
          </div>
          <div class="job-card-meta">
            ${(job.skills_required || []).map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join("")}
          </div>
        </div>
        <div class="job-card-footer">
          <div>
            <strong>${job.salary.raw_text}</strong>
          </div>
          <a href="${job.apply_url}" target="_blank" rel="noopener noreferrer" class="apply-btn-direct">
            Apply Now ↗
          </a>
        </div>
      </div>
    `).join("");
  } catch (err) {
    container.innerHTML = `<div style="grid-column: 1/-1; color: var(--accent-rose); text-align: center;">Failed to load recommendations.</div>`;
  }
}

// ==================== 8-STAGE APPLICATION TRACKER ====================

async function loadTrackedJobsView() {
  const stages = [
    { id: "pipe-saved", status: "Saved" },
    { id: "pipe-planning", status: "Planning to Apply" },
    { id: "pipe-applied", status: "Applied" },
    { id: "pipe-interview", status: "Interview" },
    { id: "pipe-test", status: "Technical Test" },
    { id: "pipe-offer", status: "Offer" },
    { id: "pipe-rejected", status: "Rejected" },
    { id: "pipe-withdrawn", status: "Withdrawn" }
  ];

  stages.forEach(s => {
    const el = document.getElementById(s.id);
    if (el) el.innerHTML = `<div style="color: var(--text-muted); font-size: 11px; text-align: center; padding: 20px;">Empty</div>`;
  });

  try {
    const res = await fetch("/api/global/tracker");
    const data = await res.json();
    const tracked = data.tracked_jobs || [];

    document.getElementById("tracker-count").textContent = tracked.length;

    stages.forEach(stage => {
      const items = tracked.filter(t => t.status === stage.status);
      const colEl = document.querySelector(`.pipeline-column[data-status="${stage.status}"] .pipe-count`);
      if (colEl) colEl.textContent = items.length;

      const itemsContainer = document.getElementById(stage.id);
      if (!itemsContainer) return;

      if (!items.length) {
        itemsContainer.innerHTML = `<div style="color: var(--text-muted); font-size: 11px; text-align: center; padding: 20px;">No jobs in this stage</div>`;
        return;
      }

      itemsContainer.innerHTML = items.map(item => `
        <div class="tracker-card" onclick="openTrackModal('${item.job_id}', '${escapeHtml(item.title || item.job_id)}', '${escapeHtml(item.company_name || '')}', ${item.score || 0})">
          <div class="tracker-card-title">${escapeHtml(item.title || item.job_id)}</div>
          <div class="tracker-card-company">${escapeHtml(item.company_name || '')} · ${escapeHtml(item.country || '')}</div>
          ${item.notes ? `<div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 6px; font-style: italic;">"${escapeHtml(item.notes)}"</div>` : ''}
          <div class="tracker-card-footer">
            <span>${item.updated_at ? item.updated_at.split('T')[0] : 'Recently'}</span>
            <a href="${item.apply_url || '#'}" target="_blank" onclick="event.stopPropagation();" style="color: #818cf8; text-decoration: underline;">Link ↗</a>
          </div>
        </div>
      `).join("");
    });
  } catch (err) {
    console.error("Error loading tracker:", err);
  }
}

function openTrackModal(jobId, title, company, score) {
  document.getElementById("track-modal-job-id").value = jobId;
  document.getElementById("track-modal-title").textContent = `Track: ${title}`;
  document.getElementById("track-modal").classList.add("show");
}

async function handleSaveTrackStage() {
  const jobId = document.getElementById("track-modal-job-id").value;
  const status = document.getElementById("track-modal-status").value;
  const recruiter = document.getElementById("track-modal-recruiter").value;
  const notes = document.getElementById("track-modal-notes").value;

  try {
    await fetch("/api/global/tracker", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_id: jobId,
        status: status,
        recruiter_info: recruiter,
        notes: notes,
        score: 0.85
      })
    });
    document.getElementById("track-modal").classList.remove("show");
    loadTrackedJobsCount();
    loadTrackedJobsView();
  } catch (err) {
    alert("Could not update job stage: " + err);
  }
}

// ==================== ALERTS VIEW ====================

async function loadAlertsView() {
  const container = document.getElementById("alerts-list-container");
  container.innerHTML = `<div class="loading-container" style="grid-column: 1/-1;"><div class="loader-spinner"></div><p style="margin-top: 10px;">Loading your active alerts...</p></div>`;

  try {
    const res = await fetch("/api/global/alerts");
    const data = await res.json();
    const alerts = data.alerts || [];

    document.getElementById("alerts-count").textContent = alerts.length;

    if (!alerts.length) {
      container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 40px;">No alerts created yet. Create one above to receive instant notifications.</div>`;
      return;
    }

    container.innerHTML = alerts.map(a => `
      <div class="alert-card">
        <div class="alert-card-title">${escapeHtml(a.title)}</div>
        <div class="alert-card-criteria">
          <div><strong>Keywords:</strong> ${escapeHtml(a.query || 'Any')}</div>
          <div><strong>Country Scope:</strong> ${escapeHtml(a.country || 'Worldwide')}</div>
          <div><strong>Remote Preference:</strong> ${a.remote_only ? 'Remote Only' : 'All Modes'}</div>
          <div><strong>Status:</strong> <span style="color: #6ee7b7;">● Active Monitoring</span></div>
        </div>
      </div>
    `).join("");
  } catch (err) {
    container.innerHTML = `<div style="grid-column: 1/-1; color: var(--accent-rose); text-align: center;">Failed to load alerts.</div>`;
  }
}

async function handleCreateAlert() {
  const query = document.getElementById("new-alert-query").value.trim();
  const country = document.getElementById("new-alert-country").value;
  if (!query) {
    alert("Please enter a job title or skill keywords for the alert.");
    return;
  }

  const title = `Alert: ${query} (${country})`;
  try {
    await fetch("/api/global/alerts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: title,
        query: query,
        country: country,
        remote_only: true
      })
    });
    document.getElementById("new-alert-query").value = "";
    loadAlertsView();
    loadAlertsCount();
  } catch (err) {
    alert("Failed to save alert: " + err);
  }
}

// ==================== MARKET ANALYTICS ====================

async function loadMarketAnalytics() {
  try {
    const res = await fetch("/api/analytics");
    const data = await res.json();
    document.getElementById("stat-total-jobs").textContent = data.total_openings || 0;
    document.getElementById("stat-transparency").textContent = `${data.transparency_rate || 0}%`;
    document.getElementById("stat-median-salary").textContent = `${(data.median_salary_bdt || 0).toLocaleString()} BDT`;
  } catch (err) {
    console.error("Error loading analytics:", err);
  }
}

// ==================== TAXONOMY & HELPERS ====================

async function loadTaxonomy() {
  try {
    const res = await fetch("/api/taxonomy");
    currentTaxonomy = await res.json();
    renderCategoryChips();
  } catch (err) {
    console.error("Error loading taxonomy:", err);
  }
}

function switchTab(tabName) {
  currentTab = tabName;
  document.getElementById("tab-functional").classList.toggle("active", tabName === "Functional");
  document.getElementById("tab-special").classList.toggle("active", tabName === "Special Skilled");
  const tabGlobal = document.getElementById("tab-global-sources");
  if (tabGlobal) tabGlobal.classList.toggle("active", tabName === "Global");
  renderCategoryChips();
}

function renderCategoryChips(searchFilter = "") {
  const container = document.getElementById("category-chips-container");
  let categories = [];
  
  if (currentTab === "Global") {
    categories = [
      { id: 901, name: "Remote OK (Worldwide Tech)", job_count: "Global" },
      { id: 902, name: "We Work Remotely (Engineering)", job_count: "Global" },
      { id: 903, name: "Indeed Global (DE, UK, US, IN, SG)", job_count: "Multi-Country" },
      { id: 904, name: "Company Career Pages (Google, MS)", job_count: "Direct" }
    ];
  } else {
    categories = (currentTaxonomy.categories || []).filter(c => c.type === currentTab);
  }

  if (searchFilter) {
    categories = categories.filter(c => c.name.toLowerCase().includes(searchFilter.toLowerCase()));
  }

  container.innerHTML = categories.map(cat => `
    <div class="cat-chip ${cat.id === selectedCategoryId ? 'active' : ''}" onclick="selectCategory(${cat.id})">
      <span>${escapeHtml(cat.name)}</span>
      <span class="cat-count">${cat.job_count || ''}</span>
    </div>
  `).join("");
}

function selectCategory(catId) {
  selectedCategoryId = catId;
  renderCategoryChips();
  loadJobs();
}

async function loadTrackedJobsCount() {
  try {
    const res = await fetch("/api/global/tracker");
    const data = await res.json();
    document.getElementById("tracker-count").textContent = (data.tracked_jobs || []).length;
  } catch (e) {}
}

async function loadAlertsCount() {
  try {
    const res = await fetch("/api/global/alerts");
    const data = await res.json();
    document.getElementById("alerts-count").textContent = (data.alerts || []).length;
  } catch (e) {}
}

async function handleLinkedInSubmit() {
  const text = document.getElementById("linkedin-paste-text").value.trim();
  if (!text) {
    alert("Please paste LinkedIn job text or JSON-LD first.");
    return;
  }

  try {
    const res = await fetch("/api/ingest/linkedin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: text,
        target_category_id: selectedCategoryId
      })
    });
    if (!res.ok) throw new Error("Could not parse LinkedIn text");
    document.getElementById("linkedin-modal").classList.remove("show");
    document.getElementById("linkedin-paste-text").value = "";
    loadJobs();
  } catch (err) {
    alert("Error: " + err.message);
  }
}

function setupBookmarkletLink() {
  const bLink = document.getElementById("draggable-bookmarklet");
  if (bLink) {
    bLink.href = `javascript:(function(){var d=document.body.innerText||'';fetch('http://127.0.0.1:8000/api/ingest/linkedin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:d.substring(0,6000),target_category_id:8})}).then(r=>r.json()).then(data=>{alert('Job Analyzer: Successfully ingested \"'+(data.job?data.job.title:'Job')+'\"!');}).catch(e=>{alert('Job Analyzer: Ingestion failed. Ensure local server is running.');});})();`;
  }
}

function exportToCSV() {
  if (!loadedJobs.length) {
    alert("No jobs loaded to export.");
    return;
  }
  const rows = [
    ["Title", "Company", "Country", "Location", "Workplace Mode", "Eligibility", "Salary", "Source", "Apply URL"]
  ];
  loadedJobs.forEach(j => {
    rows.push([
      `"${j.title.replace(/"/g, '""')}"`,
      `"${j.company.name.replace(/"/g, '""')}"`,
      `"${j.country}"`,
      `"${j.location.replace(/"/g, '""')}"`,
      `"${j.workplace_type}"`,
      `"${j.candidate_eligibility.status}"`,
      `"${j.salary.raw_text}"`,
      `"${j.source}"`,
      `"${j.apply_url}"`
    ]);
  });
  const csvContent = "data:text/csv;charset=utf-8," + rows.map(e => e.join(",")).join("\n");
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", `job_analyzer_export_${new Date().toISOString().split('T')[0]}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
