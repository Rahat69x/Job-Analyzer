// Job Analyzer — Global Job Discovery & Remote Job Platform Controller

let currentTaxonomy = { categories: [], industries: [] };
let currentTab = "Functional";
let loadedJobs = [];
let activeCompanyFilter = null;

const GLOBAL_CONNECTORS = [
  { id: 901, name: "Remote OK (Worldwide Tech)", source: "Remote OK", job_count: "Global" },
  { id: 902, name: "We Work Remotely (Engineering)", source: "We Work Remotely", job_count: "Global" },
  { id: 903, name: "Indeed Global (DE, UK, US, IN, SG)", source: "Indeed", job_count: "Multi-Country" },
  { id: 904, name: "Company Career Pages (Google, MS)", source: "CompanyCareerPage", job_count: "Direct" },
  { id: 905, name: "Curated Top Companies (72 Global)", source: "CompanyCareerPage", job_count: "Curated" },
  { id: 906, name: "BDJobs Corporate Network", source: "BDJobs", job_count: "Bangladesh" },
  { id: 907, name: "Skill.jobs Technology Portal", source: "Skill.jobs", job_count: "Partner" },
  { id: 908, name: "Chakri.com Professional Hub", source: "Chakri", job_count: "Partner" }
];

const tabConfig = {
  "Functional": {
    label: "Selected Sector:",
    hint: "• Showing all industry sectors across global & Bangladesh sources • Click any industry sector to filter live jobs",
    selectedId: null,
    selectedName: "All Sectors",
    filterType: "category_id"
  },
  "Special Skilled": {
    label: "Selected Skill:",
    hint: "• Showing all vocational skills • Click any skill to filter live jobs",
    selectedId: null,
    selectedName: "All Skills",
    filterType: "category_id"
  },
  "Global": {
    label: "Selected Source:",
    hint: "• Showing all connected worldwide & Bangladesh sources • Click any source to filter",
    selectedId: null,
    selectedName: "All Global & BD Sources",
    selectedSource: null,
    filterType: "source"
  }
};

// Debounce utility for real-time search
function debounce(fn, delay = 400) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}
const debouncedLoadJobs = debounce(() => loadJobs(), 400);

// ==================== SALARY FILTER STATE & HELPERS ====================
const salaryState = {
  currency: "BDT", // "BDT" (Monthly) or "USD" (Annual)
  min: 0,
  max: 0,
  sliderMaxBDT: 200000,
  sliderMaxUSD: 200000,
  stepBDT: 5000,
  stepUSD: 5000,
  exchangeRate: 120 // 1 USD = 120 BDT
};

const SALARY_PRESETS = {
  BDT: [
    { label: "Any", val: 0 },
    { label: "30K+ ৳", val: 30000 },
    { label: "60K+ ৳", val: 60000 },
    { label: "100K+ ৳ (High)", val: 100000 },
    { label: "$50K+ (Global)", val: 500000 }
  ],
  USD: [
    { label: "Any", val: 0 },
    { label: "$30K+", val: 30000 },
    { label: "$60K+", val: 60000 },
    { label: "$100K+ (High)", val: 100000 },
    { label: "$150K+ (Top)", val: 150000 }
  ]
};

function updateSalarySliderFill(val) {
  const slider = document.getElementById("input-salary-slider");
  if (!slider) return;
  const min = parseFloat(slider.min) || 0;
  const max = parseFloat(slider.max) || 100;
  const pct = Math.min(100, Math.max(0, ((val - min) / (max - min)) * 100));
  slider.style.background = `linear-gradient(to right, #6366f1 0%, #6366f1 ${pct}%, #e2e8f0 ${pct}%, #e2e8f0 100%)`;
}

function formatSalaryDisplay(val, currency) {
  if (!val || val <= 0) return "Any";
  if (currency === "BDT") {
    if (val >= 100000) return `৳${(val / 100000).toFixed(val % 100000 === 0 ? 0 : 1)}L+/mo`;
    return `৳${Math.round(val / 1000)}k+/mo`;
  } else {
    return `$${Math.round(val / 1000)}k+/yr`;
  }
}

function updateSalaryReadout() {
  const readout = document.getElementById("salary-dual-readout");
  const badge = document.getElementById("label-salary-display");
  if (!readout || !badge) return;

  const minVal = salaryState.min;
  const maxVal = salaryState.max;

  badge.textContent = formatSalaryDisplay(minVal, salaryState.currency);

  if (minVal <= 0 && maxVal <= 0) {
    readout.innerHTML = `<span>All salaries (Disclosed & Negotiable)</span>`;
    return;
  }

  if (salaryState.currency === "BDT") {
    // BDT Monthly
    const bdtMinText = minVal > 0 ? `৳${minVal.toLocaleString()}` : "0";
    const bdtMaxText = maxVal > 0 ? `৳${maxVal.toLocaleString()}` : "";
    const bdtRange = maxVal > 0 ? `${bdtMinText} – ${bdtMaxText}/mo` : `≥ ${bdtMinText}/mo`;

    // Dual conversion in USD (annual)
    const usdMinAnnual = Math.round((minVal * 12) / salaryState.exchangeRate);
    const usdMaxAnnual = maxVal > 0 ? Math.round((maxVal * 12) / salaryState.exchangeRate) : 0;
    const usdEquiv = maxVal > 0 
      ? `~$${(usdMinAnnual / 1000).toFixed(0)}k–$${(usdMaxAnnual / 1000).toFixed(0)}k/yr USD`
      : `~$${(usdMinAnnual / 1000).toFixed(0)}k+/yr USD`;

    readout.innerHTML = `<span>Range: <strong>${bdtRange}</strong></span><span style="color: #6ee7b7; font-size: 10.5px;">${usdEquiv}</span>`;
  } else {
    // USD Annual
    const usdMinText = minVal > 0 ? `$${minVal.toLocaleString()}` : "0";
    const usdMaxText = maxVal > 0 ? `$${maxVal.toLocaleString()}` : "";
    const usdRange = maxVal > 0 ? `${usdMinText} – ${usdMaxText}/yr` : `≥ ${usdMinText}/yr`;

    // Dual conversion in BDT (monthly)
    const bdtMinMo = Math.round((minVal * salaryState.exchangeRate) / 12);
    const bdtMaxMo = maxVal > 0 ? Math.round((maxVal * salaryState.exchangeRate) / 12) : 0;
    const bdtEquiv = maxVal > 0
      ? `~৳${formatBDT(bdtMinMo)}–${formatBDT(bdtMaxMo)}/mo`
      : `~৳${formatBDT(bdtMinMo)}+/mo BDT`;

    readout.innerHTML = `<span>Range: <strong>${usdRange}</strong></span><span style="color: #818cf8; font-size: 10.5px;">${bdtEquiv}</span>`;
  }
}

function renderSalaryPresets() {
  const container = document.getElementById("salary-quick-presets");
  if (!container) return;
  const presets = SALARY_PRESETS[salaryState.currency] || SALARY_PRESETS.BDT;
  container.innerHTML = presets.map(p => {
    const isActive = (salaryState.min === p.val && salaryState.max === 0);
    return `<button type="button" class="salary-preset-btn ${isActive ? 'active' : ''}" data-val="${p.val}">${p.label}</button>`;
  }).join("");

  container.querySelectorAll(".salary-preset-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const val = parseFloat(btn.getAttribute("data-val")) || 0;
      setSalaryFilter(val, 0, true);
    });
  });
}

function setSalaryFilter(minVal, maxVal = 0, triggerSearch = true) {
  salaryState.min = Math.max(0, minVal);
  salaryState.max = Math.max(0, maxVal);

  const slider = document.getElementById("input-salary-slider");
  const minInput = document.getElementById("input-salary-min");
  const maxInput = document.getElementById("input-salary-max");

  if (slider) {
    slider.value = salaryState.min;
    updateSalarySliderFill(salaryState.min);
  }

  if (minInput) minInput.value = salaryState.min > 0 ? salaryState.min : "";
  if (maxInput) maxInput.value = salaryState.max > 0 ? salaryState.max : "";

  updateSalaryReadout();

  const presets = document.querySelectorAll(".salary-preset-btn");
  presets.forEach(p => {
    const val = parseFloat(p.getAttribute("data-val")) || 0;
    p.classList.toggle("active", val === salaryState.min && salaryState.max === 0);
  });

  if (triggerSearch) {
    loadJobs();
  }
}

function setSalaryCurrency(curr) {
  if (salaryState.currency === curr) return;
  salaryState.currency = curr;

  const btnBdt = document.getElementById("btn-curr-bdt");
  const btnUsd = document.getElementById("btn-curr-usd");
  const prefixMin = document.getElementById("salary-prefix-min");
  const prefixMax = document.getElementById("salary-prefix-max");
  const slider = document.getElementById("input-salary-slider");

  if (curr === "BDT") {
    if (btnBdt) btnBdt.classList.add("active");
    if (btnUsd) btnUsd.classList.remove("active");
    if (prefixMin) prefixMin.textContent = "৳";
    if (prefixMax) prefixMax.textContent = "৳";
    if (slider) {
      slider.max = salaryState.sliderMaxBDT;
      slider.step = salaryState.stepBDT;
    }
  } else {
    if (btnBdt) btnBdt.classList.remove("active");
    if (btnUsd) btnUsd.classList.add("active");
    if (prefixMin) prefixMin.textContent = "$";
    if (prefixMax) prefixMax.textContent = "$";
    if (slider) {
      slider.max = salaryState.sliderMaxUSD;
      slider.step = salaryState.stepUSD;
    }
  }

  salaryState.min = 0;
  salaryState.max = 0;
  if (slider) {
    slider.value = 0;
    updateSalarySliderFill(0);
  }
  const minInput = document.getElementById("input-salary-min");
  const maxInput = document.getElementById("input-salary-max");
  if (minInput) minInput.value = "";
  if (maxInput) maxInput.value = "";

  renderSalaryPresets();
  updateSalaryReadout();
  loadJobs();
}

document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  setupBookmarkletLink();
  loadTaxonomy();
  loadTrackedJobsCount();
  loadAlertsCount();
  loadSourceHealthTabBadge();
  loadJobs(); // Initial catalog load
});

function initEventListeners() {
  // Navigation Tabs (10 views)
  const navTabs = [
    { id: "nav-tab-explorer", view: "view-explorer", onOpen: null },
    { id: "nav-tab-remote", view: "view-remote", onOpen: loadRemoteJobsView },
    { id: "nav-tab-country", view: "view-country", onOpen: loadCountryExplorerView },
    { id: "nav-tab-recommended", view: "view-recommended", onOpen: loadRecommendedJobsView },
    { id: "nav-tab-tracker", view: "view-tracker", onOpen: loadTrackedJobsView },
    { id: "nav-tab-alerts", view: "view-alerts", onOpen: loadAlertsView },
    { id: "nav-tab-source-health", view: "view-source-health", onOpen: loadSourceHealthView },
    { id: "nav-tab-analytics", view: "view-analytics", onOpen: loadMarketAnalytics },
    { id: "nav-tab-companies", view: "view-companies", onOpen: loadCompaniesView },
    { id: "nav-tab-ai-analytics", view: "view-ai-analytics", onOpen: loadAiMarketAnalyticsView }
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

  // Salary Filter Controls
  const salarySlider = document.getElementById("input-salary-slider");
  if (salarySlider) {
    updateSalarySliderFill(salarySlider.value);
    salarySlider.addEventListener("input", (e) => {
      const val = parseFloat(e.target.value) || 0;
      salaryState.min = val;
      updateSalarySliderFill(val);
      const minInput = document.getElementById("input-salary-min");
      if (minInput) minInput.value = val > 0 ? val : "";
      updateSalaryReadout();
      document.querySelectorAll(".salary-preset-btn").forEach(p => {
        const pVal = parseFloat(p.getAttribute("data-val")) || 0;
        p.classList.toggle("active", pVal === val && salaryState.max === 0);
      });
    });
    salarySlider.addEventListener("change", () => loadJobs());
  }

  const btnCurrBdt = document.getElementById("btn-curr-bdt");
  if (btnCurrBdt) {
    btnCurrBdt.addEventListener("click", () => setSalaryCurrency("BDT"));
  }
  const btnCurrUsd = document.getElementById("btn-curr-usd");
  if (btnCurrUsd) {
    btnCurrUsd.addEventListener("click", () => setSalaryCurrency("USD"));
  }

  const minSalaryInput = document.getElementById("input-salary-min");
  if (minSalaryInput) {
    minSalaryInput.addEventListener("input", debounce(() => {
      const val = parseFloat(minSalaryInput.value) || 0;
      salaryState.min = val;
      if (salarySlider && val <= parseFloat(salarySlider.max)) {
        salarySlider.value = val;
        updateSalarySliderFill(val);
      }
      updateSalaryReadout();
      loadJobs();
    }, 400));
  }

  const maxSalaryInput = document.getElementById("input-salary-max");
  if (maxSalaryInput) {
    maxSalaryInput.addEventListener("input", debounce(() => {
      const val = parseFloat(maxSalaryInput.value) || 0;
      salaryState.max = val;
      updateSalaryReadout();
      loadJobs();
    }, 400));
  }

  const btnSalaryReset = document.getElementById("btn-salary-reset");
  if (btnSalaryReset) {
    btnSalaryReset.addEventListener("click", () => {
      setSalaryFilter(0, 0, true);
    });
  }

  renderSalaryPresets();
  updateSalaryReadout();

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

  // Country & Workplace & Sort & Freshness filter dropdowns — real-time
  const countryFilter = document.getElementById("filter-country");
  if (countryFilter) countryFilter.addEventListener("change", () => loadJobs());
  const workplaceFilter = document.getElementById("filter-workplace");
  if (workplaceFilter) workplaceFilter.addEventListener("change", () => loadJobs());
  const sortFilter = document.getElementById("filter-sort");
  if (sortFilter) sortFilter.addEventListener("change", () => loadJobs());
  const freshnessFilter = document.getElementById("filter-freshness");
  if (freshnessFilter) freshnessFilter.addEventListener("change", () => loadJobs());

  // Source Health Dashboard event listeners
  const btnTrigger = document.getElementById("btn-trigger-pipeline");
  if (btnTrigger) btnTrigger.addEventListener("click", triggerIngestionPipeline);
  const btnRefreshH = document.getElementById("btn-refresh-health");
  if (btnRefreshH) btnRefreshH.addEventListener("click", loadSourceHealthView);

  const sourceCatButtons = document.querySelectorAll(".source-cat-btn");
  sourceCatButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      sourceCatButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const cat = btn.getAttribute("data-cat");
      renderSourceHealthTable(cat);
    });
  });

  // Companies Tab & Filters
  const tabCompanies = document.getElementById("nav-tab-companies");
  if (tabCompanies) {
    tabCompanies.addEventListener("click", () => {
      switchView("nav-tab-companies", "view-companies");
      loadCompaniesView();
    });
  }
  const companyInput = document.getElementById("company-filter-input");
  if (companyInput) companyInput.addEventListener("input", debounce(loadCompaniesView, 250));
  const companySort = document.getElementById("company-sort-select");
  if (companySort) companySort.addEventListener("change", loadCompaniesView);

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

  // Apply Flow Modal
  const aModal = document.getElementById("apply-flow-modal");
  const btnCloseApply = document.getElementById("btn-close-apply-modal");
  if (btnCloseApply) btnCloseApply.addEventListener("click", () => aModal.classList.remove("show"));
  const btnCancelApply = document.getElementById("btn-cancel-apply");
  if (btnCancelApply) btnCancelApply.addEventListener("click", () => aModal.classList.remove("show"));

  const btnCopyPitch = document.getElementById("btn-copy-pitch");
  if (btnCopyPitch) {
    btnCopyPitch.addEventListener("click", () => {
      const pitchText = document.getElementById("apply-preserved-pitch").value;
      navigator.clipboard.writeText(pitchText).then(() => {
        btnCopyPitch.textContent = "✓ Copied!";
        setTimeout(() => { btnCopyPitch.textContent = "📋 Copy Pitch"; }, 2000);
      });
    });
  }

  const btnCopySkills = document.getElementById("btn-copy-skills");
  if (btnCopySkills) {
    btnCopySkills.addEventListener("click", () => {
      if (currentApplyingJob && currentApplyingJob.skills_required) {
        navigator.clipboard.writeText(currentApplyingJob.skills_required.join(", ")).then(() => {
          btnCopySkills.textContent = "✓ Copied!";
          setTimeout(() => { btnCopySkills.textContent = "Copy Skills"; }, 2000);
        });
      }
    });
  }

  const btnMarkApplied = document.getElementById("btn-apply-mark-applied");
  if (btnMarkApplied) {
    btnMarkApplied.addEventListener("click", async () => {
      if (!currentApplyingJob) return;
      try {
        await fetch("/api/global/tracker", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            job_id: currentApplyingJob.id,
            status: "Applied",
            recruiter_info: currentApplyingJob.company ? currentApplyingJob.company.name : "",
            notes: "Applied via Universal Application Flow (" + (currentResolvedApply ? currentResolvedApply.platform_name : "Direct") + ")",
            score: 0.90
          })
        });
        btnMarkApplied.textContent = "✓ Saved as Applied!";
        loadTrackedJobsCount();
        setTimeout(() => { btnMarkApplied.textContent = "✓ Mark Applied"; }, 2500);
      } catch (e) {
        console.error("Tracker save error:", e);
      }
    });
  }

  const btnMarkPlanning = document.getElementById("btn-apply-mark-planning");
  if (btnMarkPlanning) {
    btnMarkPlanning.addEventListener("click", async () => {
      if (!currentApplyingJob) return;
      try {
        await fetch("/api/global/tracker", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            job_id: currentApplyingJob.id,
            status: "Planning to Apply",
            recruiter_info: currentApplyingJob.company ? currentApplyingJob.company.name : "",
            notes: "Plan to complete application on " + (currentResolvedApply ? currentResolvedApply.platform_name : "Company Portal"),
            score: 0.85
          })
        });
        btnMarkPlanning.textContent = "✓ Saved to Plan!";
        loadTrackedJobsCount();
        setTimeout(() => { btnMarkPlanning.textContent = "📌 Plan to Apply"; }, 2500);
      } catch (e) {
        console.error("Tracker save error:", e);
      }
    });
  }

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
  const tabs = ["nav-tab-explorer", "nav-tab-remote", "nav-tab-country", "nav-tab-recommended", "nav-tab-tracker", "nav-tab-alerts", "nav-tab-source-health", "nav-tab-analytics", "nav-tab-companies", "nav-tab-ai-analytics"];
  const views = ["view-explorer", "view-remote", "view-country", "view-recommended", "view-tracker", "view-alerts", "view-source-health", "view-analytics", "view-companies", "view-ai-analytics"];
  
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
  const sortBy = document.getElementById("filter-sort") ? document.getElementById("filter-sort").value : "recent";
  const candidateOrigin = document.getElementById("candidate-origin") ? document.getElementById("candidate-origin").value : "Bangladesh";
  const skills = document.getElementById("input-skills").value.trim();
  const exp = document.getElementById("input-experience").value;
  const visaOnly = document.getElementById("filter-visa-only") ? document.getElementById("filter-visa-only").checked : false;
  const freshness = document.getElementById("filter-freshness") ? document.getElementById("filter-freshness").value : "";

  const params = new URLSearchParams();
  if (query) params.append("q", query);
  if (country && country !== "Worldwide") params.append("country", country);
  if (workplace && workplace !== "All") params.append("workplace_type", workplace);
  if (sortBy) params.append("sort_by", sortBy);
  if (candidateOrigin) params.append("candidate_origin", candidateOrigin);
  if (skills) params.append("skills", skills);
  if (exp) params.append("experience", exp);
  if (visaOnly) params.append("visa_sponsorship", "true");
  if (freshness) params.append("freshness_days", freshness);
  if (refreshLive) params.append("refresh_live", "true");

  // Salary range filters
  if (salaryState.min > 0) {
    params.append("min_salary", salaryState.min);
  }
  if (salaryState.max > 0) {
    params.append("max_salary", salaryState.max);
  }
  params.append("salary_currency", salaryState.currency);
  params.append("salary_period", salaryState.currency === "USD" ? "Annual" : "Monthly");
  
  if (!activeCompanyFilter) {
    const currentCfg = tabConfig[currentTab];
    if (currentCfg) {
      if (currentCfg.filterType === "category_id" && currentCfg.selectedId) {
        params.append("category_id", currentCfg.selectedId);
      } else if (currentCfg.filterType === "source" && currentCfg.selectedSource) {
        params.append("source", currentCfg.selectedSource);
      }
    }
  }
  params.append("limit", "500");

  try {
    const res = await fetch(`/api/global/search?${params.toString()}`);
    const data = await res.json();
    let results = data.results || [];

    // Filter by candidate eligibility if checkbox is checked
    const eligibleOnly = document.getElementById("filter-eligible-only") ? document.getElementById("filter-eligible-only").checked : false;
    if (eligibleOnly) {
      results = results.filter(r => r.job.candidate_eligibility && r.job.candidate_eligibility.is_eligible);
    }

    // Filter by international applicants if checkbox is checked
    const intlOnly = document.getElementById("filter-intl-only") ? document.getElementById("filter-intl-only").checked : false;
    if (intlOnly) {
      results = results.filter(r => r.job.remote_eligibility && r.job.remote_eligibility.accepts_international);
    }

    loadedJobs = results.map(r => r.job);
    document.getElementById("total-jobs-count").textContent = results.length;
    document.getElementById("current-scope-label").textContent = country === "Worldwide" ? "Worldwide & Bangladesh" : country;

    renderSourceStatus(data);
    renderJobsTable(results, data.search_diagnostics);
  } catch (err) {
    console.error("Error loading jobs:", err);
    document.getElementById("total-jobs-count").textContent = "0";
    const bar = document.getElementById("source-status-bar");
    if (bar) bar.innerHTML = `<span class="source-alert-pill">⚠️ Connection error: Job feeds temporarily unreachable</span>`;
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--accent-rose); padding: 30px;">Failed to load job listings. Please ensure server is running.</td></tr>`;
  }
}

function renderJobsTable(results, diagnostics = null) {
  const tbody = document.getElementById("jobs-table-body");
  if (!results.length) {
    const diag = diagnostics || {};
    const sourcesSearched = diag.sources_queried || 33;
    const sourcesUnavailable = diag.sources_unavailable || 37;
    const totalEvaluated = diag.total_evaluated || loadedJobs.length || 0;
    const matchingTitle = diag.matching_title_or_skills || 0;
    const matchingLoc = diag.matching_location || 0;
    const matchingRemote = diag.matching_remote || 0;

    tbody.innerHTML = `
      <tr>
        <td colspan="8">
          <div class="zero-results-diagnostic">
            <h3>
              <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 8v4m0 4h.01"/></svg>
              No matching jobs found from currently available sources
            </h3>
            <p class="diagnostic-summary">Here is the transparent diagnostic breakdown of your search criteria against live indexed catalog:</p>
            <div class="funnel-grid">
              <div class="funnel-step">
                <span class="step-num">Step 1</span>
                <span class="step-label">Sources Searched</span>
                <strong class="step-val" style="color: #6ee7b7;">${sourcesSearched} Active</strong>
              </div>
              <div class="funnel-step">
                <span class="step-num">Step 2</span>
                <span class="step-label">Unavailable Sources</span>
                <strong class="step-val" style="color: #94a3b8;">${sourcesUnavailable} Skipped</strong>
              </div>
              <div class="funnel-step">
                <span class="step-num">Step 3</span>
                <span class="step-label">Total Jobs Evaluated</span>
                <strong class="step-val" style="color: #a5b4fc;">${totalEvaluated} Listings</strong>
              </div>
              <div class="funnel-step">
                <span class="step-num">Step 4</span>
                <span class="step-label">Matching Title / Skills</span>
                <strong class="step-val">${matchingTitle} Matches</strong>
              </div>
              <div class="funnel-step">
                <span class="step-num">Step 5</span>
                <span class="step-label">Matching Location</span>
                <strong class="step-val">${matchingLoc} Filtered</strong>
              </div>
              <div class="funnel-step">
                <span class="step-num">Step 6</span>
                <span class="step-label">Matching Remote Policy</span>
                <strong class="step-val">${matchingRemote} Passed</strong>
              </div>
            </div>
            <div class="diagnostic-hint-box">
              <strong>Search Guidance:</strong> Try broadening your role keyword (e.g. "Software Engineer" or "Analyst"), clearing strict location filters, or resetting salary bounds. You can inspect all operational endpoints on the <a href="javascript:void(0)" onclick="switchView('nav-tab-source-health', 'view-source-health'); loadSourceHealthView();" style="color: #818cf8; text-decoration: underline; font-weight: 600;">Source Health Dashboard</a>.
            </div>
          </div>
        </td>
      </tr>
    `;
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
          <div class="job-title" style="cursor: pointer;" onclick="openApplyFlowModal('${job.id}')" title="Click to view application flow and details">${escapeHtml(job.title)}</div>
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
          <button type="button" class="apply-btn-direct" onclick="openApplyFlowModal('${job.id}')" title="Launch intelligent application assistant for ${escapeHtml(job.title)}">
            Apply Now ↗
          </button>
        </td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="openTrackModal('${job.id}')">
            📌 Track
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

function renderSourceStatus(data) {
  const bar = document.getElementById("source-status-bar");
  if (!bar) return;

  const sourcesEvaluated = (data && data.sources_evaluated) ? data.sources_evaluated : {};
  const unavailableSources = (data && data.unavailable_sources) ? data.unavailable_sources : [];
  const diagnostics = (data && data.search_diagnostics) ? data.search_diagnostics : null;

  let chipsHtml = `<span class="source-title-label">Evaluated Sources:</span>`;

  const evalEntries = Object.entries(sourcesEvaluated);
  if (evalEntries.length > 0) {
    evalEntries.slice(0, 8).forEach(([srcName, count]) => {
      chipsHtml += `
        <span class="source-chip has-jobs" title="${escapeHtml(srcName)} returned ${count} matching listings">
          <span class="source-dot"></span>
          <span>${escapeHtml(srcName)}</span>
          <span class="source-count">${count}</span>
        </span>
      `;
    });
  } else if (diagnostics) {
    chipsHtml += `
      <span class="source-chip has-jobs" title="Queried ${diagnostics.sources_queried || 33} active global sources">
        <span class="source-dot"></span>
        <span>${diagnostics.sources_queried || 33} Active Connectors</span>
      </span>
    `;
  }

  // Diagnostic Link
  chipsHtml += `
    <button type="button" class="btn btn-secondary btn-xs" onclick="switchView('nav-tab-source-health', 'view-source-health'); loadSourceHealthView();" style="margin-left: auto; display: flex; align-items: center; gap: 4px;" title="Open Source Health & Diagnostic Dashboard">
      <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
      Source Health
    </button>
  `;

  bar.innerHTML = chipsHtml;
}

  bar.innerHTML = chipsHtml;
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

    results.forEach(r => {
      if (r.job && !loadedJobs.some(j => j.id === r.job.id)) loadedJobs.push(r.job);
    });

    container.innerHTML = results.map(({ job, score }) => `
      <div class="job-card">
        <div>
          <div class="job-card-header">
            <div>
              <div class="job-card-title" style="cursor: pointer;" onclick="openApplyFlowModal('${job.id}')" title="Click to view details & application flow">${escapeHtml(job.title)}</div>
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
          <button type="button" class="apply-btn-direct" onclick="openApplyFlowModal('${job.id}')" title="Launch application assistant for ${escapeHtml(job.title)}">
            Apply Now ↗
          </button>
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

    results.forEach(r => {
      if (r.job && !loadedJobs.some(j => j.id === r.job.id)) loadedJobs.push(r.job);
    });

    container.innerHTML = results.map(({ job, score }) => `
      <div class="job-card">
        <div>
          <div class="job-card-header">
            <div>
              <div class="job-card-title" style="cursor: pointer;" onclick="openApplyFlowModal('${job.id}')" title="Click to view details & application flow">${escapeHtml(job.title)}</div>
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
          <button type="button" class="apply-btn-direct" onclick="openApplyFlowModal('${job.id}')" title="Launch application assistant for ${escapeHtml(job.title)}">
            Apply Now ↗
          </button>
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
  const found = loadedJobs.find(j => j.id === jobId);
  const displayTitle = title || (found ? found.title : "Job Opportunity");
  document.getElementById("track-modal-job-id").value = jobId;
  document.getElementById("track-modal-title").textContent = `Track: ${displayTitle}`;
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

// ==================== UNIVERSAL APPLICATION & ATS RESOLVER FLOW ====================

let currentApplyingJob = null;
let currentResolvedApply = null;

async function openApplyFlowModal(jobId) {
  const job = loadedJobs.find(j => j.id === jobId) || null;
  currentApplyingJob = job;

  const modal = document.getElementById("apply-flow-modal");
  if (!modal) return;

  // Set initial placeholders
  document.getElementById("apply-job-title").textContent = job ? job.title : "Job Application";
  document.getElementById("apply-job-company").textContent = (job && job.company) ? job.company.name : "";
  document.getElementById("apply-job-location").textContent = job ? (job.location || job.country) : "";
  document.getElementById("apply-job-salary").textContent = (job && job.salary) ? job.salary.raw_text : "Disclosed on portal";
  
  const badgeContainer = document.getElementById("apply-type-badge-container");
  badgeContainer.innerHTML = `<span class="badge badge-primary">ANALYZING DESTINATION...</span>`;
  
  const alertBox = document.getElementById("apply-alert-box");
  alertBox.style.display = "none";
  
  const stepsList = document.getElementById("apply-steps-list");
  stepsList.innerHTML = `<li style="color: var(--text-muted);">Detecting platform flow, ATS signatures, and authentication steps...</li>`;
  
  const skillsContainer = document.getElementById("apply-skills-tags");
  const skills = (job && job.skills_required) ? job.skills_required : [];
  skillsContainer.innerHTML = skills.map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join("");

  document.getElementById("apply-preserved-pitch").value = "Drafting tailored application note based on role requirements...";
  document.getElementById("apply-canonical-url-text").textContent = job ? job.apply_url : "Resolving canonical destination...";

  const proceedBtn = document.getElementById("btn-proceed-application");
  proceedBtn.href = job ? job.apply_url : "#";

  modal.classList.add("show");

  try {
    const res = await fetch("/api/apply/resolve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_id: jobId,
        apply_url: job ? job.apply_url : "",
        title: job ? job.title : "",
        company: (job && job.company) ? job.company.name : "",
        location: job ? (job.location || job.country) : "",
        skills: skills,
        source: job ? job.source : "Global"
      })
    });

    if (!res.ok) throw new Error("Could not resolve application flow");
    const data = await res.json();
    currentResolvedApply = data;

    // Platform Name & Title
    document.getElementById("apply-platform-name").textContent = data.platform_name || "Official Platform";
    document.getElementById("apply-canonical-url-text").textContent = data.canonical_url;
    proceedBtn.href = data.canonical_url;

    // Platform Icon
    const iconEl = document.getElementById("apply-modal-platform-icon");
    if (data.application_type === "EXTERNAL_ATS") {
      iconEl.textContent = "⚙️";
    } else if (data.application_type === "DIRECT_JOB_BOARD") {
      iconEl.textContent = "⚡";
    } else if (data.application_type === "QUICK_APPLY") {
      iconEl.textContent = "✉️";
    } else {
      iconEl.textContent = "🏢";
    }

    // Type Badge
    let typeClass = "badge-primary";
    if (data.application_type === "EXTERNAL_ATS") typeClass = "badge-accent";
    if (data.application_type === "QUICK_APPLY") typeClass = "badge-success";
    badgeContainer.innerHTML = `<span class="badge ${typeClass}">${data.application_type.replace(/_/g, " ")}: ${data.platform_name.toUpperCase()}</span>`;

    // Alert Banner (Auth, CAPTCHA, or BDJobs exclusion notice)
    if (data.notice) {
      alertBox.className = "apply-alert-banner alert-bdjobs-filtered";
      document.getElementById("apply-alert-icon").textContent = "🛡️";
      document.getElementById("apply-alert-text").textContent = data.notice;
      alertBox.style.display = "flex";
    } else if (data.auth_requirement === "AUTH_REQUIRED") {
      alertBox.className = "apply-alert-banner alert-auth";
      document.getElementById("apply-alert-icon").textContent = "🔐";
      document.getElementById("apply-alert-text").textContent = data.auth_details || "Candidate sign-in or account registration required on this platform.";
      alertBox.style.display = "flex";
    } else if (data.auth_requirement === "CAPTCHA_CHECK") {
      alertBox.className = "apply-alert-banner alert-captcha";
      document.getElementById("apply-alert-icon").textContent = "🛡️";
      document.getElementById("apply-alert-text").textContent = data.auth_details || "Security check/CAPTCHA required.";
      alertBox.style.display = "flex";
    } else {
      alertBox.style.display = "none";
    }

    // Render Steps
    stepsList.innerHTML = (data.steps || []).map(step => `<li>${escapeHtml(step)}</li>`).join("");

    // Pitch & Preserved Data
    if (data.preserved_payload && data.preserved_payload.tailored_pitch) {
      document.getElementById("apply-preserved-pitch").value = data.preserved_payload.tailored_pitch;
    }

  } catch (err) {
    console.error("Apply resolution error:", err);
    badgeContainer.innerHTML = `<span class="badge badge-primary">DIRECT APPLICATION</span>`;
    stepsList.innerHTML = `
      <li>Open original job posting and review requirements.</li>
      <li>Upload your CV and submit directly on the destination website.</li>
    `;
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

// ==================== AI JOB MARKET ANALYTICS (v4.0) ====================

async function loadAiMarketAnalyticsView() {
  try {
    // Setup smooth scrolling for subnav links
    document.querySelectorAll(".ai-subnav-link").forEach(link => {
      if (!link.dataset.bound) {
        link.dataset.bound = "true";
        link.addEventListener("click", (e) => {
          e.preventDefault();
          const targetId = link.getAttribute("href");
          const targetEl = document.querySelector(targetId);
          if (targetEl) {
            targetEl.scrollIntoView({ behavior: "smooth", block: "start" });
            document.querySelectorAll(".ai-subnav-link").forEach(l => l.classList.remove("active"));
            link.classList.add("active");
          }
        });
      }
    });

    const res = await fetch("/api/analytics/ai-market");
    if (!res.ok) return;
    const data = await res.json();
    if (!data || !data.overview) return;

    const ov = data.overview;
    const setTxt = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    };

    setTxt("ai-kpi-jobs", Number(ov.total_job_postings_analyzed || 34979).toLocaleString());
    setTxt("ai-kpi-salaries", Number(ov.total_salary_benchmarks_analyzed || 71913).toLocaleString());
    setTxt("ai-kpi-median-salary", `$${Number(ov.median_salary_usd || 138750).toLocaleString()}`);
    setTxt("ai-kpi-remote-share", `${Number(ov.remote_jobs_percentage || 11.79).toFixed(1)}%`);
    setTxt("ai-kpi-companies", Number(ov.unique_companies || 18758).toLocaleString());
    setTxt("ai-kpi-countries", `${ov.unique_countries || 145}+`);
  } catch (err) {
    console.error("Error loading AI market analytics:", err);
  }
}

// ==================== TAXONOMY & HELPERS ====================

function updateStatusFooter() {
  const cfg = tabConfig[currentTab] || tabConfig["Functional"];
  const labelEl = document.getElementById("cat-footer-label");
  const displayEl = document.getElementById("active-category-display");
  const hintEl = document.getElementById("cat-footer-hint");
  
  if (labelEl) labelEl.textContent = cfg.label;
  if (displayEl) displayEl.textContent = cfg.selectedName;
  if (hintEl) hintEl.textContent = cfg.hint;
}

async function loadTaxonomy() {
  try {
    const res = await fetch("/api/taxonomy");
    currentTaxonomy = await res.json();

    const funcCount = (currentTaxonomy.categories || []).filter(c => c.type === "Functional").length;
    const specCount = (currentTaxonomy.categories || []).filter(c => c.type === "Special Skilled").length;

    const tabFunc = document.getElementById("tab-functional");
    if (tabFunc) tabFunc.textContent = `Functional Roles (${funcCount || 31})`;

    const tabSpec = document.getElementById("tab-special");
    if (tabSpec) tabSpec.textContent = `Special Skilled (${specCount || 33})`;

    const tabGlobal = document.getElementById("tab-global-sources");
    if (tabGlobal) tabGlobal.textContent = `Global Connectors (${GLOBAL_CONNECTORS.length})`;

    renderCategoryChips();
  } catch (err) {
    console.error("Error loading taxonomy:", err);
  }
}

function switchTab(tabName) {
  currentTab = tabName;
  activeCompanyFilter = null;

  document.getElementById("tab-functional").classList.toggle("active", tabName === "Functional");
  document.getElementById("tab-special").classList.toggle("active", tabName === "Special Skilled");
  const tabGlobal = document.getElementById("tab-global-sources");
  if (tabGlobal) tabGlobal.classList.toggle("active", tabName === "Global");
  
  const searchInput = document.getElementById("category-search");
  if (searchInput) searchInput.value = "";

  renderCategoryChips();
  loadJobs();
}

function renderCategoryChips(searchFilter = "") {
  const container = document.getElementById("category-chips-container");
  if (!container) return;

  let categories = [];
  let allLabel = "All Sectors";
  if (currentTab === "Global") {
    categories = [...GLOBAL_CONNECTORS];
    allLabel = "All Sources";
  } else if (currentTab === "Special Skilled") {
    categories = (currentTaxonomy.categories || []).filter(c => c.type === currentTab);
    allLabel = "All Skills";
  } else {
    categories = (currentTaxonomy.categories || []).filter(c => c.type === currentTab);
    allLabel = "All Sectors";
  }

  if (searchFilter) {
    const q = searchFilter.toLowerCase();
    categories = categories.filter(c => c.name.toLowerCase().includes(q));
  }

  const currentSelectedId = tabConfig[currentTab] ? tabConfig[currentTab].selectedId : null;
  const isAllActive = (currentSelectedId === null);

  let chipsHtml = `
    <div class="cat-chip ${isAllActive ? 'active' : ''}" data-id="all" data-name="${allLabel}" onclick="selectCategory(null, '${allLabel}')">
      <span>${allLabel}</span>
    </div>
  `;

  chipsHtml += categories.map(cat => {
    const count = (cat.active_jobs !== undefined && cat.active_jobs !== null) ? cat.active_jobs : (cat.job_count || '');
    const isActive = (currentSelectedId !== null && cat.id === currentSelectedId);
    return `
      <div class="cat-chip ${isActive ? 'active' : ''}" data-id="${cat.id}" data-name="${escapeHtml(cat.name)}" onclick="selectCategory(${cat.id}, this.getAttribute('data-name'))">
        <span>${escapeHtml(cat.name)}</span>
        ${count ? `<span class="cat-count">${count}</span>` : ''}
      </div>
    `;
  }).join("");

  container.innerHTML = chipsHtml;
  updateStatusFooter();
}

function selectCategory(catId, catName) {
  const cfg = tabConfig[currentTab];
  if (!cfg) return;

  // Toggle off to All if already selected
  if (cfg.selectedId === catId && catId !== null) {
    const defaultName = currentTab === "Functional" ? "All Sectors" : (currentTab === "Special Skilled" ? "All Skills" : "All Global & BD Sources");
    selectCategory(null, defaultName);
    return;
  }

  cfg.selectedId = catId;
  activeCompanyFilter = null;

  if (catId === null) {
    cfg.selectedName = catName || (currentTab === "Functional" ? "All Sectors" : (currentTab === "Special Skilled" ? "All Skills" : "All Global & BD Sources"));
    cfg.selectedSource = null;
  } else if (currentTab === "Global") {
    const conn = GLOBAL_CONNECTORS.find(c => c.id === catId);
    if (conn) {
      cfg.selectedName = conn.name;
      cfg.selectedSource = conn.source;
    } else if (catName) {
      cfg.selectedName = catName;
    }
  } else {
    if (catName) {
      cfg.selectedName = catName;
    } else {
      const found = (currentTaxonomy.categories || []).find(c => c.id === catId);
      if (found) cfg.selectedName = found.name;
    }
  }

  updateStatusFooter();

  const container = document.getElementById("category-chips-container");
  if (container) {
    container.querySelectorAll(".cat-chip").forEach(chip => {
      const chipIdAttr = chip.getAttribute("data-id");
      if (catId === null) {
        chip.classList.toggle("active", chipIdAttr === "all");
      } else {
        const chipId = parseInt(chipIdAttr, 10);
        chip.classList.toggle("active", chipId === catId);
      }
    });
  }

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
  const platform = document.getElementById("paste-source-select") ? document.getElementById("paste-source-select").value : "linkedin";
  
  if (!text) {
    alert("Please paste the job text or JSON-LD first.");
    return;
  }

  const endpoint = platform === "facebook" ? "/api/ingest/facebook" : "/api/ingest/linkedin";

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: text,
        target_category_id: tabConfig["Functional"].selectedId || 8
      })
    });
    if (!res.ok) throw new Error(`Could not parse job from pasted ${platform === "facebook" ? "Facebook" : "LinkedIn"} text.`);
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

async function loadCompaniesView() {
  const container = document.getElementById("companies-cards-container");
  if (!container) return;

  const q = document.getElementById("company-filter-input") ? document.getElementById("company-filter-input").value.trim() : "";
  const sort = document.getElementById("company-sort-select") ? document.getElementById("company-sort-select").value : "name";

  container.innerHTML = `<div class="loading-container" style="grid-column: 1 / -1;"><div class="loader-spinner"></div><p style="margin-top: 10px;">Loading verified company directory...</p></div>`;

  try {
    const params = new URLSearchParams();
    if (q) params.append("q", q);
    if (sort) params.append("sort_by", sort);

    const res = await fetch(`/api/companies?${params.toString()}`);
    const data = await res.json();
    const companies = data.companies || [];

    const countEl = document.getElementById("companies-count");
    if (countEl) countEl.textContent = companies.length;

    if (companies.length === 0) {
      container.innerHTML = `<div class="empty-state" style="grid-column: 1 / -1;"><p>No companies found matching your query.</p></div>`;
      return;
    }

    container.innerHTML = companies.map(c => `
      <div class="glass-card job-card" style="display: flex; flex-direction: column; justify-content: space-between;">
        <div>
          <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; margin-bottom: 8px;">
            <h3 style="font-size: 16px; font-weight: 700; color: #fff; margin: 0;">${escapeHtml(c.name)}</h3>
            <span class="company-tier tier-${(c.tier || 'sme').toLowerCase().replace(/[^a-z]/g, '-')}">${escapeHtml(c.tier || 'Corporate')}</span>
          </div>
          <div style="font-size: 12px; color: var(--accent-indigo); font-weight: 500; margin-bottom: 8px;">
            ${escapeHtml(c.industry || 'Technology')}
          </div>
          <div style="font-size: 12.5px; color: var(--text-secondary); margin-bottom: 12px; line-height: 1.5;">
            <strong>Typical Roles:</strong> ${escapeHtml((c.typical_roles || []).join(', '))}
          </div>
          <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px;">
            <span class="badge" style="background: rgba(99, 102, 241, 0.12); color: #a5b4fc; font-size: 11px;">📍 ${escapeHtml(c.location || 'Remote')}</span>
            <span class="badge" style="background: rgba(16, 185, 129, 0.12); color: #6ee7b7; font-size: 11px;">💼 ${escapeHtml(c.workplace_type || 'Remote')}</span>
            ${c.salary_range && c.salary_range !== 'not verified' ? `<span class="badge" style="background: rgba(245, 158, 11, 0.12); color: #fcd34d; font-size: 11px; font-weight: 600;">💰 ${escapeHtml(c.salary_range)}</span>` : `<span class="badge" style="background: rgba(100, 116, 139, 0.15); color: #94a3b8; font-size: 11px;">Salary: not verified</span>`}
          </div>
        </div>
        <div style="display: flex; gap: 8px; border-top: 1px solid var(--border-subtle); padding-top: 12px;">
          <a href="${c.careers_url && c.careers_url !== 'not verified' ? c.careers_url : c.website}" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-sm" style="flex: 1; text-align: center; text-decoration: none;">
            Official Careers ↗
          </a>
          <button class="btn btn-secondary btn-sm company-search-btn" data-company="${escapeHtml(c.name)}" style="flex: 1;">
            Search Openings
          </button>
        </div>
      </div>
    `).join("");

    if (!container._hasClickDelegate) {
      container.addEventListener("click", (e) => {
        const btn = e.target.closest(".company-search-btn");
        if (btn) {
          const compName = btn.getAttribute("data-company");
          if (compName) filterByCompany(compName);
        }
      });
      container._hasClickDelegate = true;
    }
  } catch (err) {
    container.innerHTML = `<div class="error-box" style="grid-column: 1 / -1;">Error loading companies: ${err.message}</div>`;
  }
}

function filterByCompany(companyName) {
  switchView("nav-tab-explorer", "view-explorer");
  const input = document.getElementById("global-search-input");
  if (input) {
    input.value = companyName;
  }
  activeCompanyFilter = companyName;
  const countrySelect = document.getElementById("filter-country");
  if (countrySelect) countrySelect.value = "Worldwide";
  loadJobs();
}

// ==================== SOURCE HEALTH DASHBOARD (Section 10 & 16) ====================
let currentHealthSources = [];

async function loadSourceHealthTabBadge() {
  try {
    const res = await fetch("/api/sources/health");
    if (!res.ok) return;
    const data = await res.json();
    const countEl = document.getElementById("active-sources-tab-count");
    if (countEl) countEl.textContent = data.active_sources_count || 33;
  } catch (e) {}
}

async function loadSourceHealthView() {
  const tbody = document.getElementById("sources-health-tbody");
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="9" class="loading-container"><div class="loader-spinner"></div><p style="margin-top: 10px;">Querying live health metrics across all 70 registered sources...</p></td></tr>`;

  try {
    const res = await fetch("/api/sources/health");
    const data = await res.json();

    const elTotal = document.getElementById("health-total-sources");
    const elActive = document.getElementById("health-active-sources");
    const elPartial = document.getElementById("health-partial-sources");
    const elUnavail = document.getElementById("health-unavailable-sources");
    const elIngested = document.getElementById("health-jobs-ingested");
    const elDeduped = document.getElementById("health-jobs-deduped");
    const tabCount = document.getElementById("active-sources-tab-count");

    if (elTotal) elTotal.textContent = data.total_registered_sources || 70;
    if (elActive) elActive.textContent = data.active_sources_count || 0;
    if (elPartial) elPartial.textContent = data.partial_sources_count || 0;
    if (elUnavail) elUnavail.textContent = data.unavailable_sources_count || 0;
    if (elIngested) elIngested.textContent = data.total_jobs_ingested || 0;
    if (elDeduped) elDeduped.textContent = data.total_jobs_deduped || 0;
    if (tabCount) tabCount.textContent = data.active_sources_count || 0;

    currentHealthSources = data.sources || [];
    const activeBtn = document.querySelector(".source-cat-btn.active");
    const activeCat = activeBtn ? activeBtn.getAttribute("data-cat") : "ALL";
    renderSourceHealthTable(activeCat);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--accent-rose); padding: 30px;">Error retrieving source health telemetry: ${escapeHtml(err.message)}</td></tr>`;
  }
}

function renderSourceHealthTable(categoryFilter = "ALL") {
  const tbody = document.getElementById("sources-health-tbody");
  if (!tbody) return;

  let sources = currentHealthSources;
  if (categoryFilter && categoryFilter !== "ALL") {
    sources = sources.filter(s => s.category === categoryFilter);
  }

  if (!sources.length) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 30px;">No sources registered under this category.</td></tr>`;
    return;
  }

  tbody.innerHTML = sources.map(s => {
    let badgeClass = "status-badge-unavailable";
    if (s.status === "ACTIVE") badgeClass = "status-badge-active";
    else if (s.status === "PARTIAL") badgeClass = "status-badge-partial";
    else if (s.status === "ERROR") badgeClass = "status-badge-error";

    const lastSuccessTime = s.last_success ? new Date(s.last_success).toLocaleTimeString() : '<span style="color: var(--text-muted);">-</span>';
    const httpCode = s.http_status ? `<span class="badge" style="background: rgba(255,255,255,0.06); font-family: monospace;">${s.http_status}</span>` : '<span style="color: var(--text-muted);">-</span>';
    const errorMsg = s.last_error ? `<span style="color: #fb7185; font-size: 11px;">${escapeHtml(s.last_error)}</span>` : (s.status === "ACTIVE" ? '<span style="color: #34d399; font-size: 11px;">✓ Operational & verified</span>' : '<span style="color: var(--text-muted); font-size: 11px;">No live API adapter registered</span>');

    return `
      <tr>
        <td>
          <div style="font-weight: 600; color: #fff;">${escapeHtml(s.name)}</div>
          <div style="font-size: 10.5px; color: var(--text-muted); font-family: monospace;">${escapeHtml(s.id)}</div>
        </td>
        <td>
          <span style="font-size: 12px; color: #cbd5e1;">${escapeHtml(s.category)}</span>
          <div style="font-size: 10px; color: var(--accent-indigo);">${escapeHtml(s.region)}</div>
        </td>
        <td>
          <span class="badge" style="background: rgba(99, 102, 241, 0.15); color: #a5b4fc; font-size: 10.5px;">${escapeHtml(s.type)}</span>
          <div style="font-size: 10px; color: var(--text-muted); margin-top: 2px;">${escapeHtml(s.access_method)}</div>
        </td>
        <td>
          <span class="status-badge ${badgeClass}">
            <span class="status-dot-pulse"></span>
            ${escapeHtml(s.status)}
          </span>
        </td>
        <td style="font-weight: 600; color: #fff;">${s.jobs_found || 0}</td>
        <td style="font-weight: 600; color: #38bdf8;">${s.jobs_deduped || 0}</td>
        <td>${httpCode}</td>
        <td style="font-size: 11.5px; color: #cbd5e1;">${lastSuccessTime}</td>
        <td>${errorMsg}</td>
      </tr>
    `;
  }).join("");
}

async function triggerIngestionPipeline() {
  const btn = document.getElementById("btn-trigger-pipeline");
  const banner = document.getElementById("pipeline-status-banner");
  if (btn) btn.disabled = true;
  if (banner) {
    banner.style.display = "block";
    banner.style.background = "rgba(99, 102, 241, 0.15)";
    banner.style.border = "1px solid rgba(99, 102, 241, 0.4)";
    banner.style.color = "#c7d2fe";
    banner.innerHTML = `<span class="loader-spinner" style="display: inline-block; width: 14px; height: 14px; vertical-align: middle; margin-right: 8px;"></span> Harvesting live jobs across registered sources in parallel...`;
  }

  try {
    const res = await fetch("/api/ingest/run?limit=50&workers=8", { method: "POST" });
    const data = await res.json();
    const sum = data.summary || {};
    if (banner) {
      banner.style.background = "rgba(16, 185, 129, 0.15)";
      banner.style.border = "1px solid rgba(16, 185, 129, 0.4)";
      banner.style.color = "#6ee7b7";
      banner.innerHTML = `✓ Ingestion completed: Harvested <strong>${sum.total_raw_jobs || 0}</strong> raw jobs across <strong>${sum.sources_active || 0}</strong> active sources, removed <strong>${sum.duplicates_removed || 0}</strong> duplicates in <strong>${sum.elapsed_seconds || 0}s</strong>.`;
    }
    await loadSourceHealthView();
    await loadJobs();
  } catch (err) {
    if (banner) {
      banner.style.background = "rgba(244, 63, 94, 0.15)";
      banner.style.border = "1px solid rgba(244, 63, 94, 0.4)";
      banner.style.color = "#fda4af";
      banner.textContent = `Ingestion error: ${err.message}`;
    }
  } finally {
    if (btn) btn.disabled = false;
  }
}


