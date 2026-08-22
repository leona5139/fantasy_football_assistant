"use strict";

const state = {
  players: [],
  session: null,
  selectedPlayer: null,
};

async function api(method, path, body) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const resp = await fetch(path, opts);
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(data.detail || `Request to ${path} failed (${resp.status})`);
  }
  return data;
}

function el(id) {
  return document.getElementById(id);
}

// ---- Setup screen ----

async function populateRosterDefaults() {
  const defaults = await api("GET", "/api/config/defaults");
  const container = el("roster-slots-fields");
  container.innerHTML = "";
  for (const [pos, count] of Object.entries(defaults.roster_slots)) {
    const wrapper = document.createElement("div");
    wrapper.className = "roster-slot-field";
    const label = document.createElement("label");
    label.textContent = pos;
    label.htmlFor = `roster_slot_${pos}`;
    const input = document.createElement("input");
    input.type = "number";
    input.min = "0";
    input.max = "10";
    input.value = count;
    input.id = `roster_slot_${pos}`;
    input.dataset.pos = pos;
    wrapper.appendChild(label);
    wrapper.appendChild(input);
    container.appendChild(wrapper);
  }
}

function collectRosterSlots() {
  const inputs = document.querySelectorAll("#roster-slots-fields input");
  const slots = {};
  inputs.forEach((input) => {
    slots[input.dataset.pos] = Number(input.value);
  });
  return slots;
}

async function handleSetupSubmit(evt) {
  evt.preventDefault();
  const errorBox = el("setup-error");
  errorBox.hidden = true;
  el("setup-submit").disabled = true;
  el("setup-submit").textContent = "Starting...";

  try {
    const body = {
      num_teams: Number(el("num_teams").value),
      scoring: el("scoring").value,
      draft_style: el("draft_style").value,
      initial_pick: Number(el("initial_pick").value),
      roster_slots: collectRosterSlots(),
      bench_slots: Number(el("bench_slots").value),
    };
    state.session = await api("POST", "/api/session", body);
    el("setup-screen").hidden = true;
    el("draft-board").hidden = false;
    await refreshAll();
  } catch (err) {
    errorBox.textContent = err.message;
    errorBox.hidden = false;
  } finally {
    el("setup-submit").disabled = false;
    el("setup-submit").textContent = "Start Draft";
  }
}

// ---- Draft board ----

async function refreshAll() {
  const [players, sessionState] = await Promise.all([
    api("GET", "/api/players"),
    api("GET", "/api/state"),
  ]);
  state.players = players;
  state.session = sessionState;
  renderTurnBanner();
  renderScarcity();
  renderRoster();
  renderLog();
  clearSelection();
  await renderGreedy();
  el("mcts-panel").innerHTML = "";
}

function renderTurnBanner() {
  const s = state.session;
  const banner = el("turn-banner");
  if (s.draft_complete) {
    banner.textContent = "Draft complete!";
    banner.className = "complete";
    return;
  }
  banner.textContent = s.is_our_pick
    ? `Your pick! (Round ${s.current_round}, Pick ${s.current_pick})`
    : `Team ${s.current_team + 1}'s pick (Round ${s.current_round}, Pick ${s.current_pick})`;
  banner.className = s.is_our_pick ? "our-turn" : "opponent-turn";
}

function renderScarcity() {
  const container = el("scarcity-badges");
  container.innerHTML = "";
  const scarcity = state.session.positional_scarcity;
  for (const [pos, counts] of Object.entries(scarcity)) {
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = `${pos}: ${counts.remaining}/${counts.total} left`;
    container.appendChild(badge);
  }
}

function renderRoster() {
  const list = el("our-roster");
  list.innerHTML = "";
  for (const player of state.session.our_roster) {
    const li = document.createElement("li");
    li.textContent = `${player.Player} (${player.Position}, ${player.Team}) - ${player.Total_FPTS.toFixed(1)} pts`;
    list.appendChild(li);
  }
  el("roster-value").textContent = `- value: ${state.session.our_roster_value.toFixed(1)}`;
}

function renderLog() {
  const list = el("draft-log");
  list.innerHTML = "";
  const history = [...state.session.pick_history].reverse();
  for (const entry of history) {
    const li = document.createElement("li");
    const who = entry.is_ours ? "You" : `Team ${entry.team_idx + 1}`;
    li.textContent = `Pick ${entry.pick_number} (Rd ${entry.round_num}): ${who} took ${entry.player.Player} (${entry.player.Position})`;
    list.appendChild(li);
  }
}

async function renderGreedy() {
  const panel = el("greedy-panel");
  if (state.session.draft_complete) {
    panel.innerHTML = "<p>Draft complete.</p>";
    return;
  }
  const data = await api("GET", "/api/recommend/greedy?n=5");
  panel.innerHTML = "";
  const maxVorp = Math.max(1, ...data.candidates.map((c) => c.vorp));

  for (const candidate of data.candidates) {
    const row = document.createElement("div");
    row.className = "candidate-row";

    const bar = document.createElement("div");
    bar.className = "bar";
    const fill = document.createElement("div");
    fill.className = "bar-fill";
    fill.style.width = `${Math.max(4, (candidate.vorp / maxVorp) * 100)}%`;
    bar.appendChild(fill);

    const label = document.createElement("div");
    label.className = "candidate-label";
    label.innerHTML = `<strong>${candidate.Player}</strong> (${candidate.Position}, ${candidate.Team}) &mdash; ${candidate.Total_FPTS.toFixed(1)} pts`;

    const reason = document.createElement("div");
    reason.className = "candidate-reason";
    reason.textContent = `VORP ${candidate.vorp.toFixed(1)} · need ${candidate.need_factor.toFixed(2)} · scarcity ${candidate.scarcity_factor.toFixed(2)} · quality ${candidate.quality_factor.toFixed(2)}`;

    const draftBtn = document.createElement("button");
    draftBtn.textContent = "Draft";
    draftBtn.addEventListener("click", () => draftPlayer(candidate.Player));

    row.appendChild(bar);
    row.appendChild(label);
    row.appendChild(reason);
    row.appendChild(draftBtn);
    panel.appendChild(row);
  }
}

async function handleThinkHarder() {
  const btn = el("think-harder-btn");
  const panel = el("mcts-panel");
  btn.disabled = true;
  btn.textContent = "Thinking... (~15s)";
  panel.innerHTML = "";
  try {
    const result = await api("POST", "/api/recommend/mcts");
    const card = document.createElement("div");
    card.className = "mcts-card";
    const p = result.player;
    card.innerHTML = `<strong>${p.Player}</strong> (${p.Position}, ${p.Team}) &mdash; ${p.Total_FPTS.toFixed(1)} pts`;
    const draftBtn = document.createElement("button");
    draftBtn.textContent = "Draft this player";
    draftBtn.addEventListener("click", () => draftPlayer(p.Player));
    card.appendChild(document.createElement("br"));
    card.appendChild(draftBtn);
    panel.appendChild(card);
  } catch (err) {
    panel.textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = "Think Harder (MCTS, ~15s)";
  }
}

// ---- Player search ----

function clearSelection() {
  state.selectedPlayer = null;
  el("selected-player").hidden = true;
  el("player-search").value = "";
  el("search-results").innerHTML = "";
}

function handleSearchInput() {
  const query = el("player-search").value.trim().toLowerCase();
  const results = el("search-results");
  results.innerHTML = "";
  if (!query) return;

  const matches = state.players
    .filter((p) => p.Player.toLowerCase().includes(query))
    .slice(0, 8);

  for (const player of matches) {
    const li = document.createElement("li");
    li.textContent = `${player.Player} (${player.Position}, ${player.Team})`;
    li.addEventListener("click", () => selectPlayer(player.Player));
    results.appendChild(li);
  }
}

function selectPlayer(name) {
  state.selectedPlayer = name;
  el("selected-player-name").textContent = name;
  el("selected-player").hidden = false;
  el("search-results").innerHTML = "";
  el("player-search").value = name;
}

async function draftPlayer(name) {
  await api("POST", "/api/pick", { player: name });
  await refreshAll();
}

// ---- Wiring ----

el("setup-form").addEventListener("submit", handleSetupSubmit);
el("player-search").addEventListener("input", handleSearchInput);
el("draft-selected-btn").addEventListener("click", () => {
  if (state.selectedPlayer) draftPlayer(state.selectedPlayer);
});
el("think-harder-btn").addEventListener("click", handleThinkHarder);
el("undo-btn").addEventListener("click", async () => {
  await api("POST", "/api/undo");
  await refreshAll();
});

populateRosterDefaults();
