const questionEl = document.getElementById("question");
const runBtn = document.getElementById("run-btn");
const resultEl = document.getElementById("result");
const historyEl = document.getElementById("history");

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function sqlBlock(sql) {
  return sql ? `<div class="result-sql">${escapeHtml(sql)}</div>` : "";
}

async function runQuery() {
  const question = questionEl.value.trim();
  if (!question) return;

  runBtn.disabled = true;
  runBtn.textContent = "Generating…";
  resultEl.innerHTML = `<div class="result-status generated">generating…</div>`;

  try {
    const res = await fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();

    if (data.status === "blocked") {
      resultEl.innerHTML = `
        <div class="result-status blocked">✕ blocked by guardrails</div>
        ${sqlBlock(data.sql)}
        <div class="result-note blocked-note">${escapeHtml(data.reason)}</div>`;
    } else if (data.status === "error" || data.error) {
      resultEl.innerHTML = `
        <div class="result-status error">! error</div>
        <div class="result-note error-note">${escapeHtml(data.reason || data.error)}</div>`;
    } else {
      resultEl.innerHTML = `
        <div class="result-status generated">✓ generated</div>
        ${sqlBlock(data.sql)}`;
    }
  } catch (err) {
    resultEl.innerHTML = `
      <div class="result-status error">! error</div>
      <div class="result-note error-note">Something went wrong reaching the server. Try again.</div>`;
  }

  runBtn.disabled = false;
  runBtn.textContent = "Generate SQL";
  loadHistory();
}

const HIST_ICON = { generated: "✓", blocked: "✕", error: "!" };

async function loadHistory() {
  const res = await fetch("/api/history");
  const items = await res.json();
  historyEl.innerHTML = items
    .map(
      (i) => `
      <li>
        <span class="hist-icon ${i.status}">${HIST_ICON[i.status] || "?"}</span>
        <span class="hist-question">${escapeHtml(i.question)}</span>
      </li>`
    )
    .join("");
}

runBtn.addEventListener("click", runQuery);
questionEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
    runQuery();
  }
});

loadHistory();