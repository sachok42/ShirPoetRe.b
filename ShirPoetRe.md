# Final Review — ShirPoetRe

**Team:** Roman Roginskii (`sachok42`), Mikhail Morozov (`ThomasLemann`), Yura Kabkov (`hedgegogg`), Abdurahim Ismoilov (`iaraha`)
**Repository:** `sachok42/ShirPoetRe.b`
**Project:** ShirPoetRe.b — a Qt6 (PySide6) poetry writing environment combining a distraction-free text IDE with linguistic analysis (stress, rhyme, meter via CMU Pronouncing Dictionary + TextBlob) and neural poem generation (evolved from dummy predictor → n-gram → transformer → PyTorch Bi-LSTM).
**Semester:** 2026, weeks 16–21 (activity window 2026-04-19 → 2026-05-18)
**Grading formula:** `FinalGrade(student) = Presentation(student) + ProjectTeamScore × ContributionCoeff(student)`

---

## Final Grades

| Student | Presentation | ProjectTeamScore | ContributionCoeff | FinalGrade |
|---|---|---|---|---|
| Mikhail Morozov  | 30 / 30 | 55.5 / 70 | 1.0 | **85.5 / 100** |
| Roman Roginskii  | 30 / 30 | 55.5 / 70 | 1.0 | **85.5 / 100** |
| Yura Kabkov      | 30 / 30 | 55.5 / 70 | 1.0 | **85.5 / 100** |
| Abdurahim Ismoilov | 30 / 30 | 55.5 / 70 | 0.4 | **52.2 / 100** |

---

## ProjectTeamScore — 55.5 / 70

### Result + Quality — 38.5 / 45

Six rubric items, equal weights (7.5 each).

| # | Item | Score |
|---|---|---|
| 1 | User stories end-to-end (demoable, ≥ 2·N = 8) | 7.5 / 7.5 |
| 2 | Used minimum 2 from the "possible topics" list | 7.5 / 7.5 |
| 3 | Reproducible run + config template | 6.5 / 7.5 |
| 4 | Automated checks in CI | 3.5 / 7.5 |
| 5 | Architecture documentation | 6.5 / 7.5 |
| 6 | Codebase coherence | 7 / 7.5 |

- **Item 1.** 18 demoable user stories against the team's threshold of 8: 8 writing-environment features (cursor position, line numbers, dark/light theme, focus mode, real-time word/char counters, file ops, file explorer, .txt export), 7 NLP analysis features (stress highlighting, rhyme detection, rhyme schemes, grammar errors, meter visualization, stylistic fit, rhyme/rhythm repair), and 3 neural network features (poem-start generation, line continuation preserving rhyme/stress/style, word-level suggestions).
- **Item 2.** Self-suggested complex stack: PySide6 (Qt6) cross-platform GUI, PyTorch Bi-LSTM poetry generator with transformer evolution, CMU Pronouncing Dictionary integration for phonetics, TextBlob NLP for grammar, eng-to-ipa phonetic transcription, NLTK, n-gram language modeling, property-based testing via Hypothesis, pytest-qt for GUI tests.
- **Item 3 (6.5 / 7.5).** `requirements.txt` covers all 10 dependencies (PySide6, torch, numpy, pronouncing, eng-to-ipa, nltk, textblob, pytest, pytest-qt, hypothesis). The reduction is for the thin README: "Execute via launching src/main.py" plus "Requirements are listed in requirements.txt" is the entire installation guidance — no venv creation steps, no Python version specified, no setup explanation. The README also states "Is guaranteed to work on Ubuntu", imposing an OS constraint without a Docker fallback.
- **Item 4 (3.5 / 7.5).** The methodology requires "checks **in CI**". `.github/workflows/` is absent. But 247 LOC of `pytest-qt` GUI tests plus `from hypothesis import given, strategies as st` in `src/rhyme_analysis.py` show property-based testing was set up — test discipline exists at the content level, even though the suite doesn't run automatically. A 30-line `ci.yml` running `pytest` would have unlocked the remainder.
- **Item 5 (6.5 / 7.5).** The methodology asks for two things — a simple system diagram **and** module/service responsibilities. The team delivered the second part: README "Use Cases" section categorizes capability by layer (Writing Environment, NLP, Neural Network), and in-module docstrings throughout `src/rhyme_analysis.py`, `src/text_IDE.py` cover sub-component responsibilities. What is missing is a system-level visual diagram and an in-repo `architecture.md` or `docs/` directory. For the next project: a simple ASCII or Mermaid diagram in README — one box per layer with arrows showing data flow (text input → tokenize → stress/rhyme analysis → annotation overlay; or input → model → next-word suggestions) — completes this rubric item. The diagram doesn't need to be polished; it needs to exist.
- **Item 6 (7 / 7.5).** 18 modules at 2772 LOC with type hints (`Optional[str]`, `list[str]`), frozen dataclasses, Levenshtein distance for rhyme matching (DP implementation in `rhyme_analysis.py:36-51`), property-based testing imports, graceful fallback for optional dependencies (`pronouncing`, `textblob`), clean NLP/UI layering (pure analysis functions tested without `pytest-qt`). The small reduction is for integration smells visible in the repo: two duplicate entry points (`src/main.py` + `rahas_main.py`), an `archive/` directory still containing old `main.py`/`tests.py`/`new_version.py`, and parallel codepaths (`window.py` vs `text_IDE.py`; three `words_rhyme` variants). These are housekeeping issues from late-sprint integration, not architectural defects — the architecture itself is sound.
        
### Development Process — 17 / 25

Six rubric items, weighted by importance (sum = 25).

| # | Item | Score |
|---|---|---|
| 1 | Tracker as source of truth | 5 / 5 |
| 2 | Issue ↔ PR link | 1 / 4 |
| 3 | Small, regular deliveries | 5 / 6 |
| 4 | PR workflow enforced | 3 / 3 |
| 5 | Code review required | 3 / 3 |
| 6 | CI as merge gate | **0 / 4** |

- **Item 1 (5 / 5).** 40 issues with 39 closed — a strong issue volume and closure rate. Assignees are present (12 of 40, with Roman as the primary tracker owner at 10 issues). Status is tracked through the open/closed mechanism, which is fine — the methodology did not stipulate a particular status convention.
- **Item 2 (1 / 4).** 0 of 23 PRs use formal `Closes #N` syntax. Without labels for grouping or branch-name patterns to detect, the proportion of semantically linkable PRs is under 20%.
- **Item 3 (5 / 6).** 6 active ISO weeks (16-21) with merges in each — the methodology's "1 PR per week per team" requirement is met within the active project window. The small reduction reflects the 11 empty pre-semester weeks: no PRs from semester start (2026-02-01) until 2026-04-19. Once the team started, work was distributed weekly, but the project effectively used only the final month. See also Team Note: Late Project Start.
- **Item 5 (3 / 3).** 16 of 23 merged PRs (70%) have at least one external human review — strong peer-review coverage. Mikhail and Yura contributed the substantive reviews (8 meaningful between them).
- **Item 6 (0 / 4).** No `.github/workflows/` — same structural absence as in R+Q-§4.

---

## Per-Student Evidence

### Mikhail Morozov (`ThomasLemann`) — 1.0

**Domain owner:** Qt6 PySide6 GUI workstream (text editor, tabs, focus mode, themes, counters).

**Merged PRs (semester window): 7 / 5 ✓**

Timeline:
- Week 16 (Apr 19): PR #6 "First version of software on Pyside6".
- Week 17 (Apr 26): PR #10 "New version with Light/Dark theme and pointer position".
- Week 19 (May 7): PR #13 "Add Word and Char counters, correct counter update on multiple files".
- Week 20 (May 13): PR #14 "Add Focus Mode".
- Week 20 (May 15): PR #15 "Added tests for application. Changed a bit the usage of F12".
- Week 20 (May 16): PR #22 "Add work with multiple files simultaneously (tabs)".
- Week 20 (May 17): PR #60 "Added some tests for GUI. Check also tests from the previous".

You're the only team member with sustained weekly cadence from project start (April 19) to project end (May 17). You carry the entire GUI workstream: foundational Qt6 setup, theme system, focus mode, counters, multi-file tabs, and the team's GUI testing infrastructure.

**Issues (closed as assignee): 2 / 5 ✗** — under threshold but balanced with strong PR count.
**Reviews: 5 / 5 ✓**.

**Code Feedback.**
- Sustained weekly cadence Feb 12 README iterations → Apr 5 "First version of software on Pyside6" → continuous feature work May 7 / May 13 / May 15 / May 16 / May 17. This is exactly the "1 PR per 1-2 weeks" pattern the methodology asks for as the default.
- Qt6 GUI stack delivered: `src/text_IDE.py` (324 LOC), `src/window.py` (300 LOC), `src/my_text_edit.py` (317 LOC) — modular GUI workstream with clean concern separation.
- Full IDE-like feature set: multi-file tabs (PR #22), theme system (PR #10), focus mode (PR #14), counters (PR #13), pytest-qt GUI tests (PR #15, #60). You built the testing infrastructure the team uses.
- **To improve.** The pytest-qt tests you added don't run automatically because `.github/workflows/` is empty. A single 30-line `ci.yml` running `pytest` on PR would unlock R+Q §4 (+4) and DP §6 (+4), for +8 to PTS — the largest single-action improvement available to this team. The tests are there; only the trigger is missing.

### Roman Roginskii (`sachok42`) — 1.0

**Domain owner:** Code restructuring + UI integration + analysis layer.

**Merged PRs (semester window): 7 / 5 ✓**

Timeline:
- Week 20 (May 16): PR #8 "rhyming logic and gapfill", #18 "first_draft", #20 "strcturized_the_code".
- Week 20 (May 17): PR #56 "UI_with_analysis (befriending)", #58 "Recstucturized the UI into separate files".
- Week 21 (May 18): PR #61 "sometesting", #64 "mergingtwouniverses".

All 7 authored PRs landed in a 3-day window — but you also created the project repository (`Initial commit` 2026-02-12, semester week 6). The team-enabling work (repo creation, initial structure) happened in February even though your feature PRs concentrated at the end.

**Issues (closed as assignee): 10 / 5 ✓** — primary tracker owner.
**Reviews: 2 / 5 ✗** — 2 of 15 classified as meaningful.

**Code Feedback.**
- You created the project repository (`Initial commit` 2026-02-12) — invisible team-enabling work.
- Primary tracker user — 10 of 12 assigned issues on the team.
- Restructuring PRs (#20 "strcturized_the_code", #58 "Recstucturized the UI into separate files") — integration work that prepared the codebase for the multi-author merge. Restructuring is harder to credit than features but is the work that makes features composable.
- **To improve.** All 7 authored PRs in a 3-day window even though you created the repo in February. For the next project: open a **draft PR per feature on day 1** — even an empty stub PR. The team can review your interface contracts incrementally. Also PR titles like "first_draft", "strcturized_the_code", "UI_with_analysis (befriending)", "mergingtwouniverses" — colorful, but six months from now you yourself won't remember what each meant. Conventional Commits style (`refactor:`, `feat:`, `fix:`) takes the same number of characters and survives time.

### Yura Kabkov (`hedgegogg`) — 1.0

**Domain owner:** Neural poetry model.

**Merged PRs (semester window): 6 / 5 ✓**

Timeline (cleanly mapped to ML model evolution):
- Week 16 (Apr 19): PR #5 "Updated README, added one new feature, improved clarity".
- Week 18 (Apr 30): PR #7 "Add basic model interface with dummy next-word predictor".
- Week 20 (May 13): PR #9 "Update model vocab loading and notebook pipeline", #11 "Improve dummy poetry model with lightweight n-gram training", #12 "Changed model's architecture to the transformer".
- Week 21 (May 18): PR #57 "Revised architecture, rewritten on Pytorch".

The PRs trace a deliberate progression: README updates → dummy predictor → vocab + n-gram → transformer → PyTorch rewrite. This is the entire ML/NLP workstream of the project, delivered across 4 distinct ISO weeks (16, 18, 20, 21) with regular cadence — the methodology's "1 PR per 1-2 weeks" definition matched.

**Issues (closed as assignee): 0 / 5 ✗**.
**Reviews: 3 meaningful** on PR #6 (110-char body), PR #8 (CHANGES_REQUESTED with 48-char body), PR #15 (40-char body).

**Code Feedback.**
- Distributed cadence across 4 ISO weeks (Apr 19 → May 18) — the methodology's "1 PR per 1-2 weeks" pattern.
- Sequential ML evolution documented in PR titles: dummy predictor → n-gram → transformer → PyTorch Bi-LSTM. You iterated through approaches rather than trying to write the final model from scratch — that's the right learning approach for an unfamiliar domain.
- Substantive reviews on teammates' PRs (CHANGES_REQUESTED with rationale, APPROVED with substance).
- You also contributed to a different team's repository (cross-team helpfulness) — a positive qualitative signal of cohort-level collaboration.
- **To improve.** Model architecture decisions documented in PR descriptions would be useful for future contributors — what data did the n-gram → transformer transition unblock? What did Bi-LSTM choose to capture that earlier models couldn't? A short paragraph in each PR body explaining the *why* (not just the diff) turns commits into a tutorial others can learn from.

### Abdurahim Ismoilov (`iaraha`) — 0.4

**Merged PRs (semester window): 3 / 5 ✗** — all 3 within a single day (2026-05-18).

- PR #59 "Merged everything into final working file".
- PR #62 "Project X: everything is AI".
- PR #63 "Added both basic and rare words to suggestion".

Your earliest commit on `main` is 2026-05-15 — already inside the team's late-sprint window. Your PRs are substantive (word-suggestion improvement, AI integration, final merge) but the engagement window is the sprint itself, not the semester.

**Issues (closed as assignee): 0 / 5 ✗**.
**Reviews: 1 / 5 ✗**.

**Code Feedback.**
- `rahas_main.py` — an alternative launcher with additional imports — shows an attempt at an independent contribution path.
- PR #62 "Project X: everything is AI", PR #63 "Added both basic and rare words to suggestion" — actual feature additions, not just config-file touchups.
- **To improve.** Three PRs across three calendar days (May 15-18) — you joined the project at the very end. For the next project: even if you onboard onto a team late, ask for a **narrow scope (one feature)** and work on it steadily from the moment you join, not as a single push at the deadline. Also `rahas_main.py` duplicates `src/main.py` — one file with CLI args (`--mode standard|alternate`) is cleaner than two launchers; the docstring on `src/app.py` ("previously in a separate launcher") suggests your launcher's work was absorbed into Mikhail's main, which is the wrong direction of integration.

---

## Team Note: Late Project Start

No merged PRs landed before 2026-04-19. The first 11 weeks of the semester (weeks 5–15 of 2026) are structurally empty in the repository. The team then maintained ~1 PR per week from April 19 to May 13, and ramped to 12 PRs in week 20 and 6 PRs in week 21.

The pattern is not "one gap in normal work" — it is "the team formed and started working only in the final 4–5 weeks". DP-§3 (5/6) reflects this with partial credit: weekly cadence was achieved within the active window, but the project effectively used only the final month rather than the full semester.

**For subsequent projects:** start earlier, even with small PRs. The two duplicate entry-point files (`src/main.py` + `rahas_main.py`) and the `archive/` directory are visible traces of the late-stage integration crunch — those wouldn't exist if interface contracts had been pinned down in the first few weeks.

## Team Note: CI as the missing 8-point unlock

The team has tests (247 LOC pytest-qt + Hypothesis property-based testing imports) but no `.github/workflows/`. A 30-line `ci.yml` would unlock R+Q-§4 (+4) and DP-§6 (+4), for a total +8 to PTS. The content is present; only the trigger is missing.

---

## Additional Code Review Findings

A thorough code review of the codebase surfaced critical product-quality issues — several headline features have bugs that should be fixed before shipping.

**What works well:**
- 29 tests pass in ~2.5s. One test is deselected: `test_focus_mode_toggle` hangs forever because `toggle_focus_mode` calls `QMessageBox.information(...)` modally, which never auto-dismisses in headless mode. This hanging test would also block any future CI.
- Clean layered NLP/UI separation — pure functions tested without `pytest-qt`.
- Bi-LSTM architecture correctly factored (`ReemaModelConfig` / `ReemaBiLSTMPoemGenerator` / `PoetryNextWordModel`) with proper torch-optional graceful degradation (`TORCH_AVAILABLE` flag).
- Inline annotation rendering does not overlap text — custom `paintEvent` reserves a gutter column for badges and paints to the right of the last glyph (`my_text_edit.py:202-318`).
- ZIP extraction is path-traversal safe (`_zip_member_is_safe`, `model/__init__.py:124-132`).
- Style scoring is a real weighted heuristic, not random (`style_analysis.py:33-50`).
- Debounced auto-analysis (600 ms timer, both editor-event and bulk-AI paths converge on one timer).

**Note on tests:** depth is shallow — most assertions are `isinstance(x, list)` or `len >= 1`. The tests would not catch the headline bugs below. Hypothesis is imported but every `@given` decorator in the codebase is commented out (`rhyme_analysis.py:6, 11, 27, …`).

**Critical findings (product-quality, fix these before shipping):**

1. **Meter detection is broken on iambic pentameter.** `rhythm_analysis.py:25-35`. Verified on Shakespeare's "Shall I compare thee to a summer's day" — stress string `"11011101011"` → reported foot **"spondee"** instead of iambic. Headline feature broken on canonical input. Root cause: monosyllabic function words ("shall", "thee", "to") all get CMU stress="1", so adjacent "1"s outvote iambs. Fix: collapse function-word stress before voting, or use a longer rolling window when classifying feet.
2. **The neural model has no weights on a fresh clone.** `model/__init__.py:688`. `model/data.zip` (19 MB) existed in history — added by Yura, removed in commit `6ac00d8` ("Almost working product") by Abdurahim. On a fresh clone `is_fitted()=False`, vocab is the 10-word FALLBACK list, `predict()` returns `[]`, `generate()` returns the input unchanged. **All AI features silently no-op.** Fix: either ship `data.zip` (Git LFS or release asset), or document that the user must train via the README's training procedure before AI features work.
3. **`test_focus_mode_toggle` hangs the whole suite forever.** `test/test_text_ide_gui.py:73-78`. The test invokes `toggle_focus_mode` which calls `QMessageBox.information(...)` modally; in headless mode this dialog never auto-dismisses. Until fixed, no CI can pass. Fix: patch `QMessageBox.information` with `unittest.mock` in the test, or use `pytest-qt`'s `qtbot` to dismiss programmatically.
4. **Cyrillic is silently stripped from analysis.** `src/utils.py:55` uses `[a-zA-Z]+` while `src/poetry_tools.py:20` uses a Cyrillic-aware regex. The README's `Ёё` and Russian context suggest support was intended, but the analysis pipeline drops every non-ASCII letter. Fix: replace `[a-zA-Z]+` with `[a-zA-Zа-яА-ЯёЁ]+` (or use `\w` with `re.UNICODE`).
5. **`pronouncing._cmu_entries()` private API doesn't exist in the installed version.** `improved_rhyme_matching.py:132`, `my_text_edit.py:44-49`. Both call sites silently fall to `except`. The "soft-rhyme fallback when CMU exact list is thin" never executes. Fix: use the public `pronouncing.phones_for_word` + iterate the CMU dict yourself, or vendor a minimal CMU subset.

**Additional coherence issues worth fixing** (visible in the codebase): two parallel `TextIDE` / `MyTextEdit` / `LineNumberArea` implementations (`window.py` vs `text_IDE.py` + helpers); three parallel `words_rhyme` codepaths with different answers on the identical-word edge case; two `suggest_rhyme_repairs` functions; the `archive/` directory has three further generations (`src/`, `src2/`, `src3/`); `src/window.py` and `src/rhyme_repair.py` are live dead code inside the active package.

**NLP correctness summary:** rhyme detection works (`kiss/miss`, `boat/note`, `cat/hat`, `love/dove`, `soft_rhyme(love, above)=True`, `soft_rhyme(orange, door)=False`); rhyme-scheme ABAB detects correctly; stress highlighting is technically correct but inherits the function-word issue that breaks meter; meter analysis is broken; generation is dead because weights aren't shipped; Cyrillic is silently dropped.

All findings above include file:line references and concrete fixes.
