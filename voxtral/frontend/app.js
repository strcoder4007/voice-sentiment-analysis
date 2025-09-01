/**
 * Voxtral Frontend
 * - Upload audio
 * - Analyze (POST /api/analyze)
 * - Render analysis result with actionable sections
 * - Auto-hide empty sections
 * - Quick navigation chips
 * - Raw JSON viewer and copy buttons
 */

const API_BASE = "http://localhost:8002";

// DOM helpers
const byId = (id) => document.getElementById(id);
const el = (tag, opts = {}) => {
  const e = document.createElement(tag);
  if (opts.className) e.className = opts.className;
  if (opts.text) e.textContent = opts.text;
  if (opts.html) e.innerHTML = opts.html;
  if (opts.attrs) Object.entries(opts.attrs).forEach(([k, v]) => e.setAttribute(k, v));
  return e;
};
const clear = (node) => {
  node.innerHTML = "";
};
const show = (node, on) => node.classList.toggle("hidden", !on);
const toPercent = (v) => (typeof v === "number" ? `${Math.round(v * 100)}%` : "");
const sentimentClass = (s) => (s ? `sentiment-${String(s).toLowerCase().replace(/\s+/g, "_")}` : "");
const satisfactionClass = (s) => (s ? `satisfaction-${String(s).toLowerCase().replace(/\s+/g, "_")}` : "");
const pill = (text, classes = [], dotColor) => {
  const t = document.getElementById("pillTemplate");
  const p = t ? t.content.firstElementChild.cloneNode(true) : el("span", { className: "pill" });
  p.textContent = text;
  classes.forEach((c) => p.classList.add(c));
  if (dotColor) {
    const dot = el("span", { className: "dot" });
    dot.style.background = dotColor;
    p.prepend(dot);
  }
  return p;
};
const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
};
const nonEmptyArray = (arr) => Array.isArray(arr) && arr.length > 0;

const formatDuration = (totalSeconds) => {
  if (typeof totalSeconds !== "number" || !isFinite(totalSeconds) || totalSeconds <= 0) return "";
  const sec = Math.round(totalSeconds);
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  const pad = (n) => String(n).padStart(2, "0");
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
};

// Global state
let currentData = null;

// Renderers
function renderOverview(data) {
  const container = byId("overview");
  clear(container);

  // Determine if any overview data exists
  const hasOverview =
    !!data.emotion_overall ||
    typeof data.emotion_confidence === "number" ||
    !!data.satisfaction ||
    typeof data.satisfaction_confidence === "number" ||
    !!data.agent_speaker_label ||
    typeof data.agent_identification_confidence === "number";

  if (!hasOverview) {
    show(container, false);
    return false;
  }

  show(container, true);
  const title = el("div", { className: "section-title" });
  title.appendChild(el("h2", { text: "Overview" }));
  container.appendChild(title);

  const grid = el("div", { className: "overview-grid" });

  // Emotion
  if (data.emotion_overall) {
    const card = el("div", { className: "row" });
    card.appendChild(pill(`Emotion: ${data.emotion_overall}`, ["nowrap", sentimentClass(data.emotion_overall)]));
    if (typeof data.emotion_confidence === "number") {
      card.appendChild(pill(`Conf: ${toPercent(data.emotion_confidence)}`, ["mono", "faded"]));
    }
    grid.appendChild(card);
  }

  // Satisfaction
  if (data.satisfaction) {
    const card = el("div", { className: "row" });
    card.appendChild(pill(`Satisfaction: ${data.satisfaction}`, ["nowrap", satisfactionClass(data.satisfaction)]));
    if (typeof data.satisfaction_confidence === "number") {
      card.appendChild(pill(`Conf: ${toPercent(data.satisfaction_confidence)}`, ["mono", "faded"]));
    }
    grid.appendChild(card);
  }

  // Agent speaker
  if (data.agent_speaker_label) {
    const card = el("div", { className: "row" });
    card.appendChild(pill(`Agent ≈ ${data.agent_speaker_label}`, ["owner-agent"]));
    if (typeof data.agent_identification_confidence === "number") {
      card.appendChild(pill(`Conf: ${toPercent(data.agent_identification_confidence)}`, ["mono", "faded"]));
    }
    grid.appendChild(card);
  }

  container.appendChild(grid);
  return true;
}

function renderSummary(data) {
  const container = byId("summary");
  clear(container);
  if (!data.summary) {
    show(container, false);
    return false;
  }
  show(container, true);

  const title = el("div", { className: "section-title" });
  title.appendChild(el("h2", { text: "Summary" }));
  container.appendChild(title);

  const p = el("p");
  p.textContent = data.summary;
  container.appendChild(p);
  return true;
}

function renderIntentIssues(data) {
  const container = byId("intentIssues");
  clear(container);
  const has = !!data.customer_intent || nonEmptyArray(data.issues);
  if (!has) {
    show(container, false);
    return false;
  }
  show(container, true);

  const title = el("div", { className: "section-title" });
  title.appendChild(el("h2", { text: "Intent & Issues" }));
  container.appendChild(title);

  if (data.customer_intent) {
    const row = el("div", { className: "row" });
    row.appendChild(pill("Intent"));
    const span = el("span");
    span.textContent = data.customer_intent;
    row.appendChild(span);
    container.appendChild(row);
  }

  if (nonEmptyArray(data.issues)) {
    const ul = el("ul", { className: "clean" });
    data.issues.forEach((it) => {
      const li = el("li");
      const m = el("div", { className: "li-main" });
      m.textContent = it;
      li.appendChild(m);
      ul.appendChild(li);
    });
    container.appendChild(ul);
  }
  return true;
}

function renderActions(data) {
  const container = byId("actions");
  clear(container);
  const has = nonEmptyArray(data.action_items) || nonEmptyArray(data.next_best_actions_ranked);
  if (!has) {
    show(container, false);
    return false;
  }
  show(container, true);

  const title = el("div", { className: "section-title" });
  title.appendChild(el("h2", { text: "Actions" }));
  container.appendChild(title);

  if (nonEmptyArray(data.action_items)) {
    container.appendChild(el("div", { className: "section-subtitle", text: "Action Items" }));
    const ul = el("ul", { className: "clean" });
    data.action_items.forEach((a) => {
      const li = el("li");
      const main = el("div", { className: "li-main" });
      main.textContent = a.item || "";
      li.appendChild(main);

      const sub = el("div", { className: "li-sub" });
      if (a.owner) sub.appendChild(pill(`Owner: ${a.owner}`, [`owner-${a.owner}`]));
      if (a.due) sub.appendChild(pill(`Due: ${a.due}`, ["mono"]));
      li.appendChild(sub);

      ul.appendChild(li);
    });
    container.appendChild(ul);
  }

  if (nonEmptyArray(data.next_best_actions_ranked)) {
    container.appendChild(el("div", { className: "section-subtitle", text: "Next Best Actions (ranked)" }));
    const ul = el("ul", { className: "clean" });
    data.next_best_actions_ranked.forEach((a) => {
      const li = el("li");
      const main = el("div", { className: "li-main" });
      main.textContent = a.action || "";
      li.appendChild(main);

      const sub = el("div", { className: "li-sub" });
      if (typeof a.priority === "number") sub.appendChild(pill(`P${a.priority}`, ["priority"]));
      if (a.owner) sub.appendChild(pill(`Owner: ${a.owner}`, [`owner-${a.owner}`]));
      if (a.due) sub.appendChild(pill(`Due: ${a.due}`, ["mono"]));
      if (a.rationale) {
        const span = el("span", { className: "faded" });
        span.textContent = a.rationale;
        sub.appendChild(span);
      }
      li.appendChild(sub);

      ul.appendChild(li);
    });
    container.appendChild(ul);
  }
  return true;
}

function renderSpeakerSentiment(data) {
  const container = byId("speakerSentiment");
  clear(container);
  const arr = data.speaker_sentiment;
  if (!nonEmptyArray(arr)) {
    show(container, false);
    return false;
  }
  show(container, true);

  const title = el("div", { className: "section-title" });
  title.appendChild(el("h2", { text: "Speakers & Sentiment" }));
  container.appendChild(title);

  const ul = el("ul", { className: "clean" });
  arr.forEach((s) => {
    const li = el("li");
    const main = el("div", { className: "li-main" });
    main.textContent = `${s.speaker_label || "unknown"} · ${s.role || "unknown"}`;
    li.appendChild(main);

    const sub = el("div", { className: "li-sub" });
    if (s.sentiment) sub.appendChild(pill(`Sentiment: ${s.sentiment}`, [sentimentClass(s.sentiment)]));
    if (typeof s.confidence === "number") sub.appendChild(pill(`Conf: ${toPercent(s.confidence)}`, ["mono", "faded"]));
    li.appendChild(sub);

    ul.appendChild(li);
  });
  container.appendChild(ul);
  return true;
}

function renderTranscript(data) {
  const container = byId("transcript");
  clear(container);
  const arr = data.transcript;
  if (!nonEmptyArray(arr)) {
    show(container, false);
    return false;
  }
  show(container, true);

  const title = el("div", { className: "section-title" });
  title.appendChild(el("h2", { text: "Transcript" }));
  container.appendChild(title);

  const ul = el("ul", { className: "clean" });
  arr.forEach((t) => {
    const li = el("li");

    const header = el("div", { className: "row" });
    if (t.approx_time) header.appendChild(pill(t.approx_time, ["mono", "faded"]));
    const who = [t.speaker_label || "unknown", t.role || "unknown"].filter(Boolean).join(" · ");
    if (who) header.appendChild(pill(who, ["nowrap"]));
    li.appendChild(header);

    const body = el("div", { className: "li-sub" });
    const p = el("p");
    p.textContent = t.text || "";
    body.appendChild(p);
    li.appendChild(body);

    ul.appendChild(li);
  });
  container.appendChild(ul);
  return true;
}

function renderWins(data) {
  const container = byId("wins");
  clear(container);
  const arr = data.what_worked;
  if (!nonEmptyArray(arr)) {
    show(container, false);
    return false;
  }
  show(container, true);

  const title = el("div", { className: "section-title" });
  title.appendChild(el("h2", { text: "What Worked" }));
  container.appendChild(title);

  const ul = el("ul", { className: "clean" });
  arr.forEach((w) => {
    const li = el("li");
    const main = el("div", { className: "li-main" });
    main.textContent = w.observation || "";
    li.appendChild(main);

    const sub = el("div", { className: "li-sub" });
    if (w.category) sub.appendChild(pill(w.category));
    if (w.impact) sub.appendChild(pill(`Impact: ${w.impact}`, ["mono"]));
    if (w.evidence) {
      const span = el("span", { className: "faded" });
      span.textContent = `“${w.evidence}”`;
      sub.appendChild(span);
    }
    li.appendChild(sub);

    ul.appendChild(li);
  });
  container.appendChild(ul);
  return true;
}

function renderImprovements(data) {
  const container = byId("improvements");
  clear(container);
  const didnt = data.what_didnt_work;
  const opps = data.agent_improvement_opportunities;
  const has = nonEmptyArray(didnt) || nonEmptyArray(opps);
  if (!has) {
    show(container, false);
    return false;
  }
  show(container, true);

  const title = el("div", { className: "section-title" });
  title.appendChild(el("h2", { text: "Improvements" }));
  container.appendChild(title);

  if (nonEmptyArray(didnt)) {
    container.appendChild(el("div", { className: "section-subtitle", text: "What didn't work" }));
    const ul = el("ul", { className: "clean" });
    didnt.forEach((d) => {
      const li = el("li");
      const main = el("div", { className: "li-main" });
      main.textContent = d.observation || "";
      li.appendChild(main);

      const sub = el("div", { className: "li-sub" });
      if (d.category) sub.appendChild(pill(d.category));
      if (d.impact) sub.appendChild(pill(`Impact: ${d.impact}`, ["mono"]));
      if (d.evidence) {
        const span = el("span", { className: "faded" });
        span.textContent = `“${d.evidence}”`;
        sub.appendChild(span);
      }
      if (d.recommended_fix) {
        const span = el("span");
        span.textContent = `Fix: ${d.recommended_fix}`;
        sub.appendChild(span);
      }
      li.appendChild(sub);

      ul.appendChild(li);
    });
    container.appendChild(ul);
  }

  if (nonEmptyArray(opps)) {
    container.appendChild(el("div", { className: "section-subtitle", text: "Agent improvement opportunities" }));
    const ul = el("ul", { className: "clean" });
    opps.forEach((o) => {
      const li = el("li");
      const main = el("div", { className: "li-main" });
      main.textContent = o.observation || "";
      li.appendChild(main);

      const sub = el("div", { className: "li-sub" });
      if (o.category) sub.appendChild(pill(o.category));
      if (o.impact) sub.appendChild(pill(`Impact: ${o.impact}`, ["mono"]));
      if (o.evidence) {
        const span = el("span", { className: "faded" });
        span.textContent = `“${o.evidence}”`;
        sub.appendChild(span);
      }
      if (o.recommended_change) {
        const span = el("span");
        span.textContent = `Change: ${o.recommended_change}`;
        sub.appendChild(span);
      }
      li.appendChild(sub);
      ul.appendChild(li);
    });
    container.appendChild(ul);
  }

  return true;
}

function renderWinBack(data) {
  const container = byId("winBack");
  clear(container);
  const wb = data.win_back_strategy || {};
  const has =
    wb.root_cause ||
    nonEmptyArray(wb.messaging_pillars) ||
    nonEmptyArray(wb.do) ||
    nonEmptyArray(wb.avoid) ||
    wb.sample_response;
  if (!has) {
    show(container, false);
    return false;
  }
  show(container, true);

  const title = el("div", { className: "section-title" });
  title.appendChild(el("h2", { text: "Win-back Strategy" }));
  container.appendChild(title);

  if (wb.root_cause) {
    const row = el("div", { className: "row" });
    row.appendChild(pill("Root cause", ["faded"]));
    const span = el("span");
    span.textContent = wb.root_cause;
    row.appendChild(span);
    container.appendChild(row);
  }

  if (nonEmptyArray(wb.messaging_pillars)) {
    const row = el("div", { className: "row" });
    row.appendChild(pill("Messaging", ["faded"]));
    wb.messaging_pillars.forEach((p) => row.appendChild(pill(p)));
    container.appendChild(row);
  }

  if (nonEmptyArray(wb.do) || nonEmptyArray(wb.avoid)) {
    const wrap = el("div", { className: "row" });
    if (nonEmptyArray(wb.do)) {
      const doWrap = el("div");
      doWrap.appendChild(el("div", { className: "section-subtitle", text: "Do" }));
      const ul = el("ul", { className: "clean" });
      wb.do.forEach((d) => {
        const li = el("li");
        li.textContent = d;
        ul.appendChild(li);
      });
      doWrap.appendChild(ul);
      wrap.appendChild(doWrap);
    }
    if (nonEmptyArray(wb.avoid)) {
      const avWrap = el("div");
      avWrap.appendChild(el("div", { className: "section-subtitle", text: "Avoid" }));
      const ul = el("ul", { className: "clean" });
      wb.avoid.forEach((d) => {
        const li = el("li");
        li.textContent = d;
        ul.appendChild(li);
      });
      avWrap.appendChild(ul);
      wrap.appendChild(avWrap);
    }
    container.appendChild(wrap);
  }

  if (wb.sample_response) {
    const st = el("div", { className: "section-actions" });
    const btn = el("button", { className: "ghost small", text: "Copy sample response" });
    btn.addEventListener("click", async () => {
      await copyToClipboard(wb.sample_response);
      btn.textContent = "Copied";
      setTimeout(() => (btn.textContent = "Copy sample response"), 1200);
    });
    st.appendChild(btn);
    container.appendChild(st);

    const block = el("div", { className: "copy-block" });
    const p = el("p");
    p.textContent = wb.sample_response;
    block.appendChild(p);
    container.appendChild(block);
  }
  return true;
}

function renderObjections(data) {
  const container = byId("objections");
  clear(container);
  const arr = data.objections;
  if (!nonEmptyArray(arr)) {
    show(container, false);
    return false;
  }
  show(container, true);

  const title = el("div", { className: "section-title" });
  title.appendChild(el("h2", { text: "Objections" }));
  container.appendChild(title);

  const ul = el("ul", { className: "clean" });
  arr.forEach((o) => {
    const li = el("li");
    const main = el("div", { className: "li-main" });
    const pieces = [];
    if (o.type) pieces.push(o.type);
    if (o.severity) pieces.push(`sev: ${o.severity}`);
    if (o.agent_response_quality) pieces.push(`resp: ${o.agent_response_quality}`);
    main.textContent = pieces.join(" · ");
    li.appendChild(main);

    const sub = el("div", { className: "li-sub" });
    if (o.evidence) sub.appendChild(el("span", { className: "faded", text: `“${o.evidence}”` }));
    if (o.recommended_response) sub.appendChild(el("span", { text: `Try: ${o.recommended_response}` }));
    li.appendChild(sub);

    ul.appendChild(li);
  });
  container.appendChild(ul);
  return true;
}

function renderCommitmentOutcome(data) {
  const container = byId("commitmentOutcome");
  clear(container);
  const hasCommit =
    data.customer_commitment &&
    (data.customer_commitment.level || nonEmptyArray(data.customer_commitment.statements));
  const hasOutcome =
    data.outcome &&
    (data.outcome.resolution_status ||
      data.outcome.reason ||
      typeof data.outcome.follow_up_required === "boolean");
  const has = hasCommit || hasOutcome;
  if (!has) {
    show(container, false);
    return false;
  }
  show(container, true);

  const title = el("div", { className: "section-title" });
  title.appendChild(el("h2", { text: "Commitment & Outcome" }));
  container.appendChild(title);

  if (hasCommit) {
    container.appendChild(el("div", { className: "section-subtitle", text: "Customer commitment" }));
    const row = el("div", { className: "row" });
    if (data.customer_commitment.level) row.appendChild(pill(`Level: ${data.customer_commitment.level}`));
    container.appendChild(row);
    if (nonEmptyArray(data.customer_commitment.statements)) {
      const ul = el("ul", { className: "clean" });
      data.customer_commitment.statements.forEach((s) => {
        const li = el("li");
        li.textContent = s;
        ul.appendChild(li);
      });
      container.appendChild(ul);
    }
  }

  if (hasOutcome) {
    container.appendChild(el("div", { className: "section-subtitle", text: "Outcome" }));
    const row = el("div", { className: "row" });
    if (data.outcome.resolution_status) row.appendChild(pill(`Status: ${data.outcome.resolution_status}`));
    if (typeof data.outcome.follow_up_required === "boolean")
      row.appendChild(pill(`Follow-up: ${data.outcome.follow_up_required ? "yes" : "no"}`));
    container.appendChild(row);
    if (data.outcome.reason) {
      const p = el("p", { className: "faded" });
      p.textContent = data.outcome.reason;
      container.appendChild(p);
    }
  }
  return true;
}

function renderRecommendations(data) {
  const container = byId("recommendations");
  clear(container);
  const has =
    nonEmptyArray(data.clarifying_questions_to_ask_next_time) ||
    nonEmptyArray(data.post_call_recommendations) ||
    !!data.sentiment_analysis;
  if (!has) {
    show(container, false);
    return false;
  }
  show(container, true);

  const title = el("div", { className: "section-title" });
  title.appendChild(el("h2", { text: "Recommendations" }));
  container.appendChild(title);

  if (nonEmptyArray(data.clarifying_questions_to_ask_next_time)) {
    container.appendChild(el("div", { className: "section-subtitle", text: "Ask next time" }));
    const ul = el("ul", { className: "clean" });
    data.clarifying_questions_to_ask_next_time.forEach((q) => {
      const li = el("li");
      li.textContent = q;
      ul.appendChild(li);
    });
    container.appendChild(ul);
  }

  if (nonEmptyArray(data.post_call_recommendations)) {
    container.appendChild(el("div", { className: "section-subtitle", text: "Post-call" }));
    const ul = el("ul", { className: "clean" });
    data.post_call_recommendations.forEach((r) => {
      const li = el("li");
      li.textContent = r;
      ul.appendChild(li);
    });
    container.appendChild(ul);
  }

  if (data.sentiment_analysis) {
    container.appendChild(el("div", { className: "section-subtitle", text: "Sentiment analysis" }));
    const p = el("p");
    p.textContent = data.sentiment_analysis;
    container.appendChild(p);
  }

  return true;
}

function renderDrafts(data) {
  const container = byId("drafts");
  clear(container);
  if (!data.follow_up_message_draft) {
    show(container, false);
    return false;
  }
  show(container, true);

  const title = el("div", { className: "section-title" });
  title.appendChild(el("h2", { text: "Drafts" }));
  const actions = el("div", { className: "section-actions" });
  const copyBtn = el("button", { className: "ghost small", text: "Copy follow-up draft" });
  copyBtn.addEventListener("click", async () => {
    await copyToClipboard(data.follow_up_message_draft);
    copyBtn.textContent = "Copied";
    setTimeout(() => (copyBtn.textContent = "Copy follow-up draft"), 1200);
  });
  actions.appendChild(copyBtn);
  title.appendChild(actions);
  container.appendChild(title);

  const block = el("div", { className: "copy-block" });
  const p = el("p");
  p.textContent = data.follow_up_message_draft;
  block.appendChild(p);
  container.appendChild(block);

  return true;
}

function renderNotes(data) {
  const container = byId("notes");
  clear(container);
  const has = nonEmptyArray(data.manager_coach_notes_top3) || nonEmptyArray(data.agent_takeaways_top3);
  if (!has) {
    show(container, false);
    return false;
  }
  show(container, true);

  const title = el("div", { className: "section-title" });
  title.appendChild(el("h2", { text: "Notes" }));
  container.appendChild(title);

  if (nonEmptyArray(data.manager_coach_notes_top3)) {
    container.appendChild(el("div", { className: "section-subtitle", text: "Manager coach notes" }));
    const ul = el("ul", { className: "clean" });
    data.manager_coach_notes_top3.forEach((n) => {
      const li = el("li");
      li.textContent = n;
      ul.appendChild(li);
    });
    container.appendChild(ul);
  }

  if (nonEmptyArray(data.agent_takeaways_top3)) {
    container.appendChild(el("div", { className: "section-subtitle", text: "Agent takeaways" }));
    const ul = el("ul", { className: "clean" });
    data.agent_takeaways_top3.forEach((n) => {
      const li = el("li");
      li.textContent = n;
      ul.appendChild(li);
    });
    container.appendChild(ul);
  }
  return true;
}

function renderKnowledge(data) {
  const container = byId("knowledgeGaps");
  clear(container);
  const arr = data.knowledge_gaps;
  if (!nonEmptyArray(arr)) {
    show(container, false);
    return false;
  }
  show(container, true);

  const title = el("div", { className: "section-title" });
  title.appendChild(el("h2", { text: "Knowledge Gaps" }));
  container.appendChild(title);

  const ul = el("ul", { className: "clean" });
  arr.forEach((g) => {
    const li = el("li");
    li.textContent = g;
    ul.appendChild(li);
  });
  container.appendChild(ul);
  return true;
}

function renderRawJson(data) {
  const pre = byId("jsonViewer");
  pre.textContent = JSON.stringify(data || {}, null, 2);
}

function buildQuickNav() {
  const nav = byId("quickNav");
  clear(nav);

  const sections = [
    ["overview", "Overview"],
    ["summary", "Summary"],
    ["intentIssues", "Intent & Issues"],
    ["actions", "Actions"],
    ["speakerSentiment", "Speakers"],
    ["transcript", "Transcript"],
    ["wins", "Wins"],
    ["improvements", "Improvements"],
    ["winBack", "Win-back"],
    ["objections", "Objections"],
    ["commitmentOutcome", "Outcome"],
    ["recommendations", "Recommendations"],
    ["drafts", "Drafts"],
    ["notes", "Notes"],
    ["knowledgeGaps", "Knowledge"],
    ["rawJson", "Raw JSON"],
  ];

  let any = false;
  sections.forEach(([id, label]) => {
    const sec = byId(id);
    if (sec && !sec.classList.contains("hidden")) {
      const a = el("a", { attrs: { href: `#${id}` } });
      a.textContent = label;
      nav.appendChild(a);
      any = true;
    }
  });

  show(nav, any);
}

function renderAll(data) {
  currentData = data || {};
  const successFlags = [
    renderOverview(currentData),
    renderSummary(currentData),
    renderIntentIssues(currentData),
    renderActions(currentData),
    renderSpeakerSentiment(currentData),
    renderTranscript(currentData),
    renderWins(currentData),
    renderImprovements(currentData),
    renderWinBack(currentData),
    renderObjections(currentData),
    renderCommitmentOutcome(currentData),
    renderRecommendations(currentData),
    renderDrafts(currentData),
    renderNotes(currentData),
    renderKnowledge(currentData),
  ];
  renderRawJson(currentData);
  buildQuickNav();

  const results = byId("results");
  const hasAny = successFlags.some(Boolean);
  show(results, hasAny);
}

// Networking
async function analyzeViaBackend(file) {
  const status = byId("status");
  const analyzeBtn = byId("analyzeBtn");
  try {
    status.textContent = "Uploading audio & starting analysis…";
    analyzeBtn.disabled = true;

    const fd = new FormData();
    fd.append("file", file);

    const resp = await fetch(`${API_BASE}/api/analyze`, {
      method: "POST",
      body: fd,
    });

    if (!resp.ok) {
      throw new Error(`Backend responded ${resp.status}`);
    }

    status.textContent = "Parsing response…";
    const data = await resp.json();
    status.textContent = "Analysis complete.";
    return { ok: true, data };
  } catch (err) {
    console.error("Analyze failed:", err);
    status.textContent = `Analysis failed. Ensure backend is running at ${API_BASE}/api/analyze`;
    return { ok: false, error: err?.message || String(err) };
  } finally {
    analyzeBtn.disabled = false;
  }
}

// Init
function init() {
  const audioInput = byId("audioInput");
  const fileLabel = byId("fileLabel");
  const analyzeBtn = byId("analyzeBtn");
  const toggleRawBtn = byId("toggleRawBtn");
  const copyJsonBtn = byId("copyJsonBtn");
  const status = byId("status");
  const durationEl = byId("duration");

  status.textContent = "Select an audio file to analyze.";

  audioInput.addEventListener("change", () => {
    const f = audioInput.files && audioInput.files[0];
    if (f) {
      fileLabel.textContent = f.name;
      analyzeBtn.disabled = false;
      status.textContent = "Reading audio metadata…";
      // Try to compute duration client-side
      try {
        const audio = document.createElement("audio");
        audio.preload = "metadata";
        const url = URL.createObjectURL(f);
        audio.src = url;
        audio.onloadedmetadata = () => {
          const formatted = formatDuration(audio.duration);
          if (formatted) {
            durationEl.textContent = `Duration: ${formatted}`;
            show(durationEl, true);
          } else {
            durationEl.textContent = "";
            show(durationEl, false);
          }
          URL.revokeObjectURL(url);
          status.textContent = "Ready. Click Analyze to start.";
        };
        audio.onerror = () => {
          show(durationEl, false);
          status.textContent = "Ready. Click Analyze to start.";
        };
      } catch {
        show(durationEl, false);
        status.textContent = "Ready. Click Analyze to start.";
      }
    } else {
      fileLabel.textContent = "Choose audio file…";
      analyzeBtn.disabled = true;
      status.textContent = "Select an audio file to analyze.";
      show(durationEl, false);
    }
  });

  analyzeBtn.addEventListener("click", async () => {
    const f = audioInput.files && audioInput.files[0];
    if (!f) return;
    status.textContent = "Preparing request…";
    analyzeBtn.disabled = true;
    const res = await analyzeViaBackend(f);
    if (res.ok) {
      status.textContent = "Rendering results…";
      renderAll(res.data);
      status.textContent = "Done.";
    } else {
      // status is already set in analyzeViaBackend on failure
    }
    analyzeBtn.disabled = false;
  });

  toggleRawBtn.addEventListener("click", () => {
    const raw = byId("rawJson");
    const isHidden = raw.classList.contains("hidden");
    show(raw, isHidden);
    toggleRawBtn.textContent = isHidden ? "Hide JSON" : "Raw JSON";
    buildQuickNav();
  });

  if (copyJsonBtn) {
    copyJsonBtn.addEventListener("click", async () => {
      if (!currentData) return;
      const ok = await copyToClipboard(JSON.stringify(currentData, null, 2));
      copyJsonBtn.textContent = ok ? "Copied" : "Copy failed";
      setTimeout(() => (copyJsonBtn.textContent = "Copy JSON"), 1200);
    });
  }
}

document.addEventListener("DOMContentLoaded", init);
