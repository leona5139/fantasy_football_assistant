# Fantasy Football Assistant — Improvement Plan

## Context

The repo currently contains four disconnected, CLI/Streamlit scripts sharing only a static player CSV: a greedy VBD draft assistant (`project/draft/greedy.py`), an MCTS draft assistant (`project/draft/mcts.py`), a Streamlit weekly waiver/roster dashboard (`project/management/`), and a broken standalone playoff-odds calculator. There's no shared package, no dependency manifest, no tests, and no packaging — every tool is `python x.py` with typed `input()`.

Five improvements are planned: (1) faster/smarter draft recommendations via parallelization and precomputation, (2) a light webapp replacing the typed-CLI draft experience with autocomplete and visuals, (3) a weekly management tool that actually gives explicit recommendations instead of raw tags nobody acted on last year, (4) an LLM-powered trade analyzer, (5) friendly macOS packaging for a non-technical end user.

**Hard constraint discovered during scoping (as of 2026-08-20):** (1) and (2), packaged for macOS, need to reach a non-technical friend **by Sunday 2026-08-23** for that weekend's draft — and neither the repo owner nor the assistant doing this work has Mac access to test on. (3), (4), and (5)-full-polish are explicitly OK to land after draft season. This plan is split into a **Phase 0 Sunday scope** and a **Phase 1+ roadmap**, so the urgent slice stays realistic and everything else isn't lost.

Key decisions locked in:
- Draft stays manual-entry (mirror picks from whatever platform is used to draft) — no live platform sync.
- League default: 10-team, PPR, standard roster — but editable in a setup screen, since baselines are currently hardcoded in `greedy.py`.
- Player data must be **live** for 2026 (current `cleaned_data.csv` is a stale one-time snapshot from the initial commit) — pull from a free API rather than another manual export.
- Distribution is single-user (one friend) — no Apple notarization needed, but Gatekeeper's "unidentified developer" warning still applies and must be documented for a non-technical user.
- No Mac available for testing before handoff — this pushes weight onto CI-based automated verification (build **and** smoke-test the binary in GitHub Actions) since nobody can manually verify a double-click.

---

## Phase 0 — Sunday deadline (draft tool + webapp + macOS package)

### 0.1 Live 2026 player data (do this first — it's the biggest unknown)
Replace the static `project/data/cleaned_data.csv` pipeline with a live pull, reusing the pattern already proven in `project/management/data_generation.py` (`nfl_data_py` calls).

- Research spike (timebox: half a day): check whether `nfl_data_py` exposes real preseason fantasy **projections/ADP** (not just historical weekly stats — that's what it's used for today). If it doesn't, fall back to the free, no-auth **Sleeper API** (`api.sleeper.app`), which exposes player metadata and ADP/trending data and is widely used by fantasy tools.
- **Fallback if neither pans out fast enough:** keep the existing manual-CSV path (`project/data/clean_player_data.py`) as a documented escape hatch so a bad data source doesn't blow the Sunday deadline — hand-export current rankings as a last resort.
- Output: a `project/data/live_rankings.py` module producing the same shape `cleaned_data.csv` already has (`Rank, Total_FPTS, Average_FPTS, Player, Team, Position`), so `greedy.py`/`mcts.py` don't need to change their data contract.

### 0.2 Draft engine: parallelization + precomputation
Refactor `project/draft/greedy.py` and `project/draft/mcts.py` out of their `input()`-driven CLI loops into importable classes/functions (needed for the webapp anyway), then:

- **Precompute once per draft session, not per pick:** replacement baselines and static VORP components (`establish_replacement_baselines` in `greedy.py`) already run once at init — verify this and cache the derived scores; replace the `iterrows()` scan in `get_best_player` with a vectorized pandas/numpy pass so the webapp feels instant on every "who should I take" refresh.
- **Parallelize MCTS via root parallelization:** run N independent MCTS searches (one per CPU core) using `concurrent.futures.ProcessPoolExecutor`, each within the same time budget, then merge by summing visit counts across trees for the final recommendation. This is the safe/bounded way to parallelize MCTS (no shared mutable state, no risk of subtle concurrency bugs) and directly buys either faster answers or more playouts in the same wall-clock time.
- **Explicitly out of scope for Sunday** (defer to Phase 1): cross-pick tree reuse, pre-draft mock-simulation prior tables. Note them in code comments/TODO so they're not forgotten.
- Expose both engines behind one API: `greedy` as the instant default recommendation, MCTS as an optional "think harder" button with a shorter budget than today's 30s (parallelization should let ~10–15s match or beat today's single-threaded 30s).

### 0.3 Light webapp
Backend: **FastAPI + Uvicorn**, wrapping the refactored draft classes. Frontend: **plain HTML/CSS/vanilla JS** — no React/Node build step. This is a deliberate simplicity choice: a Node toolchain adds real packaging risk on a 3-day deadline with no way to test, and the ask is "light webapp," not a SPA.

- Setup screen: team count, scoring (PPR/half/standard), roster slots — defaults to 10-team PPR standard, editable, feeds the baseline calculation from 0.2.
- Draft board screen:
  - Player search box with **client-side type-ahead** against the (small, ~200-300 row) preloaded player list — solves "don't make me type the exact full name" without server round-trips.
  - "Recommended pick" panel showing top 3-5 greedy suggestions plus reasoning (VORP, positional scarcity), and a "think harder" button for the parallel MCTS pick.
  - Simple visuals: horizontal bar list of top candidates by score, a positional-scarcity indicator — plain CSS/SVG, no external charting library (avoids CDN/offline issues in a packaged app).
  - Actions to mark a player drafted (by you or an opponent) and undo.
- New files: `project/webapp/server.py`, `project/webapp/api/draft.py`, `project/webapp/static/{index.html,app.js,styles.css}`.

### 0.4 macOS packaging (built via CI, not locally)
PyInstaller cannot cross-compile, so packaging happens on GitHub's `macos-latest`/`macos-13` runners (repo already has a GitHub remote: `github.com/leona5139/fantasy_football_assistant`).

- `packaging/launcher.py`: starts Uvicorn on localhost in the background, then opens the default browser via `webbrowser.open`.
- `packaging/app.spec`: PyInstaller spec, `--windowed`, bundling the static frontend assets.
- `.github/workflows/build-macos.yml`: matrix build on **both `macos-13` (Intel/x86_64) and `macos-14`/`macos-latest` (Apple Silicon/arm64)** — since nobody can test locally, we can't afford to guess the friend's Mac chip wrong. Produces two downloadable `.app` zips.
- **CI smoke test (critical given no manual Mac testing):** after building, run the packaged binary headlessly on the runner, curl a `/health` endpoint, assert a 200/expected JSON response, then kill the process. This is the closest substitute we have for "someone tried it on a real Mac" before it reaches the friend.
- Handoff doc (`packaging/HANDOFF.md`): plain-language instructions for a non-technical user — which zip to pick (Apple Silicon vs Intel, with a one-line "how to check" via Apple menu → About This Mac), and the **right-click → Open** workaround for Gatekeeper's unidentified-developer warning (plus an `xattr -d com.apple.quarantine` fallback command if right-click → Open still refuses).
- `requirements.txt`: formalize dependencies (none exist today) — needed for both CI and PyInstaller to resolve a consistent environment.

### 0.5 Verification for Phase 0
- Unit tests (new `project/tests/`) for the vectorized greedy scoring and the parallel MCTS aggregation — compare against the original single-threaded output on a fixed seed to confirm parallelization doesn't change recommendation quality, only speed.
- Manual local run: `uvicorn project.webapp.server:app` locally, exercise the draft flow end-to-end in a browser (search, recommend, mark-drafted, think-harder) before ever pushing to CI.
- GitHub Actions run: confirm both architecture builds succeed and the smoke test passes — this is the actual go/no-go gate for sending the app to the friend, since it's the only verification available before handoff.

---

## Phase 1+ — after draft season (no hard deadline)

### 1. Weekly management tool rebuild
Replace the current "tags you interpret yourself" output (`project/management/dashboard.py`, `dashboard_utils.py`) with **explicit ranked recommendations, 2-3 candidates per slot, with reasoning shown**, instead of a single forced call or plain tags.

- Fix the real gaps found during exploration: there's currently no kicker-specific signal at all (kickers just inherit the generic `favored_flag`/`pace_flag`) despite the intended "K based on Vegas point totals" behavior — build a real one from `total_line`/team implied totals in `data_generation.py`. Similarly, "FLEX based on waiver pickups" today is just the generic waiver table filtered by position — add real logic (recent-usage trend + matchup + scarcity) that ranks FLEX-eligible waiver options rather than just listing them.
- Turn the existing flags (`favored_flag`, `pace_flag`, `fpts_trend_flag`, `consistency_flag`, `upcoming_favored_flag`) into a composite score per candidate, and surface the top 2-3 with a plain-language reasoning string built from which flags drove the score.
- Decide during Phase 1 kickoff whether this stays in Streamlit or moves into the same FastAPI webapp from Phase 0 for a consistent experience — leaning toward folding it into the webapp once there's no more time pressure.

### 2. Trade analysis tool (LLM-powered)
- Research free/low-cost LLM APIs suitable for occasional single-user trade analysis (not a redistributed public app, so a user-supplied API key entered in a settings screen is the simplest safe pattern — avoids paying for someone else's usage and avoids bundling a secret in a distributed binary).
- Design: feed both sides of a proposed trade (players, recent performance, ROS outlook reused from the weekly tool's signals) to the LLM, request a structured recommendation + reasoning, render in the webapp.
- No LLM usage or API-key handling exists anywhere in the repo today — this is greenfield, including `.env`/config handling for the key.

### 3. Full packaging polish
- Fold the weekly tool and trade tool into the same packaged webapp from Phase 0 so there's one app, not three.
- Revisit notarization/code-signing only if distribution scope grows beyond a single friend.

---

## Critical files touched
- `project/draft/greedy.py`, `project/draft/mcts.py` — refactor to importable + parallelized/vectorized
- `project/data/clean_player_data.py`, new `project/data/live_rankings.py` — live data source
- New `project/webapp/` — FastAPI backend + static frontend
- New `packaging/` — PyInstaller spec, launcher, handoff doc
- New `.github/workflows/build-macos.yml` — CI build + smoke test
- New `requirements.txt`
- New `project/tests/` — parallelization/vectorization regression tests
- `project/management/data_generation.py`, `dashboard.py` — Phase 1 rebuild
