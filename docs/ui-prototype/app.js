"use strict";

const NODES = ["A", "B", "C", "D", "F", "G", "H", "I", "J", "K", "L", "M"];
const NODE_NAMES = { A:"认证", B:"机会", C:"额度", D:"范围", F:"字段", G:"证据", H:"机制", I:"候选", J:"回测", K:"诊断", L:"终检", M:"审批" };
const TERMINAL = new Set(["SUBMITTED", "REJECTED", "STOPPED", "FAILED", "BUDGET_EXHAUSTED", "NO_PROGRESS"]);
const state = { bootstrap:null, runs:[], scopeOptions:null, datasetRows:[], currentRun:null, detail:null, detailSignature:null, view:"home", step:1, logFilter:"", poll:null };
const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];

async function api(path, options={}) {
  const init = { ...options, headers:{ "Content-Type":"application/json", ...(options.headers || {}) } };
  if (init.body && typeof init.body !== "string") init.body = JSON.stringify(init.body);
  const response = await fetch(path, init);
  const body = await response.json().catch(() => ({ ok:false, detail:`HTTP ${response.status}` }));
  if (!response.ok || body.ok === false) throw new Error(body.detail || body.error_type || `HTTP ${response.status}`);
  return body;
}

function esc(value) {
  return String(value ?? "").replace(/[&<>'"]/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[ch]));
}
function fmtTime(value) {
  if (!value) return "—";
  const d = new Date(value); return Number.isNaN(d.getTime()) ? value : d.toLocaleString("zh-CN", { hour12:false });
}
function stateClass(value) {
  if (["SUBMITTED","AWAITING_APPROVAL"].includes(value)) return "good";
  if (["FAILED","REJECTED","STOPPED","BUDGET_EXHAUSTED","NO_PROGRESS"].includes(value)) return "bad";
  if (["RUNNING","CREATED"].includes(value)) return "running";
  return "";
}
function toast(message) {
  const el = $("#toast"); el.textContent = message; el.hidden = false;
  clearTimeout(toast.timer); toast.timer = setTimeout(() => { el.hidden = true; }, 3600);
}
function modal(title, body, actions=[]) {
  $("#modalTitle").textContent = title; $("#modalBody").innerHTML = body;
  $("#modalActions").innerHTML = actions.map((item, i) => `<button class="btn ${esc(item.className || "")}" data-modal-action="${i}">${esc(item.label)}</button>`).join("");
  actions.forEach((item, i) => $(`[data-modal-action="${i}"]`).addEventListener("click", item.onClick));
  $("#modal").hidden = false;
}
function closeModal() { $("#modal").hidden = true; }
function showView(name) {
  state.view = name;
  $$(".view").forEach(el => el.classList.toggle("active", el.id === `view-${name}`));
  $$(".nav-btn").forEach(el => el.classList.toggle("active", el.dataset.view === name));
  if (name === "home") renderHome();
  if (name === "history") renderHistory();
  if (name === "run") { renderRunSelect(); loadCurrentRun(); }
  if (name === "settings") renderSettings();
  location.hash = name;
}

async function refreshAll() {
  const [bootstrap, runs, scopeOptions] = await Promise.all([
    api("/api/bootstrap"),
    api("/api/runs"),
    api("/api/platform/simulation-options").catch(error => ({ok:false, detail:error.message})),
  ]);
  state.bootstrap = bootstrap; state.runs = runs.runs;
  if (scopeOptions.ok) state.scopeOptions = scopeOptions;
  if (!state.currentRun && state.runs.length) state.currentRun = state.runs[0].run_id;
  $("#apiState").textContent = "API READY"; $("#apiState").className = "status-dot ok";
  renderHome(); renderRunSelect(); renderHistory(); renderSettings(); renderScopeOptions();
}

function setSelectChoices(select, choices, preferred) {
  const rows = Array.isArray(choices) ? choices : [];
  select.innerHTML = rows.map(item => `<option value="${esc(item.value)}">${esc(item.label)}</option>`).join("");
  if (!rows.length) select.innerHTML = `<option value="">无可用选项</option>`;
  const values = rows.map(item => String(item.value));
  select.value = values.includes(String(preferred)) ? String(preferred) : (values[0] || "");
}

function updateDependentScopeOptions() {
  if (!state.scopeOptions?.scope) return;
  const scope = state.scopeOptions.scope, region = $('[name="region"]').value;
  const delay = $('[name="delay"]'), universe = $('[name="universe"]'), neutral = $('[name="neutralization"]');
  const previous = {delay:delay.value, universe:universe.value, neutralization:neutral.value};
  const defaults = state.bootstrap?.defaults || {};
  setSelectChoices(delay, scope.delays?.[region], previous.delay || defaults.delay || 1);
  setSelectChoices(universe, scope.universes?.[region], previous.universe || defaults.universe || "");
  setSelectChoices(neutral, scope.neutralizations?.[region], previous.neutralization || "FAST");
  loadDatasetChoices();
}
async function loadDatasetChoices() {
  const mode=$("input[name=scope_mode]:checked").value;
  const region=(mode === "auto" ? $('[name="auto_region"]') : $('[name="region"]')).value;
  if (!region) return;
  const select=$('[name="dataset_id"]'), previous=select.value; select.disabled=true;
  try {
    const result=await api(`/api/platform/datasets?region=${encodeURIComponent(region)}`);
    state.datasetRows=Array.isArray(result.datasets) ? result.datasets : [];
    const category=$('[name="dataset_category"]'), previousCategory=category.value;
    const categories=[...new Set(state.datasetRows.map(row=>String(row.category || "uncategorized")))].sort();
    setSelectChoices(category, categories.map(value=>({value,label:value})), previousCategory);
    category.disabled=!categories.length;
    renderDatasetChoices(previous);
  } catch (error) {
    state.datasetRows=[];
    $('[name="dataset_category"]').disabled=true;
    select.innerHTML='<option value="">无法加载数据集</option>';
  }
  finally { select.disabled=false; }
}

function renderDatasetChoices(preferred) {
  const category=$('[name="dataset_category"]').value;
  const rows=state.datasetRows.filter(item=>!category || String(item.category || "uncategorized") === category);
  const select=$('[name="dataset_id"]'), selected=preferred === undefined ? select.value : preferred;
  select.innerHTML=`<option value="">选择数据集</option>${rows.map(item=>`<option value="${esc(item.id)}">${esc(item.label)} (${esc(item.id)})</option>`).join("")}`;
  select.value=rows.some(item=>item.id===selected) ? selected : "";
}

function renderScopeOptions() {
  const payload = state.scopeOptions;
  if (!payload?.scope) {
    $("#scopeOptionsSource").textContent = "WQ OPTIONS · UNAVAILABLE";
    $("#scopeOptionsMeta").textContent = "未能读取平台范围配置";
    return;
  }
  const scope = payload.scope, regionSelect = $('[name="region"]'), autoRegionSelect = $('[name="auto_region"]');
  const currentRegion = regionSelect.value;
  const currentAutoRegion = autoRegionSelect.value;
  const defaultRegion = state.bootstrap?.defaults?.region || "USA";
  setSelectChoices(regionSelect, scope.regions, currentRegion || defaultRegion);
  setSelectChoices(autoRegionSelect, scope.regions, currentAutoRegion || defaultRegion);
  updateDependentScopeOptions();
  const universeCount = Object.values(scope.universes || {}).reduce((total, rows) => total + rows.length, 0);
  const neutralCount = Object.values(scope.neutralizations || {}).reduce((total, rows) => total + rows.length, 0);
  const sourceLabels = {platform:"WQ PLATFORM LIVE",local_cache:"LOCAL CACHE",run_artifact:"WQ RUN CACHE",bundled_fallback:"BUNDLED WQ SNAPSHOT"};
  $("#scopeOptionsSource").textContent = sourceLabels[payload.source] || String(payload.source).toUpperCase();
  const suffix = payload.refresh_status === "authentication_required" ? " · 登录后可刷新" : (payload.stale ? " · 缓存" : "");
  $("#scopeOptionsMeta").textContent = `${scope.regions.length} Regions · ${universeCount} Universe 组合 · ${neutralCount} Neutralization 组合 · ${payload.settings_catalog?.length || 0} Settings${suffix}`;
}

async function refreshScopeOptions() {
  const button = $("#refreshScopeOptions"); button.disabled = true;
  try {
    state.scopeOptions = await api("/api/platform/simulation-options?refresh=1");
    renderScopeOptions();
    toast(state.scopeOptions.source === "platform" ? "平台清单已刷新" : "实时平台不可用，已使用最近缓存");
  } catch (error) { toast(error.message); }
  finally { button.disabled = false; }
}

function renderHome() {
  if (!state.bootstrap) return;
  const model = role => state.bootstrap.models.find(item => item.role === role) || {};
  const planner = model("planner"), operator = model("operator");
  $("#homeAuth").textContent = state.bootstrap.auth.cookie_present ? "COOKIE 已保存" : "未登录";
  $("#homePlanner").textContent = planner.model ? `${planner.model} · ${planner.secret_configured ? "KEY OK" : "缺 KEY"}` : "未配置";
  $("#homeOperator").textContent = operator.model ? `${operator.model} · ${operator.secret_configured ? "KEY OK" : "缺 KEY"}` : "未配置";
  const attention = state.runs.filter(run => ["AWAITING_APPROVAL","NEEDS_AUTH","NEEDS_DATA","PAUSED_MODEL","RUNNING","CREATED"].includes(run.state));
  $("#homeAttention").textContent = attention.length;
  const shown = attention.length ? attention : state.runs.slice(0, 5);
  $("#homeQueue").innerHTML = shown.length ? shown.map(runItem).join("") : `<div class="empty-state">暂无研究记录</div>`;
  $$("[data-open-run]", $("#homeQueue")).forEach(button => button.addEventListener("click", () => openRun(button.dataset.openRun)));
}

function runItem(run) {
  const t = run.termination || {};
  return `<div class="run-item">
    <div><div class="run-id">${esc(run.run_id)}</div><div class="run-meta">${esc(fmtTime(run.updated_at))}</div></div>
    <div><span class="state-pill ${stateClass(run.state)}">${esc(run.state)}</span></div>
    <div><strong>${esc(run.latest_node || "—")}</strong><div class="run-meta">LATEST NODE</div></div>
    <div><strong>${esc(t.actual_simulations || 0)} / ${esc(t.max_simulations || 0)}</strong><div class="run-meta">BACKTESTS</div></div>
    <button class="btn" data-open-run="${esc(run.run_id)}">打开</button>
  </div>`;
}

function openRun(runId) { state.currentRun = runId; state.detail = null; state.detailSignature = null; showView("run"); }
function renderRunSelect() {
  const select = $("#runSelect");
  select.innerHTML = state.runs.map(run => `<option value="${esc(run.run_id)}">${esc(run.run_id)} · ${esc(run.state)}</option>`).join("");
  if (state.currentRun) select.value = state.currentRun;
  $("#activeRunLabel").textContent = state.currentRun || "NO ACTIVE RUN";
}
async function loadCurrentRun(silent=false) {
  if (state.view !== "run" || !state.currentRun) { $("#emptyRun").hidden = false; $("#runContent").hidden = true; return; }
  try {
    const detail = await api(`/api/runs/${encodeURIComponent(state.currentRun)}`);
    const signature = JSON.stringify(detail);
    const changed = signature !== state.detailSignature;
    state.detail = detail;
    state.detailSignature = signature;
    if (!silent || changed) renderRun();
    schedulePoll();
  } catch (error) { if (!silent) toast(error.message); }
}
function schedulePoll() {
  clearTimeout(state.poll);
  if (!state.detail) return;
  const job = state.detail.job;
  const active = job && ["QUEUED","RUNNING"].includes(job.state);
  if (active || !TERMINAL.has(state.detail.state)) state.poll = setTimeout(() => loadCurrentRun(true), 2500);
}

function renderRun() {
  const run = state.detail; if (!run) return;
  $("#emptyRun").hidden = true; $("#runContent").hidden = false;
  const scope = run.scope || {}, t = run.termination || {}, job = run.job;
  $("#runHero").innerHTML = [
    ["RUN ID", run.run_id], ["STATE", job && ["QUEUED","RUNNING"].includes(job.state) ? `${run.state} · ${job.action.toUpperCase()}` : run.state],
    ["SCOPE", `${scope.region ?? "AUTO"} · D${scope.delay ?? "—"}`], ["UNIVERSE", scope.universe ?? "AUTO"], ["NEUTRALIZATION", scope.neutralization ?? "AUTO"]
  ].map(([k,v]) => `<div><small>${esc(k)}</small><strong>${esc(v)}</strong></div>`).join("");
  renderOuterPipeline(run); renderIdeaPipeline(run); renderCandidatePipeline(run); renderLogs(run); renderTimeline(run); renderPlan(run); renderMeters(t); renderActions(run); renderArtifacts(run);
}

function renderOuterPipeline(run) {
  const attempts = run.timeline || [];
  const totals = run.node_attempt_counts || [];
  const byNode = Object.fromEntries(NODES.map(node => [node, attempts.filter(a => a.node === node)]));
  const running = run.job && ["QUEUED","RUNNING"].includes(run.job.state);
  const latestIndex = NODES.indexOf(run.latest_node);
  $("#outerPipeline").innerHTML = NODES.map((node, index) => {
    const rows = byNode[node], nodeTotals = totals.filter(item => item.node === node);
    const total = nodeTotals.reduce((sum,item) => sum + Number(item.count || 0), 0);
    const completed = nodeTotals.some(item => item.status === "COMPLETED") || rows.some(a => a.status === "COMPLETED");
    const failed = nodeTotals.some(item => item.status === "FAILED") || rows.some(a => a.status === "FAILED");
    const active = running && (index === latestIndex + 1 || (!run.latest_node && node === "A"));
    return `<div class="node ${completed ? "done" : ""} ${failed ? "failed" : ""} ${active ? "active" : ""}"><b>${node}</b><small>${NODE_NAMES[node]}</small>${total > 1 ? `<span class="attempt-badge">×${total}</span>` : ""}</div>`;
  }).join("");
}
function renderIdeaPipeline(run) {
  const ideas = run.ideas || [];
  const candidates = run.candidates || [];
  const statuses = ["PENDING_INSPECT","INSPECTING","READY","SIMULATING","COMPLETED","ERROR","ABORTED"];
  const labels = {PENDING_INSPECT:"Pending",INSPECTING:"Inspecting",READY:"Ready",SIMULATING:"Simulating",COMPLETED:"Completed",ERROR:"Retrying",ABORTED:"Aborted"};
  const counts = Object.fromEntries(statuses.map(status => [status, ideas.filter(idea => idea.status === status).length]));
  $("#ideaFlow").innerHTML = statuses.map(status => `<div class="flow-stage"><span>${labels[status]}</span><strong>${counts[status]}</strong></div>`).join("");
  $("#ideaCount").textContent = `${ideas.length} IDEAS`;
  $("#ideaList").innerHTML = ideas.length ? ideas.map(idea => {
    const body = idea.idea || {};
    const mechanismId = body.mechanism_id || idea.idea_id;
    const linked = candidates.filter(candidate => {
      const candidateBody = candidate.candidate || {};
      const legacyPlanOne = idea.plan_version === 1 && candidateBody.plan_version == null && candidateBody.plan_hash == null;
      return candidateBody.mechanism_id === mechanismId && (
        legacyPlanOne || (
          candidateBody.plan_version === idea.plan_version &&
          candidateBody.plan_hash === idea.plan_hash
        )
      );
    });
    const expressions = linked.map(candidate => candidate.expression || candidate.candidate?.expression).filter(Boolean);
    const canRetry = ["ERROR","ABORTED"].includes(idea.status);
    const canAbort = !["COMPLETED","ABORTED"].includes(idea.status);
    return `<article class="idea-card" data-idea-id="${esc(idea.idea_id)}">
      <div class="idea-card-head"><div><strong>${esc(body.title || body.name || idea.idea_id)}</strong><span>${esc(idea.stage)} · attempt ${esc(idea.retry_count || 0)}</span></div><span class="pipeline-pill ${esc(idea.status)}">${esc(idea.status)}</span></div>
      <p>${esc(body.hypothesis || body.reasoning_summary || "No hypothesis recorded")}</p>
      <div class="idea-fields">${(body.field_ids || []).map(field => `<code>${esc(field)}</code>`).join("")}</div>
      <details><summary>${expressions.length} expressions</summary><div class="idea-expressions">${expressions.length ? expressions.map(expression => `<code>${esc(expression)}</code>`).join("") : "No validated expression yet"}</div></details>
      ${idea.last_error ? `<div class="idea-error">${esc(idea.last_error)}${idea.next_retry_at ? `<br>next retry ${esc(fmtTime(idea.next_retry_at))}` : ""}</div>` : ""}
      <div class="idea-actions">${canRetry ? `<button class="text-btn" data-idea-action="retry">Retry</button>` : ""}${canAbort ? `<button class="text-btn danger-text" data-idea-action="abort">Abort</button>` : ""}</div>
    </article>`;
  }).join("") : `<div class="data-body">Ideas will appear after node H.</div>`;
}
function renderCandidatePipeline(run) {
  const candidates = run.candidates || [];
  const stages = ["REJECTED","VALIDATED","SIM_QUEUED","SIMULATING","SIMULATED","EVALUATED"];
  const labels = {REJECTED:"校验拒绝",VALIDATED:"已验证",SIM_QUEUED:"已排队",SIMULATING:"回测中",SIMULATED:"已回测",EVALUATED:"已诊断"};
  const counts = Object.fromEntries(stages.map(s => [s, candidates.filter(c => c.pipeline_state === s).length]));
  $("#candidateFlow").innerHTML = stages.map(s => `<div class="flow-stage"><span>${labels[s]}</span><strong>${counts[s]}</strong></div>`).join("");
  $("#candidateCount").textContent = `${candidates.length} CANDIDATES`;
  $("#candidateRows").innerHTML = candidates.length ? candidates.map(c => {
    const body = c.candidate || {}, metrics = c.metrics || {}, sims = c.simulations || [];
    const mechanism = body.mechanism_id || body.template_id || body.strategy_family || "—";
    return `<tr><td>${c.id}</td><td class="expr">${esc(c.expression || body.raw_candidate?.expression || "—")}</td><td>${esc(mechanism)}</td><td>${esc(sims.length ? sims.map(s=>s.status).join(", ") : "—")}</td><td>${esc(metrics.sharpe ?? "—")}</td><td>${esc(metrics.fitness ?? "—")}</td><td><span class="pipeline-pill ${esc(c.pipeline_state)}">${esc(c.pipeline_state)}</span>${c.reason ? `<div class="run-meta">${esc(c.reason)}</div>` : ""}</td></tr>`;
  }).join("") : `<tr><td colspan="7">尚无候选记录</td></tr>`;
}

function logEntries(run) {
  const attempts = (run.timeline || []).map(a => ({ time:a.finished_at || a.started_at, node:a.node, level:a.status === "FAILED" ? "ERROR" : "NODE", message:summaryText(a.summary) || `${a.status} · attempt ${a.attempt_number}` }));
  const models = (run.model_calls || []).map(c => ({ time:c.created_at, node:c.node, level:c.status === "FAILED" ? "ERROR" : c.role.toUpperCase(), message:`${c.model} · ${c.purpose} · ${c.status}` }));
  const commands = (run.commands || []).map(c => ({ time:c.updated_at || c.created_at, node:c.node, level:"CMD", message:`command ${c.status}${c.resource_id ? ` · ${c.resource_id}` : ""}${c.error ? ` · ${c.error}` : ""}` }));
  return [...attempts, ...models, ...commands].sort((a,b) => String(a.time).localeCompare(String(b.time)));
}
function summaryText(summary) {
  if (!summary || typeof summary !== "object") return "";
  const keys = ["decision","reason","failure","authenticated","accepted","rejected","simulations","alphas","alpha_id","status_code"];
  const parts = keys.filter(k => summary[k] !== undefined).map(k => `${k}=${typeof summary[k] === "object" ? JSON.stringify(summary[k]) : summary[k]}`);
  const route = summary._coordinator?.next_node; if (route) parts.push(`next=${route}`);
  return parts.join(" · ").slice(0, 900);
}
function renderLogs(run) {
  const entries = logEntries(run), nodes = [...new Set(entries.map(e=>e.node).filter(Boolean))];
  $("#logFilter").innerHTML = `<option value="">全部节点</option>${nodes.map(n=>`<option value="${esc(n)}">节点 ${esc(n)}</option>`).join("")}`;
  $("#logFilter").value = state.logFilter;
  const shown = state.logFilter ? entries.filter(e => e.node === state.logFilter) : entries;
  $("#logWindow").innerHTML = shown.length ? shown.map(e => `<div class="log-line"><span>${esc(fmtTime(e.time).split(" ").pop())}</span><span class="node-code">${esc(e.node || "—")}</span><span class="${e.level === "ERROR" ? "level-error" : ""}">${esc(e.level)}</span><span>${esc(e.message)}</span></div>`).join("") : "<div>暂无日志</div>";
  $("#logWindow").scrollTop = $("#logWindow").scrollHeight;
}
function renderTimeline(run) {
  const attempts = run.timeline || []; $("#attemptCount").textContent = `${attempts.length} ATTEMPTS`;
  $("#timeline").innerHTML = attempts.length ? [...attempts].reverse().map(a => `<div class="attempt"><div class="attempt-node">${esc(a.node)}</div><div class="attempt-time">${esc(fmtTime(a.started_at))}<br>${esc(a.status)}</div><div class="attempt-body"><strong>${esc(NODE_NAMES[a.node] || a.node)} · ATTEMPT ${esc(a.attempt_number)}</strong><p>${esc(summaryText(a.summary) || "节点已记录")}</p></div></div>`).join("") : `<div class="data-body">等待第一个节点。</div>`;
}
function renderPlan(run) {
  $("#planTag").textContent = run.plan_version ? `PLAN v${run.plan_version}` : "NO PLAN";
  const plan = run.plan;
  if (!plan) { $("#planBody").innerHTML = "研究计划将在 H 节点锁定。"; return; }
  const entries = Object.entries(plan).filter(([key]) => !["raw","evidence_bundle"].includes(key)).slice(0, 12);
  $("#planBody").innerHTML = `<dl>${entries.map(([key,value]) => `<dt>${esc(key.toUpperCase())}</dt><dd>${esc(typeof value === "object" ? JSON.stringify(value) : value)}</dd>`).join("")}</dl>`;
}
function renderMeters(t) {
  const rows = [["实际回测", t.actual_simulations || 0, t.max_simulations || 0], ["诊断轮数", t.rounds || 0, t.max_rounds || 0]];
  $("#terminationMeters").innerHTML = rows.map(([label,used,max]) => `<div class="meter"><div class="meter-label"><span>${label}</span><span>${used} / ${max}</span></div><div class="meter-track"><div class="meter-fill" style="width:${max ? Math.min(100, used/max*100) : 0}%"></div></div></div>`).join("");
}
function renderActions(run) {
  const activeJob = run.job && ["QUEUED","RUNNING"].includes(run.job.state);
  $("#actionTag").textContent = activeJob ? run.job.state : run.state;
  let text = activeJob ? `${run.job.action.toUpperCase()} 正在后台执行。` : `当前状态：${run.state}`;
  if (run.recoverable && !activeJob) text += ` · 可从失败节点 ${run.failed_node} 安全重试`;
  let buttons = "";
  if (run.state === "AWAITING_APPROVAL" && !activeJob) buttons = `<button class="btn" id="rejectRun">拒绝</button><button class="btn danger" id="approveRun">批准正式提交</button>`;
  else if ((run.recoverable || ![...TERMINAL,"AWAITING_APPROVAL"].includes(run.state)) && !activeJob) buttons = `<button class="btn primary" id="resumeRun">继续运行</button>`;
  const canStop = !TERMINAL.has(run.state) && run.state !== "AWAITING_APPROVAL" && run.job?.action !== "approve";
  if (canStop) buttons += `<button class="btn danger" id="stopRun">停止研究</button>`;
  else if (run.job?.state === "FAILED") text += ` · ${run.job.error_type}: ${run.job.detail}`;
  $("#actionBody").innerHTML = `<p>${esc(text)}</p><div class="action-buttons">${buttons}<button class="btn" id="refreshRun">刷新</button></div>`;
  $("#refreshRun").addEventListener("click", () => loadCurrentRun());
  $("#resumeRun")?.addEventListener("click", () => runAction("resume"));
  $("#approveRun")?.addEventListener("click", confirmApprove);
  $("#rejectRun")?.addEventListener("click", confirmReject);
  $("#stopRun")?.addEventListener("click", confirmStop);
}
function renderArtifacts(run) {
  const artifacts = run.artifacts || []; $("#artifactCount").textContent = `${artifacts.length} FILES`;
  $("#artifactList").innerHTML = artifacts.length ? artifacts.slice(0, 80).map(a => `<a class="artifact-item" target="_blank" rel="noopener" href="/api/runs/${encodeURIComponent(run.run_id)}/artifacts/${a.id}"><strong>${esc(a.node)}</strong><span>${esc(a.name)}</span></a>`).join("") : `<div class="data-body">暂无成果文件</div>`;
}
async function runAction(action, body={}) {
  try { await api(`/api/runs/${encodeURIComponent(state.currentRun)}/${action}`, { method:"POST", body }); closeModal(); toast(`${action} 已进入后台队列`); await loadCurrentRun(); }
  catch (error) { toast(error.message); }
}

function confirmStop() {
  modal("停止研究", "<p>当前研究将停止，正在执行的单个请求完成后不会继续后续步骤或创建新的模拟。</p>", [
    {label:"取消", onClick:closeModal},
    {label:"停止研究", className:"danger", onClick:()=>runAction("stop")},
  ]);
}

async function ideaAction(ideaId, action) {
  if (!state.currentRun) return;
  try {
    await api(`/api/runs/${encodeURIComponent(state.currentRun)}/ideas/${encodeURIComponent(ideaId)}/${action}`, {method:"POST", body:{}});
    toast(`${ideaId} · ${action}`);
    await loadCurrentRun();
  } catch (error) {
    toast(error.message);
  }
}
function confirmApprove() {
  modal("批准正式提交", `<p>此操作会将最终报告中推荐的 Alpha 正式提交到 BRAIN。审批会绑定当前报告哈希。</p><label><span>输入 SUBMIT 确认</span><input id="submitConfirm" autocomplete="off" /></label>`, [
    {label:"取消", onClick:closeModal}, {label:"确认提交", className:"danger", onClick:()=> { if ($("#submitConfirm").value !== "SUBMIT") return toast("请输入 SUBMIT"); runAction("approve"); }}
  ]);
}
function confirmReject() {
  modal("拒绝研究结果", `<label><span>拒绝原因</span><textarea id="rejectReason" rows="5"></textarea></label>`, [
    {label:"取消", onClick:closeModal}, {label:"确认拒绝", className:"danger", onClick:()=> runAction("reject", {reason:$("#rejectReason").value})}
  ]);
}

function renderHistory() {
  const select = $("#historyFilter"), states = [...new Set(state.runs.map(r=>r.state))].sort();
  const current = select.value; select.innerHTML = `<option value="">全部</option>${states.map(s=>`<option>${esc(s)}</option>`).join("")}`; select.value = current;
  const runs = current ? state.runs.filter(r => r.state === current) : state.runs;
  $("#historyList").innerHTML = runs.length ? runs.map(run => { const t=run.termination||{}; return `<div class="history-item"><div><div class="run-id">${esc(run.run_id)}</div><div class="run-meta">${esc(fmtTime(run.created_at))}</div></div><div><span class="state-pill ${stateClass(run.state)}">${esc(run.state)}</span></div><div><strong>${esc(run.latest_node||"—")}</strong><div class="run-meta">LATEST</div></div><div><strong>${t.actual_simulations||0}/${t.max_simulations||0}</strong><div class="run-meta">BACKTESTS</div></div><button class="btn" data-history-run="${esc(run.run_id)}">查看</button></div>`; }).join("") : `<div class="empty-state">没有匹配记录</div>`;
  $$("[data-history-run]").forEach(b => b.addEventListener("click",()=>openRun(b.dataset.historyRun)));
}

function renderSettings() {
  if (!state.bootstrap) return;
  $("#configPath").textContent = state.bootstrap.config_path; $("#authEmail").value = state.bootstrap.auth.email || "";
  $("#authTag").textContent = state.bootstrap.auth.cookie_present ? "COOKIE STORED" : "NO COOKIE";
  $("#storagePaths").innerHTML = `<dt>CONFIG</dt><dd>${esc(state.bootstrap.config_path)}</dd><dt>DATABASE</dt><dd>${esc(state.bootstrap.database_path)}</dd><dt>RUN ROOT</dt><dd>${esc(state.bootstrap.run_root)}</dd>`;
  for (const role of ["planner","operator"]) {
    const model = state.bootstrap.models.find(m=>m.role===role) || {}, root = $(`.model-settings[data-role="${role}"] .model-form`);
    root.innerHTML = `<label><span>PROVIDER</span><select data-field="provider"><option value="openai">openai</option><option value="openai-compatible">openai-compatible</option></select></label><label><span>API STYLE</span><select data-field="api_style"><option value="responses">responses</option><option value="chat_completions">chat_completions</option></select></label><label class="wide"><span>MODEL</span><input data-field="model" /></label><label class="wide"><span>BASE URL</span><input data-field="base_url" /></label><label><span>REASONING</span><input data-field="reasoning" /></label><label><span>STRUCTURED OUTPUT</span><select data-field="structured_outputs"><option value="true">true</option><option value="false">false</option></select></label><label><span>CONNECT TIMEOUT (S)</span><input type="number" min="1" max="3600" data-field="connect_timeout_seconds" /></label><label><span>READ TIMEOUT (S)</span><input type="number" min="1" max="3600" data-field="read_timeout_seconds" /></label><label><span>PROXY MODE</span><select data-field="proxy_mode"><option value="system">system</option><option value="direct">direct</option><option value="custom">custom</option></select></label><label class="wide"><span>PROXY URL</span><input data-field="proxy_url" placeholder="http://127.0.0.1:7890" /></label><div class="model-actions"><button class="btn" data-model-key="${role}">设置密钥</button><button class="btn primary" data-model-save="${role}">保存配置</button></div>`;
    for (const field of ["provider","api_style","model","base_url","reasoning","proxy_mode","proxy_url"]) root.querySelector(`[data-field="${field}"]`).value = model[field] ?? "";
    root.querySelector('[data-field="connect_timeout_seconds"]').value = model.connect_timeout_seconds ?? 10;
    root.querySelector('[data-field="read_timeout_seconds"]').value = model.read_timeout_seconds ?? 300;
    root.querySelector('[data-field="structured_outputs"]').value = String(model.structured_outputs ?? true);
  }
  $$('[data-model-save]').forEach(b => b.addEventListener("click",()=>saveModel(b.dataset.modelSave)));
  $$('[data-model-key]').forEach(b => b.addEventListener("click",()=>setModelKey(b.dataset.modelKey)));
}
async function saveModel(role) {
  const root = $(`.model-settings[data-role="${role}"] .model-form`), payload={};
  $$('[data-field]', root).forEach(el => {
    payload[el.dataset.field] = el.dataset.field === "structured_outputs"
      ? el.value === "true"
      : ["connect_timeout_seconds", "read_timeout_seconds"].includes(el.dataset.field)
        ? Number(el.value)
        : el.value;
  });
  try { await api(`/api/models/${role}`, {method:"PUT", body:payload}); toast(`${role} 配置已保存`); await refreshAll(); }
  catch (error) { toast(error.message); }
}
function setModelKey(role) {
  modal(`${role.toUpperCase()} API KEY`, `<label><span>密钥只写入系统 Keyring，不写入配置文件</span><input type="password" id="modelKey" autocomplete="new-password" /></label>`, [
    {label:"取消",onClick:closeModal},{label:"保存密钥",className:"primary",onClick:async()=>{try{await api(`/api/models/${role}/key`,{method:"PUT",body:{key:$("#modelKey").value}});closeModal();toast("密钥已写入 Keyring");await refreshAll();}catch(e){toast(e.message);}}}
  ]);
}

function setWizardStep(step) {
  state.step = Math.max(1, Math.min(4, step));
  $$(".wizard-pane").forEach(p => p.classList.toggle("active", Number(p.dataset.step) === state.step));
  $$("#stepper span").forEach((s,i)=>s.classList.toggle("active", i+1 === state.step));
  $("#wizardBack").hidden = state.step === 1; $("#wizardNext").hidden = state.step === 4; $("#startRun").hidden = state.step !== 4;
  if (state.step === 4) renderConfirmation();
}
function formPayload() {
  const data = new FormData($("#runForm"));
  const scope_mode=data.get("scope_mode");
  const payload={ scope_mode, region:scope_mode==="auto" ? data.get("auto_region") : data.get("region"), dataset_id:data.get("dataset_id"), max_simulations:Number(data.get("max_simulations")), max_rounds:Number(data.get("max_rounds")) };
  if (scope_mode !== "auto") Object.assign(payload, {delay:Number(data.get("delay")), universe:data.get("universe"), neutralization:data.get("neutralization")});
  return payload;
}
function renderConfirmation() {
  const p=formPayload(), values = [["MODE",p.scope_mode],["REGION",p.region],["DELAY",p.scope_mode==="auto"?"AUTO":p.delay],["UNIVERSE",p.scope_mode==="auto"?"AUTO":p.universe],["NEUTRALIZATION",p.scope_mode==="auto"?"AUTO":p.neutralization],["DATASET",p.dataset_id],["TERMINATION",`${p.max_simulations} sims · ${p.max_rounds} rounds`]];
  $("#runConfirm").innerHTML = values.map(([k,v])=>`<div><small>${k}</small><strong>${esc(v)}</strong></div>`).join("");
}
async function startRun(event) {
  event.preventDefault(); const payload=formPayload();
  if (payload.max_simulations < 1 || payload.max_rounds < 1) return toast("终止条件必须大于 0");
  $("#startRun").disabled = true;
  try { const result=await api("/api/runs",{method:"POST",body:payload}); state.currentRun=result.run_id; toast("研究已启动"); await refreshAll(); showView("run"); }
  catch(error){toast(error.message);} finally{$("#startRun").disabled=false;}
}

async function checkAuth() {
  $("#authResult").textContent="正在检查…";
  try { const result=await api("/api/auth/status"); const ok=result.authenticated===true; $("#authResult").textContent=ok?"会话有效":"会话无效"; $("#authTag").textContent=ok?"AUTHENTICATED":"NOT AUTHENTICATED"; }
  catch(error){$("#authResult").textContent=error.message;}
}
async function loginAuth() {
  const email=$("#authEmail").value, password=$("#authPassword").value; $("#loginAuth").disabled=true;
  try { await api("/api/auth/login",{method:"POST",body:{email,password,expiry:3600}}); $("#authPassword").value=""; toast("登录成功，Cookie 已保存"); await refreshAll(); }
  catch(error){toast(error.message);} finally{$("#loginAuth").disabled=false;}
}

function bindEvents() {
  $$('[data-view]').forEach(el=>el.addEventListener("click",e=>{e.preventDefault();showView(el.dataset.view);}));
  $("#modalClose").addEventListener("click",closeModal); $("#modal").addEventListener("click",e=>{if(e.target.id==="modal")closeModal();});
  $("#refreshHome").addEventListener("click",()=>refreshAll().catch(e=>toast(e.message)));
  $("#runSelect").addEventListener("change",e=>{state.currentRun=e.target.value;state.detail=null;state.detailSignature=null;loadCurrentRun();});
  $("#historyFilter").addEventListener("change",renderHistory);
  $("#logFilter").addEventListener("change",e=>{state.logFilter=e.target.value;renderLogs(state.detail);});
  $("#ideaList").addEventListener("click", event => {
    const button = event.target.closest("[data-idea-action]");
    const card = event.target.closest("[data-idea-id]");
    if (button && card) ideaAction(card.dataset.ideaId, button.dataset.ideaAction);
  });
  $("#copyLog").addEventListener("click",async()=>{await navigator.clipboard.writeText($("#logWindow").innerText);toast("日志已复制");});
  $("#wizardBack").addEventListener("click",()=>setWizardStep(state.step-1)); $("#wizardNext").addEventListener("click",()=>setWizardStep(state.step+1));
  $('[name="region"]').addEventListener("change", updateDependentScopeOptions);
  $('[name="delay"]').addEventListener("change", loadDatasetChoices); $('[name="universe"]').addEventListener("change", loadDatasetChoices);
  $('[name="auto_region"]').addEventListener("change", loadDatasetChoices);
  $('[name="dataset_category"]').addEventListener("change", () => renderDatasetChoices());
  $("#refreshScopeOptions").addEventListener("click", refreshScopeOptions);
  $$('input[name="scope_mode"]').forEach(el=>el.addEventListener("change",()=>{ $$(".choice").forEach(c=>c.classList.toggle("selected",c.querySelector("input").checked)); const auto=$("input[name=scope_mode]:checked").value==="auto"; $("#manualScope").hidden=auto; $("#autoScope").hidden=!auto; loadDatasetChoices(); }));
  $("#runForm").addEventListener("submit",startRun); $("#checkAuth").addEventListener("click",checkAuth); $("#loginAuth").addEventListener("click",loginAuth);
}

async function init() {
  bindEvents(); setWizardStep(1);
  try { await refreshAll(); const hash=location.hash.slice(1); if (["home","new","run","history","settings"].includes(hash)) showView(hash); }
  catch(error){$("#apiState").textContent="API ERROR";$("#apiState").className="status-dot fail";toast(error.message);}
}
init();
