const EXTERNAL_ICON = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>`;

async function analyzeTravel() {
  const destText = document.getElementById("destination-input").value.trim();
  const datesText = document.getElementById("dates-input").value.trim();

  if (!destText) {
    showError("Please describe the travel destination before generating a report.");
    return;
  }

  setLoading(true);
  hideError();

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ destination_text: destText, dates_text: datesText }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error ${res.status}`);
    }

    const data = await res.json();
    renderResults(data);
  } catch (err) {
    showError(err.message || "An unexpected error occurred.");
  } finally {
    setLoading(false);
  }
}

function setLoading(on) {
  const btn = document.getElementById("analyze-btn");
  const text = document.getElementById("btn-text");
  const spinner = document.getElementById("btn-spinner");
  btn.disabled = on;
  text.textContent = on ? "Fetching intelligence…" : "Generate Risk Intelligence";
  spinner.classList.toggle("hidden", !on);
}

function showError(msg) {
  const el = document.getElementById("error-banner");
  el.textContent = msg;
  el.classList.remove("hidden");
}

function hideError() {
  document.getElementById("error-banner").classList.add("hidden");
}

function renderResults(data) {
  const { parsed, sources } = data;

  // Destination header
  const header = document.getElementById("destination-header");
  const city = parsed.city ? `<div class="dest-city">${parsed.city}</div>` : "";
  const region = parsed.region ? `<div class="dest-region">${parsed.region}</div>` : "";
  const context = parsed.context?.purpose
    ? `<div class="dest-context">${parsed.context.purpose}${parsed.context.notes ? " · " + parsed.context.notes : ""}</div>`
    : "";

  let datesHtml = "";
  const d = parsed.dates || {};
  if (d.departure || d.return) {
    const dep = d.departure ? fmt(d.departure) : "—";
    const ret = d.return ? fmt(d.return) : "—";
    datesHtml = `<div class="dest-dates">${dep} → ${ret}</div>`;
  }
  const durHtml = d.duration_days
    ? `<div class="dest-duration">${d.duration_days} day${d.duration_days !== 1 ? "s" : ""}</div>`
    : "";

  header.innerHTML = `
    <div class="dest-main">
      <div class="dest-country">${parsed.country || "Unknown destination"}</div>
      ${city}${region}${context}
    </div>
    <div class="dest-meta">${datesHtml}${durHtml}</div>
  `;

  // Source cards
  const grid = document.getElementById("sources-grid");
  grid.innerHTML = "";

  grid.appendChild(renderStateDept(sources.state_dept));
  grid.appendChild(renderFcdo(sources.fcdo));
  grid.appendChild(renderCdc(sources.cdc));
  grid.appendChild(renderWho(sources.who));
  grid.appendChild(renderReliefweb(sources.reliefweb));
  grid.appendChild(renderAcled(sources.acled));

  document.getElementById("results").classList.remove("hidden");
  document.getElementById("results").scrollIntoView({ behavior: "smooth", block: "start" });
}

// ── Source renderers ──────────────────────────────────────────────

function renderStateDept(s) {
  const card = makeCard("US Department of State", s?.url, s?.last_updated);

  if (!s?.available) return unavailableCard(card, s, "US Department of State", s?.url);

  let levelHtml = "";
  if (s.level) {
    const bg = s.level_color || "#64748b";
    levelHtml = `
      <div class="level-badge" style="background:${bg}20; color:${bg}; border: 1px solid ${bg}40;">
        <span class="level-num" style="background:${bg}; color:#fff;">Level ${s.level}</span>
        ${s.level_text}
      </div>`;
  }

  const summary = s.summary
    ? `<div class="card-summary">${truncate(s.summary, 600)}</div>`
    : `<div class="no-data">Summary not available.</div>`;

  card.querySelector(".card-body").innerHTML = levelHtml + summary;
  return card;
}

function renderFcdo(s) {
  const card = makeCard("UK FCDO", s?.url, s?.last_updated);

  if (!s?.available) return unavailableCard(card, s, "UK FCDO", s?.url);

  const sections = (s.sections || []).map(sec => `
    <div class="fcdo-section">
      <div class="fcdo-section-title">${sec.title}</div>
      <div class="fcdo-section-text">${truncate(sec.text, 400)}</div>
    </div>
  `).join("");

  card.querySelector(".card-body").innerHTML = sections || `<div class="no-data">No sections returned.</div>`;
  return card;
}

function renderCdc(s) {
  const card = makeCard("US CDC — Traveler Health", s?.url, null);

  if (!s?.available) return unavailableCard(card, s, "US CDC", s?.url);

  let html = "";

  if (s.notices?.length) {
    html += `<div>
      <div class="card-section-title">Health Notices</div>
      ${s.notices.map(n => `<div class="alert-item"><div class="alert-title">${n}</div></div>`).join("")}
    </div>`;
  }

  if (s.vaccines?.length) {
    html += `<div>
      <div class="card-section-title">Vaccines & Medications</div>
      <div class="tag-list">${s.vaccines.map(v => `<span class="tag">${v}</span>`).join("")}</div>
    </div>`;
  }

  if (s.summary) {
    html += `<div class="card-summary">${truncate(s.summary, 500)}</div>`;
  }

  card.querySelector(".card-body").innerHTML = html || `<div class="no-data">No data returned for this destination.</div>`;
  return card;
}

function renderWho(s) {
  const card = makeCard("WHO — Disease Outbreak News", s?.url, null);

  if (!s?.available) return unavailableCard(card, s, "WHO", s?.url);

  const alerts = s.alerts || [];
  let html = "";

  if (alerts.length === 0) {
    html = `<div class="no-data">No active disease outbreak alerts found for this destination.</div>`;
  } else {
    html = alerts.map(a => `
      <div class="alert-item">
        <div class="alert-title"><a href="${a.url}" target="_blank" rel="noopener">${a.title}</a></div>
        <div class="alert-date">${a.date ? fmtRaw(a.date) : ""}</div>
        ${a.summary ? `<div class="report-snippet" style="margin-top:4px">${truncate(a.summary, 250)}</div>` : ""}
      </div>
    `).join("");

    if (s.total_found > alerts.length) {
      html += `<div class="no-data">+${s.total_found - alerts.length} more alerts — <a href="${s.url}" target="_blank">view all</a></div>`;
    }
  }

  card.querySelector(".card-body").innerHTML = html;
  return card;
}

function renderReliefweb(s) {
  const card = makeCard("ReliefWeb (UN OCHA)", s?.url, null);

  if (!s?.available) return unavailableCard(card, s, "ReliefWeb", s?.url);

  const reports = s.reports || [];
  let html = "";

  if (reports.length === 0) {
    html = `<div class="no-data">No recent situation reports found.</div>`;
  } else {
    html = reports.map(r => `
      <div class="report-item">
        <div class="report-title"><a href="${r.url}" target="_blank" rel="noopener">${r.title}</a></div>
        <div class="report-meta">${r.date || ""}${r.sources?.length ? " · " + r.sources.join(", ") : ""}</div>
        ${r.snippet ? `<div class="report-snippet">${truncate(r.snippet, 220)}</div>` : ""}
      </div>
    `).join("");

    if (s.total_found > reports.length) {
      html += `<div class="no-data" style="margin-top:8px">${s.total_found} total reports — <a href="${s.url}" target="_blank">browse all</a></div>`;
    }
  }

  card.querySelector(".card-body").innerHTML = html;
  return card;
}

function renderAcled(s) {
  const card = makeCard("ACLED — Conflict & Security Events", s?.url, null);

  if (!s?.available) return unavailableCard(card, s, "ACLED", s?.url);

  let html = "";

  // Stats row
  html += `
    <div class="stats-row">
      <div class="stat-block">
        <div class="stat-value">${s.total_events ?? "—"}</div>
        <div class="stat-label">Events (180 days)</div>
      </div>
      <div class="stat-block">
        <div class="stat-value">${s.total_fatalities ?? "—"}</div>
        <div class="stat-label">Fatalities</div>
      </div>
    </div>`;

  // By event type
  if (s.by_type && Object.keys(s.by_type).length) {
    html += `<div>
      <div class="card-section-title">By Event Type</div>
      <div class="event-summary-bars">
        ${Object.entries(s.by_type).sort((a, b) => b[1] - a[1]).map(([type, count]) => `
          <div class="event-bar">
            <span class="event-bar-label">${type}</span>
            <span class="event-bar-count">${count}</span>
          </div>
        `).join("")}
      </div>
    </div>`;
  }

  // Recent events
  if (s.recent_events?.length) {
    html += `<div>
      <div class="card-section-title">Recent Events</div>
      ${s.recent_events.map(ev => `
        <div class="event-item" style="margin-bottom:8px">
          <span class="event-type-tag">${ev.type}</span>
          <div class="event-location">${ev.date}${ev.location ? " · " + ev.location : ""}</div>
          ${ev.actors ? `<div class="event-actors">${ev.actors}</div>` : ""}
          ${ev.fatalities ? `<div class="event-fatalities">${ev.fatalities} fatality${ev.fatalities !== 1 ? "ies" : ""}</div>` : ""}
          ${ev.notes ? `<div class="event-notes">${truncate(ev.notes, 200)}</div>` : ""}
        </div>
      `).join("")}
    </div>`;
  }

  if (s.period) {
    html += `<div class="no-data">Period: ${s.period}</div>`;
  }

  card.querySelector(".card-body").innerHTML = html;
  return card;
}

// ── Helpers ──────────────────────────────────────────────────────

function makeCard(sourceName, url, lastUpdated) {
  const card = document.createElement("div");
  card.className = "source-card";

  const updatedHtml = lastUpdated ? `<span class="card-updated">Updated ${lastUpdated}</span>` : "";
  const footerHtml = url
    ? `<div class="card-footer"><a class="source-link" href="${url}" target="_blank" rel="noopener">View live source ${EXTERNAL_ICON}</a></div>`
    : "";

  card.innerHTML = `
    <div class="card-header">
      <span class="card-source-name">${sourceName}</span>
      ${updatedHtml}
    </div>
    <div class="card-body"></div>
    ${footerHtml}
  `;
  return card;
}

function unavailableCard(card, s, name, url) {
  card.classList.add("card-unavailable");
  const registerLink = url ? `<a href="${url}" target="_blank" rel="noopener">Register / view source</a>` : "";
  card.querySelector(".card-body").innerHTML = `
    <div class="unavailable-msg">
      <strong>${name} unavailable</strong>
      ${s?.error ? s.error : "Could not retrieve data."}
      ${registerLink ? `<br/><br/>${registerLink}` : ""}
    </div>`;
  return card;
}

function truncate(str, max) {
  if (!str) return "";
  if (str.length <= max) return str;
  return str.slice(0, max).replace(/\s+\S*$/, "") + "…";
}

function fmt(iso) {
  if (!iso) return "";
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function fmtRaw(str) {
  try {
    return new Date(str).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return str;
  }
}

// Allow Ctrl+Enter to submit
document.addEventListener("keydown", e => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") analyzeTravel();
});
