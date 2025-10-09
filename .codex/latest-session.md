# Session 1 — 2025-09-25 09:38

## Topic
Relocate and redesign NPS scan progress bar in settings UI.

## User Desires
Make the NPS scan status more prominent and associated with the selected directory in the settings panel.

## Specifics of User Desires
- Move the existing NPS scan progress UI directly beneath the directory label in `gui.py`.
- Ensure the progress bar spans the width of the directory label, showing progress during scans.
- After completion, display a "NPS scan complete" label instead of the bar.
- Remove the old small progress indicator at the bottom of the settings panel while keeping signals intact.

## Actions Taken
- Reviewed repository instructions and prepared to modify `gui.py` accordingly.

## Helpful Hints
- Signals `nps_progress`, `nps_update`, and `nps_done` already manage state changes; only widget placement and behavior need adjustment.
---
# Session 2 — 2025-09-25 10:13

## Topic
Material-themed redesign of main window with inline scan progress.

## User Desires
Restyle the PySide6 GUI to feel modern and cohesive, embed scan progress within the settings pane, and keep every existing feature intact.

## Specifics of User Desires
- Apply a dark Fluent/Material theme with accent highlights and consistent styling for buttons, inputs, and lists.
- Group Scan/Auto-Arrange/Export into a prominent accent button row and introduce collapsible settings sections.
- Replace the modal `QProgressDialog` with an inline progress indicator and add search/sort enhancements to the library list.
- Polish tier cards with icons, shadows, and expand/collapse behavior while preserving drag-and-drop and double-click removal.

## Actions Taken
- Rebuilt `MainWindow.__init__` to create card-based panels, an accent action row, search toolbar, toolbox settings groups, and styled library summary/footer.
- Introduced a persistent dark theme stylesheet, refreshed tier card construction with toggles and icons, and added hover/rounded styling across widgets.
- Embedded a cancelable scan progress bar under the folder picker, wired new status update helpers, and removed the old `QProgressDialog` usage.
- Added library sorting modes, inline song count updates, enhanced NPS status framing, and ensured responsive sizing plus drop shadow polish.

## Helpful Hints
- Use `_update_scan_progress_value`, `_update_scan_status`, and `_reset_scan_progress_ui` when extending scan behaviors.
- Tier headers rely on `TIER_HEADER_COLORS`; adjust these arrays for alternate accent palettes.
- The library footer updates via `_update_library_summary()`—call it after any manual list mutations.
---

---
---
---

# Session 3 — 2025-09-25 10:15

## Topic
Rebalance main window layout widths and regroup settings controls.

## User Desires
Ensure the tier builder remains fully visible, keep settings from collapsing, and reorganize settings content into logical sections without losing functionality.

## Specifics of User Desires
- Tie the tier builder width to `TIER_COLUMNS * TIER_COLUMN_MIN_WIDTH` so tiers aren't truncated at launch and resize smoothly.
- Enforce sensible minimums for the workflow/settings column, keep the library column near `LIBRARY_MIN_WIDTH`, and adjust stretch factors.
- Replace the QToolBox accordion with Setup, Filters, and Rules groupings matching the requested control arrangements.

## Actions Taken
- Introduced `MainWindow._create_settings_section` to build styled sections and rebuilt the settings panel with Setup, Filters, and Rules groups per spec.
- Applied explicit minimum/maximum widths to the library, tier builder, and settings cards, updated `_update_size_constraints`, and set main layout stretch factors.
- Seeded tier scroll minimum widths from the column constants so the builder is fully visible initially and during resizing.

## Helpful Hints
- `_create_settings_section` centralizes styling for future settings groups—pass the desired layout class when adding new sections.
- `_update_size_constraints` re-applies card minimums after state changes; call it after altering column counts or resizes.
- Adjust `LIBRARY_MIN_WIDTH`, `SETTINGS_MIN_WIDTH`, or `TIER_COLUMN_MIN_WIDTH` for global layout tweaks without touching widget construction.
---

---
---
---

# Session 4 — 2025-09-25 10:45

## Topic
Rollback window refactor to material-themed baseline.

## User Desires
Restore the GUI implementation to the state captured in commit e07301b after being unhappy with later adjustments.

## Specifics of User Desires
- Discard the follow-up layout tweaks introduced after the material redesign.
- Ensure `gui.py` matches the visuals and logic present in commit e07301b.
- Keep all existing functionality intact after rolling back.

## Actions Taken
- Fetched upstream history to locate commit e07301b requested by the user.
- Checked out the `gui.py` snapshot from commit e07301b so the UI matches that baseline.
- Prepared to rerun compilation checks to confirm the project still builds.

## Helpful Hints
- Future tweaks should branch from commit e07301b to preserve the material-themed baseline the user prefers.
- Use `git fetch https://github.com/xdtrammell/CH-Career-Mode.git` to pull additional commits if more history is required.
---

---
---
---

# Session 5 — 2025-09-25 11:10

## Topic
Safeguard the tier builder width during startup and resizing.

## User Desires
Guarantee the window opens wide enough for all tier columns while preserving layout balance and fallback behavior when space is constrained.

## Specifics of User Desires
- Apply the main window minimum size before the initial resize so launch dimensions accommodate three tier columns.
- Re-run `_update_size_constraints()` after rebuilding tier widgets and resize the window when runtime changes drop below the minimum width.
- Provide horizontal scrolling as a fallback whenever the window ends up narrower than required so columns never disappear silently.

## Actions Taken
- Set the minimum window size prior to the first resize in `MainWindow.__init__` and triggered a constraints refresh immediately after rebuilding tiers.
- Extended `_update_size_constraints()` to capture the pre-adjust width, enforce the minimum width via `resize`, and reapply the global minimum size guard.
- Toggled the tier scroll area's horizontal policy based on the pre-adjust width so users can pan to hidden columns if the window shrinks below the minimum.

## Helpful Hints
- Call `_update_size_constraints()` whenever tier counts or window metrics change to keep scroll behavior and minimums aligned.
- Adjust `WINDOW_MIN_WIDTH` alongside `TIER_COLUMN_MIN_WIDTH` if future designs introduce more or narrower columns.
- The scroll area uses `Qt.ScrollBarAsNeeded` only when the width dips below the minimum, preserving the clean appearance under normal sizing.
---
---

# Session 6 — 2025-10-02 09:23

## Topic
Buffer the launch width so tier columns remain visible by default.

## User Desires
Keep all three tier columns visible when the window opens while preserving existing minimum-size and scrolling safeguards.

## Specifics of User Desires
- Increase the default window width beyond `WINDOW_MIN_WIDTH` to provide a small buffer for the tier builder.
- After applying size constraints during initialization, ensure the window width is still at least the requested minimum.
- Maintain the horizontal scroll fallback inside `_update_size_constraints()` without altering other behaviors.

## Actions Taken
- Updated `DEFAULT_WINDOW_SIZE` to add a 40px buffer above `WINDOW_MIN_WIDTH` so the default resize fits all columns comfortably.
- Added a startup check after `_update_size_constraints()` to expand the window to `WINDOW_MIN_WIDTH + 40` if initialization left it narrower.
- Left `_update_size_constraints()` logic intact so the horizontal scroll fallback remains available when users shrink the window.

## Helpful Hints
- Adjust the buffer in `DEFAULT_WINDOW_SIZE` if tier column minimum widths or panel minimums change in the future.
- Call `_update_size_constraints()` whenever column counts change so the guard check can reapply the buffered width.
---

---
---
---

# Session 7 — 2025-10-02 09:51

## Topic
Recalculate tier panel minimum width using explicit layout margins.

## User Desires
Ensure the tier builder columns are fully visible at launch by correcting the width calculation to include the tiers layout margin.

## Specifics of User Desires
- Define a shared constant for the tier grid layout margin instead of relying on hardcoded literals.
- Incorporate the margin into the tier panel minimum width computation so the third column is never clipped.
- Update the layout configuration to reference the new constant for consistency.

## Actions Taken
- Added `TIER_GRID_LAYOUT_MARGIN` and reused it when configuring the tier grid layout margins.
- Expanded `TIERS_PANEL_MIN_WIDTH` to include both sides of the tier grid margin in its formula.
- Retained existing safeguards and tests to confirm the GUI module still compiles.

## Helpful Hints
- Any future change to the tier grid spacing should update `TIER_GRID_LAYOUT_MARGIN` to keep derived widths in sync.
- Verify `_update_size_constraints()` if additional padding constants are introduced so the enforced widths remain accurate.
---

---
---
---

# Session 8 — 2025-10-02 09:55

## Topic
Recalculate minimum widths so the tier builder's third column is visible on launch.

## User Desires
Guarantee all three tier columns render without truncation at startup while preserving the dark themed layout and existing safeguards.

## Specifics of User Desires
- Increase the effective minimum width by accounting for card padding so the tier card cannot collapse and hide a column.
- Keep prior minimum-size enforcement and horizontal scrolling logic intact as a fallback when users shrink the window.
- Maintain the buffered default window size introduced earlier while ensuring derived constants reflect actual layout needs.

## Actions Taken
- Introduced shared card padding constants and updated the window minimum width calculation to include library and tier card margins.
- Applied the padding constants to card layout margins, persisted references to the library and tier panels, and enforced their minimum widths.
- Reused the derived panel widths inside `_update_size_constraints()` so the tier scroll area and card maintain the space required for all columns.

## Helpful Hints
- Adjust `CARD_CONTENT_MARGIN` if card padding changes to keep window and panel width calculations aligned.
- When modifying tier layout margins or column counts, update `TIERS_PANEL_MIN_WIDTH` so `_update_size_constraints()` stays accurate.
---

---
---
---

# Session 9 — 2025-10-02 10:20

## Topic
Ensure tier builder columns remain fully visible via layout constraints.

## User Desires
Keep all three tier columns visible at startup by fixing the Tier Builder layout in gui.py.

## Specifics of User Desires
- Investigate the tier grid configuration to identify why the third column is clipped on launch.
- Adjust layout sizing so each column receives equal space and respects the intended minimum width.
- Preserve existing functionality while ensuring the Tier Builder stays readable even when the window resizes.

## Actions Taken
- Applied column stretch and minimum width constraints to the tier grid during initialization and rebuilds.
- Set each tier card wrapper to enforce the shared minimum width so layout math matches the panel constants.
- Re-ran the GUI size constraint routine to confirm the new limits coexist with the existing fallback safeguards.

## Helpful Hints
- If tier counts or minimum widths change, update the shared constants so the grid and window constraints stay aligned.
- When introducing new tier layouts, reuse the column minimum width call to avoid regressions in the initial viewport.
---

---
---
---

# Session 10 — 2025-10-02 10:25

## Topic
Account for window decorations when sizing the main window.

## User Desires
Ensure the tier builder's third column is always visible at startup by padding the window width for OS chrome while keeping the existing safeguards.

## Specifics of User Desires
- Replace the fixed default resize with logic that measures window decorations and adds an appropriate safety buffer.
- Apply the same padded width inside `_update_size_constraints()` whenever the window is forced back to its minimum size.
- Retain the horizontal scroll fallback so users can still reach hidden columns after manually shrinking the window.

## Actions Taken
- Added a `_decoration_padding()` helper and used it during initialization to expand the window width by the larger of the measured chrome or a 40px buffer.
- Updated `_update_size_constraints()` to reuse the padded width whenever it corrects a too-small window.
- Kept the existing horizontal scroll toggle so users who resize below the minimum can still access all tier columns.

## Helpful Hints
- The `_decoration_padding()` helper should be reused if future features need to guarantee full column visibility after dynamic layout changes.
- If tier column counts change, update the underlying constants before relying on the padding helper to avoid stale minimums.
---

---
---
---

# Session 11 — 2025-10-02 10:50

## Topic
Align tier builder scrollbar behaviour with layout padding.

## User Desires
Stop the Tier Builder panel from showing a vertical scrollbar by default and style it to match the Fluent theme.

## Specifics of User Desires
- Default the Tier Builder scroll area's vertical scrollbar to hidden and only reveal it when the content exceeds the viewport height.
- Apply a slim, translucent Fluent-inspired look when the scrollbar is displayed.
- Preserve all existing safeguards that keep the three tier columns visible at launch.

## Actions Taken
- Set the tier scroll area's vertical scrollbar policy to `ScrollBarAlwaysOff` by default and toggle it inside `_sync_all_tier_heights()` based on the current viewport and content heights.
- Assigned an object name to the tier scroll area and added stylesheet rules that render the vertical scrollbar as a narrow, semi-transparent thumb.
- Kept the horizontal scrolling fallback and size constraint routines unchanged while extending the tier height synchronisation to manage the scrollbar visibility.

## Helpful Hints
- If tier card padding or row heights change, revisit `_sync_all_tier_heights()` so the viewport comparison remains accurate.
- The Fluent scrollbar styling is scoped to `tiersScroll`; reuse this object name for future tier scroll replacements to inherit the same aesthetic.
---

---
---
---

# Session 12 — 2025-10-02 11:15

## Topic
Reposition tier builder scrollbar gutter spacing.

## User Desires
Make the tier builder scrollbar feel external to the third column and keep it slim and modern.

## Specifics of User Desires
- Wrap the tier builder scroll area in a horizontal layout with a fixed-width spacer so the vertical scrollbar sits in the gutter between Tier Builder and Workflow panels.
- Ensure the scrollbar continues using the modern styling and `ScrollBarAsNeeded` policy, preserving functionality and appearance.
- Account for the new gutter width in the tier panel minimum size calculation so columns remain fully visible.

## Actions Taken
- Added a gutter width constant, integrated it into the tier panel minimum width math, and reused it when configuring the tier grid layout margins.
- Wrapped the tier scroll area in a zero-spacing horizontal layout with a fixed-width spacer to shift the scrollbar outside the third column.
- Simplified the scrollbar policy handling to rely on `ScrollBarAsNeeded` while retaining the existing height synchronisation reset.

## Helpful Hints
- Update `TIER_SCROLL_GUTTER_WIDTH` if future visual tweaks require a wider or narrower gutter between the tier builder and workflow panels.
- The spacer widget keeps the gutter padding consistent; replace it with a styled frame if a visible divider is desired later.
---

---
---
---

# Session 13 — 2025-10-02 12:45

## Topic
External tier scrollbar gutter integration.

## User Desires
Ensure the tier builder's third column stays visible while relocating the vertical scrollbar into an external gutter that mirrors the scroll area's movement.

## Specifics of User Desires
- Reserve dedicated gutter and scrollbar widths in the tier panel sizing math so all three tier columns fit at launch.
- Replace the scroll area's built-in vertical bar with an external one that stays hidden until scrolling is necessary and adopts the Fluent styling.
- Keep the external bar synchronised with the internal scroll area after tier rebuilds, height changes, and window resizing.

## Actions Taken
- Added gutter and external scrollbar width constants, updated minimum width calculations, and wrapped the tier scroll area with a spacer plus a dedicated `QScrollBar` widget.
- Hid the internal vertical scrollbar, styled the external bar, and bridged their signals with helper methods that mirror range, value, and visibility.
- Hooked the new synchronisation routine into size constraint updates and tier height refreshes to keep the gutter bar accurate as content changes.

## Helpful Hints
- `_sync_external_tier_scrollbar()` centralises all mirroring logic; call it after any manual scrollbar adjustments to keep the gutter bar consistent.
- Adjust `EXTERNAL_VBAR_WIDTH` and `TIER_SCROLL_GUTTER_WIDTH` together if the gutter's visual weight changes in future design tweaks.
---

---
---
---

# Session 14 — 2025-10-02 13:30

## Topic
Stabilise initial tier list sizing to prevent oversized first paint.

## User Desires
Ensure the tier builder respects the configured row count at startup and that wrappers do not stretch lists beyond their synced heights.

## Specifics of User Desires
- Remove the `TierList.sizeHint()` default height so the main window controls overall sizing.
- Lock in each tier list height before the widgets are inserted into the layout, then keep wrapper bodies fixed to the calculated dimensions.
- Reapply calculated heights after the window shows and guard against empty tiers ballooning due to fallback metrics.

## Actions Taken
- Added an early `_sync_tier_height` call during tier construction, updated the synchronisation routine to cap empty tiers, and propagate heights to the enclosing body widgets.
- Switched the tier body containers to a fixed vertical size policy, collapsed them when toggled shut, and scheduled a zero-delay timer to resync heights once the UI is polished.
- Removed the `TierList` size hint override and introduced margin-aware body height updates so the grid layout never stretches lists unexpectedly.

## Helpful Hints
- `_sync_tier_height` now sets both the list and body heights; call it whenever the row count should refresh, even before a tier is added to a layout.
- The post-initialisation `QTimer.singleShot` ensures Qt font metrics are ready—keep it if additional startup adjustments rely on polished geometry.
- If tier body padding changes, update `_sync_tier_height` to include the new margins so wrappers remain aligned with the list height.
---
---
---
---

# Session 15 — 2025-10-02 14:05

## Topic
Persist the tier builder count preference with a new nine-tier default.

## User Desires
Ensure the application opens with nine tiers visible and remembers the player-selected tier count across launches.

## Specifics of User Desires
Load the tier count from settings in `MainWindow.__init__`, defaulting to nine tiers, clamp it within the spin box limits, and save the normalized value back to the settings store.

## Actions Taken
- Read the stored tier count via `QSettings` in `gui.py — MainWindow.__init__`, clamped it between one and twenty, and seeded the tier spinner plus settings with the sanitized value.
- Updated `gui.py — MainWindow._on_tier_count_changed` to persist user changes to the tier count before rebuilding tier widgets.

## Helpful Hints
If the allowed tier range changes, update the clamp in both the constructor and settings handler so persisted values stay valid.
---
---
---

# Session 16 — 2025-10-03 10:08

## Topic
Ensure the Workflow action buttons retain readable labels regardless of the initial window size.

## User Desires
The user wanted the Workflow buttons to match their stretched appearance on launch and to stop collapsing when the window is narrow.

## Specifics of User Desires
They requested enforcing minimum widths based on the buttons’ size hints, making the action row communicate its minimum size, and adjusting the window constraints so the Workflow panel cannot shrink enough to clip the text.

## Actions Taken
- Updated `gui.py — MainWindow.__init__` to pin the Workflow buttons to their size-hint widths, remove stretch factors, and store layout references for later measurement.
- Added `gui.py — MainWindow._workflow_actions_minimum_width` to calculate the minimum width required for the Workflow row including spacing and card margins.
- Reworked `gui.py — MainWindow._update_size_constraints` to apply the dynamic Workflow width when setting the settings panel and overall window minimums.

## Helpful Hints
If additional controls are added to the Workflow row, update `_workflow_actions_minimum_width` so the spacing and margin calculation still reflects the full set of buttons.
---
---
---

# Session 17 — 2025-10-03 12:30

## Topic
Follow-up layout adjustments to ensure Workflow buttons drive the initial window sizing.

## User Desires
The user wanted the main window to calculate its minimum width only after the Workflow buttons are realized so their labels never start truncated.

## Specifics of User Desires
They asked to delay the initial resizing until after the full layout is assembled, have the main layout respect child minimums, include Workflow layout margins in the measurement helper, and trigger one more constraint update once Qt finalizes style metrics.

## Actions Taken
- Updated `gui.py — MainWindow.__init__` to defer initial sizing, add a size constraint on the main layout, and schedule another `_update_size_constraints` invocation via `QTimer.singleShot`.
- Expanded `gui.py — MainWindow._workflow_actions_minimum_width` to add the Workflow row’s own margins into the total width calculation used by `_update_size_constraints`.

## Helpful Hints
Whenever new controls are added beside the Workflow buttons, recheck `_workflow_actions_minimum_width` so the margin and spacing math still yields the correct minimum width for the settings column.

---
---
---

# Session 18 — 2025-10-03 14:10

## Topic
Second follow-up to guarantee Workflow buttons report final size hints before the window minimum is enforced.

## User Desires
The user observed that the Workflow actions still appeared truncated on first launch and wanted the app to remeasure button widths after Qt finished applying fonts and DPI scaling.

## Specifics of User Desires
They requested a helper that refreshes the three action buttons’ minimum widths using up-to-date size hints, to call that helper after building the Workflow panel, again via a zero-delay timer, and once more on the first show before recalculating the global size constraints. They also wanted the width computation to consider live size hints and include a small safety buffer.

## Actions Taken
- Added `gui.py — MainWindow._refresh_workflow_button_minimums` and `MainWindow._refresh_workflow_buttons_and_update` to recalculate button minimums and immediately reapply size constraints when needed.
- Updated `gui.py — MainWindow.__init__` to invoke the refresh helper after assembling the Workflow layout, reuse it when enforcing constraints, and schedule another pass with `QTimer.singleShot(0, ...)`.
- Overrode `gui.py — MainWindow.showEvent` to trigger one final refresh/update pair on the first paint, and expanded `_workflow_actions_minimum_width` to use live size hints with an extra padding buffer.

## Helpful Hints
If future DPI or theme toggles happen dynamically, call `_refresh_workflow_buttons_and_update` so the Workflow panel can expand before Qt tries to compress the button labels.

---
---
---

# Session 19 — 2025-10-03 15:45

## Topic
Replace unsupported stylesheet shadows with QGraphics effects on key panels.

## User Desires
The user wanted the console spam about unknown `box-shadow` properties eliminated while keeping subtle elevation cues on the primary cards.

## Specifics of User Desires
They asked to delete every `box-shadow` declaration from the stylesheet, introduce a helper that applies `QGraphicsDropShadowEffect`, and use it only on the library card, workflow card, and each tier panel with tuned blur, offset, and alpha values.

## Actions Taken
- Removed the `box-shadow` rule from `gui.py — APP_STYLE_TEMPLATE` so Qt stops warning about unsupported stylesheet properties.
- Added `gui.py — MainWindow._apply_shadow` to centralise drop-shadow configuration and reused it for the library and workflow panels in the constructor.
- Updated `gui.py — MainWindow._create_tier_panel` to attach the reusable shadow effect to each tier card instead of constructing ad-hoc effects.

## Helpful Hints
Adjust the `_apply_shadow` parameters per widget to fine-tune elevation; keeping the helper ensures future tweaks avoid duplicating effect setup.

---
---
---

# Session 20 — 2025-10-04 16:45

## Topic
Unify the scan workflow into a persistent Scan Card with inline messaging.

## User Desires
The user wanted to replace the dual progress bars and blocking dialog with a single workflow card that tracks both scan phases, keeps status text in place, and uses a non-blocking inline notice.

## Specifics of User Desires
They asked for scan state tracking across idle/phase1/phase2/complete/cancel/error, a rounded card with phase/detail labels, a shared progress bar, cancel and hide actions, persistence of the collapsed state, keyboard-friendly focus handling, and an inline InfoBar moment instead of the phase-1 QMessageBox.

## Actions Taken
- Added `gui.py — InfoBar` and `ScanCard` to style the unified scan widget with notice support, progress bar, and inline actions.
- Introduced scan state constants plus `MainWindow._set_scan_state`, `_set_scan_card_collapsed`, and `_on_scan_card_hidden` to manage visibility, persistence, and button availability across workflow phases.
- Reworked `MainWindow.scan_now`, `_update_scan_progress_value`, `_on_nps_progress`, `_on_nps_done`, and `_scan_finished` to drive the Scan Card, reuse one progress bar for both phases, emit inline notices, and drop the blocking completion message box.
- Hooked keyboard shortcuts by overriding `MainWindow.keyPressEvent` and `ScanCard.keyPressEvent` so Escape focuses Cancel during scans and Enter/Space toggles Hide when finished.

## Helpful Hints
- Call `_set_scan_state` when introducing new scan transitions so the card updates button visibility and collapse persistence automatically.
- Use `scan_card.show_notice()` for short-lived inline status moments—`clear_notice()` resets it when switching phases.
- The scan card collapse preference is stored under `scan_card_collapsed`; hide actions persist the flag until the next explicit scan.

---
---
---

# Session 21 — 2025-10-05 14:20

## Topic
Embedded the scan status messaging directly in the workflow card progress bar while adding phase-specific color cues.

## User Desires
The user wanted the redundant detail label removed so the progress bar itself communicates scan status, with smooth color changes between the library and NPS phases.

## Specifics of User Desires
They asked for the bar text to show phase-specific messaging (percent for phase one, counts for phase two), to animate from blue to purple when NPS begins, and to keep the card visually compact without modal interruptions.

## Actions Taken
- Updated `gui.py — ScanCard` to drop the detail label, style the header, host the status text inside the progress bar, and drive a `QVariantAnimation` that blends the chunk color between the blue and purple phase tones.
- Revised `gui.py — MainWindow` scan lifecycle helpers to feed formatted status strings into the progress bar, remove detail label updates, and ensure completion and cancel flows present inline feedback.

## Helpful Hints
Whenever new scan states are introduced, wire them through `_set_scan_state` so the progress color animation and inline text formatting stay consistent.

---
---
---
# Session 22 — 2025-10-06 09:40

## Topic
Replaced the toolbox accordion with a tabbed workflow surface that aligns with the updated Scan Card layout.

## User Desires
The user wanted the Filters, Rules, and Advanced controls exposed through a horizontal tab row that matches the workflow card aesthetics while relocating the Clear Cache button into the Advanced tab.

## Specifics of User Desires
They asked for a VS Code-style tab presentation beneath the Scan Card using the accent underline, a shared card-toned content well with padding and light borders, responsive behavior when the Scan Card collapses, smooth tab transitions, keyboard navigation with Ctrl+Tab, and the Clear Cache action positioned at the bottom of Advanced.

## Actions Taken
- Added `gui.py — WorkflowTabs` to pair a custom-styled `QTabBar` and `QStackedWidget` with fade transitions, Ctrl+Tab cycling, and shared padding.
- Updated `gui.py — APP_STYLE_TEMPLATE` to skin the new workflow tab row with accent underlines, hover states, and a matching content panel.
- Rebuilt `gui.py — MainWindow.__init__` settings construction to load Filters, Rules, and Advanced pages into the new tab container and moved the Clear Cache button inside the Advanced panel spacing.

## Helpful Hints
Use `WorkflowTabs.addTab` when introducing new workflow panes so they inherit the shared animation and styling, and keep inner page layouts margin-free because the tab panel already applies the 16px padding for consistent spacing.
---
# Session 23 — 2025-10-06 12:30

## Topic
Stabilized the workflow tab fade animation lifecycle introduced in Session 22.

## User Desires
The user wanted the new tab transitions to avoid crashes by ensuring opacity effects are cleaned up safely between animations.

## Specifics of User Desires
They requested guard rails around `_animate_to` so that graphics effects are detached before deletion, previously destroyed effects are not referenced, and cleanup handlers survive rapid tab switching.

## Actions Taken
- Hardened `gui.py — WorkflowTabs._animate_to` to verify animations and graphics effects remain valid with `shiboken6.isValid`, detaching any existing effect from the widget before scheduling deletion.
- Wrapped the fade animation stop and cleanup routines in `try/except` blocks so repeated transitions cannot raise `RuntimeError` when Qt has already disposed of an object.
- Ensured the finished callback only clears internal references when they still point at the running animation/effect, preventing double deletions.

## Helpful Hints
When expanding the tab system with new transitions, reuse the validity checks and widget detachment pattern so that Qt manages the effect lifecycle without unexpected crashes during rapid tab changes.
# Session 24 — 2025-10-06 15:10

## Topic
Reordered the workflow settings tabs so the new grouping places tier rules first and moves advanced maintenance into its own pane.

## User Desires
The user wanted the workflow controls reshuffled into Rules, Filters, and Advanced tabs with updated option groupings that relocate Clear Cache beneath the theme selector.

## Specifics of User Desires
They specified the Rules tab should lead with tier counts and song allocation, followed by the long-song, difficulty, genre, artist, and NPS weighting toggles; Filters should only expose the meme exclusion toggle and minimum difficulty spinner; Advanced should retain theme selection alongside the Clear Cache action.

## Actions Taken
- Rebuilt `gui.py — MainWindow.__init__` tab construction so the Rules page now owns the tier counts, grouping checkboxes, and NPS weighting while Filters and Advanced contain only their requested controls.
- Converted each workflow page to a dedicated `QFormLayout` with uniform 12px margins and 10px spacing to match the refreshed grouping requirements.
- Verified the Clear Cache button now lives inside the Advanced tab form instead of the outer settings layout while keeping all signal connections intact.

## Helpful Hints
When adjusting future workflow options, add them through the corresponding `QFormLayout` so padding stays consistent and remember the Rules tab now initializes `self.lbl_artist_limit` for artist limit enable/disable toggling.

---
# Session 25 — 2025-10-06 17:45

## Topic
Rebalanced the workflow tab layouts to honor the revised ordering and grouping for Rules and Filters specified after Session 24.

## User Desires
The user wanted the Rules tab to lead with tier counts, minimum difficulty, and rule toggles while the Filters tab should present the artist cap and meme exclusion options in that order.

## Specifics of User Desires
They requested Rules contain the tier spin boxes followed by the minimum difficulty control and each checkbox in a precise sequence, and Filters should only include the artist track limit spinner paired with its label before the meme exclusion checkbox.

## Actions Taken
- Updated `gui.py — MainWindow.__init__` to rebuild the Rules form rows so tiers, songs per tier, minimum difficulty, and the rule toggles appear exactly in the requested order.
- Moved `self.lbl_artist_limit` and the artist limit spin box into the Filters form ahead of the meme exclusion checkbox while keeping consistent 12px margins and 10px spacing.
- Verified that existing signal connections for minimum difficulty, artist limit, and meme exclusion remained intact after the layout adjustments.

## Helpful Hints
When adjusting these forms in the future, remember that the Rules page now owns the minimum difficulty spinner while the Filters page retains the artist limit label for enable-state toggling in `_apply_artist_mode_state`.

---
# Session 26 — 2025-10-06 19:05

## Topic
Adjusted the workflow filters tab to house the long-song toggle per the latest review feedback.

## User Desires
The user wanted the "Keep > 7:00 out of first two tiers" checkbox relocated from the Rules tab into the Filters tab so related filtering options stay grouped together.

## Specifics of User Desires
They specified that the long-song checkbox should appear above the existing meme exclusion toggle within the Filters form while leaving all other tab contents unchanged.

## Actions Taken
- Updated `gui.py — MainWindow.__init__` so the Rules form stops adding `self.chk_longrule` and the Filters form inserts it ahead of the meme exclusion checkbox.
- Verified that the new ordering maintains the shared 12px margins and 10px spacing so layout rhythm remains consistent.
- Confirmed that the checkbox retains its original signal connection since only its form container changed.

## Helpful Hints
Future adjustments to filter options should continue to leverage the Filters tab `QFormLayout` so spacing stays uniform, and note that the artist limit label still precedes the long-song rule for clarity.

---
# Session 27 — 2025-10-06 21:15

## Topic
Implemented a configurable long-chart exclusion filter inside the Filters workflow tab to satisfy the newest user review request.

## User Desires
The user wanted an additional spin box in the Filters tab that caps eligible charts by length so extremely long tracks are hidden by default.

## Specifics of User Desires
They specified adding a minutes-based threshold control after the artist limit spinner, persisting its value with QSettings, and ensuring it immediately affects the eligible library list without hiding songs that lack length metadata.

## Actions Taken
- Updated `gui.py — MainWindow.__init__` to create `self.spin_exclude_long_charts`, add the supporting label and helper text to the Filters form, and wire its `valueChanged` signal to a new persistence slot.
- Implemented `gui.py — MainWindow._on_exclude_long_songs_changed` to save the minutes threshold and trigger `_refresh_library_view`.
- Expanded `gui.py — MainWindow._eligible_library_songs` to skip songs exceeding the configured duration while leaving metadata-free charts untouched.

## Helpful Hints
When adjusting filter ordering later, remember the hint label is inserted via an empty-form label row so maintainers should preserve that blank label parameter to keep the helper copy aligned beneath the spin box.

---
# Session 28 — 2025-10-06 22:10

## Topic
Addressed review notes for the long-chart filter presentation within the Filters workflow tab.

## User Desires
The user asked to streamline the UI by removing the inline helper copy under the duration spinner and shortening the accompanying label text while retaining the tooltip guidance.

## Specifics of User Desires
They wanted only the tooltip to communicate the helper message, the label to read "Exclude charts longer than:", and no other behavioral adjustments to the persistence or filtering logic that was delivered in Session 27.

## Actions Taken
- Updated `gui.py — MainWindow.__init__` to delete the helper QLabel row, rely on the spinner tooltip for guidance, and rename the label to the requested wording without altering any value ranges or signal wiring.
- Verified that the spinner still initializes with the stored QSettings value, retains the tooltip string, and continues to trigger `_on_exclude_long_songs_changed` so filtering remains intact.

## Helpful Hints
Future design tweaks should continue to surface supplemental guidance through tooltips to avoid upsetting the tight vertical rhythm established in the Filters `QFormLayout`.

---
# Session 29 — 2025-10-06 23:05

## Topic
Adjusted the Filters tab long-chart control to include a suffix that clarifies the minutes unit per reviewer feedback on the latest pull request.

## User Desires
The reviewer requested that the duration spin box clearly display the units directly in the control without changing any of the existing filtering behavior or persistence.

## Specifics of User Desires
They specifically wanted the spin box to append the word "minutes" with proper spacing, inherit the standard styling, and keep the tooltip-driven guidance and current value ranges untouched.

## Actions Taken
- Updated `gui.py — MainWindow.__init__` so `self.spin_exclude_long_charts` calls `setSuffix(" minutes")`, ensuring the numeric value is visually paired with the expected units while retaining the tooltip and signal wiring.
- Re-ran `python -m compileall ch_career_mode` to confirm the module continues to compile after the suffix adjustment.

## Helpful Hints
Qt automatically applies the control palette colors to suffix text, so future visual tweaks can rely on stylesheet updates rather than additional code when modifying spin box suffix presentation.

---
# Session 30 — 2025-10-07 00:45

## Topic
Implemented the short-song filter control within the Filters workflow tab alongside dynamic unit messaging updates.

## User Desires
The user wanted a new filter to skip abnormally short charts while keeping the existing long-chart filter and meme toggle consistent with the refreshed layout.

## Specifics of User Desires
They requested a seconds-based spin box that automatically switches its suffix to minutes past the one-minute mark, persists through QSettings, and applies immediately during library scans without altering previously delivered behaviors.

## Actions Taken
- Updated `gui.py — MainWindow.__init__` to instantiate `self.spin_exclude_short_songs`, wire tooltip-rich persistence, and insert the control above the long-chart option in the Filters `QFormLayout`.
- Connected the new spin box to `_on_short_song_threshold_changed` for suffix swapping and `_on_exclude_short_songs_changed` for QSettings storage plus live library refreshes.
- Extended `gui.py — MainWindow._eligible_library_songs` to reject songs shorter than the configured threshold prior to the long-chart check, ensuring the new setting affects tiering and previews immediately.

## Helpful Hints
The short-song suffix toggling relies on `QSpinBox.setSuffix`, so future localization work should update both the seconds and minutes strings together to keep the UI consistent.

---
# Session 31 — 2025-10-07 01:30

## Topic
Reworked the short-song filter spin box to convert between seconds and minutes while keeping persistence in raw seconds.

## User Desires
The reviewer wanted the UI to translate the threshold value when crossing the one-minute boundary so the display shows minutes instead of an inflated seconds count, all without breaking saved preferences or filtering behavior.

## Specifics of User Desires
They requested that increments past sixty seconds rewrite the displayed number as whole minutes, decrements below one minute revert to seconds, signals avoid double-firing during conversions, and internal logic always reason about the cutoff in total seconds.

## Actions Taken
- Added `gui.py — MainWindow._set_short_song_spinbox_display_from_seconds` to centralize range, suffix, and value adjustments while updating a `_short_song_seconds` cache used by other handlers.
- Updated `gui.py — MainWindow._on_short_song_threshold_changed` to trigger conversions in both directions with signal blocking and to normalize keyboard edits onto supported increments.
- Adjusted `gui.py — MainWindow._on_exclude_short_songs_changed` and `_eligible_library_songs` so persistence and filtering consistently consume the cached seconds value rather than the visual unit.
- Ran `python -m compileall ch_career_mode` to verify the GUI module still compiles after the refactor.

## Helpful Hints
When extending these filters, prefer reading `_short_song_seconds` for the authoritative threshold since the spin box may be presenting either minutes or seconds depending on the current value.

---
# Session 32 — 2025-10-06 09:28

## Topic
Reaffirmed the short-song filter default so the spinner initializes at thirty seconds before applying saved preferences.

## User Desires
The reviewer noted the new conversion logic made the filter start at one minute and asked for the control to open on the expected 30-second default.

## Specifics of User Desires
They wanted the Filters tab spin box to display "30 seconds" on launch unless a prior session stored an alternate threshold, ensuring newcomers see the intended baseline.

## Actions Taken
- Updated `gui.py — MainWindow.__init__` to seed `_short_song_seconds` with the 30-second default, render that state immediately, and then layer any stored preference on top.
- Persisted the default threshold to QSettings when no prior value exists so future runs stay aligned with the intended baseline without overriding existing choices.
- Recompiled the GUI module via `python -m compileall ch_career_mode` to confirm the refactor introduces no syntax regressions.

## Helpful Hints
When adding more unit-aware filters, initialize widgets with their canonical defaults before reading settings so the UI renders a predictable baseline even if persistence data is missing or malformed.

---
# Session 33 — 2025-10-06 11:10

## Topic
Enabled context menus on song lists to open items in the native file browser.

## User Desires
The user requested a right-click option across the library and tier lists to reveal the underlying song files directly inside their operating system's file explorer.

## Specifics of User Desires
They specified that the action should appear in a custom context menu, rely on each list item's stored Song payload, and launch the OS file browser with the target file selected when possible.

## Actions Taken
- Configured `gui.py — MainWindow.__init__` and `_rebuild_tier_widgets` to expose a shared custom context-menu handler on the library and every `TierList`.
- Added `gui.py — MainWindow._on_song_context_menu` to surface a "Show in File Explorer" action that passes the associated `Song` into a new launcher helper.
- Implemented `gui.py — MainWindow._show_in_explorer` to resolve chart or song paths, warn when assets are missing, and invoke Explorer, Finder, Nautilus, or xdg-open as appropriate.
- Verified the module still compiles by running `python -m compileall ch_career_mode`.

## Helpful Hints
The explorer helper prefers real chart files when available, falls back to the song.ini location, and gracefully informs the user when only the containing folder can be opened, so future actions should reuse it for other file-based commands.

---
# Session 34 — 2025-10-07 08:12

## Topic
Eliminated lingering song selections after adding context menus so lists behave like single-selection browsers.

## User Desires
The user wanted right-click context menus without leaving multiple songs highlighted, expecting only one selection at a time and automatic clearing when focus shifts elsewhere.

## Specifics of User Desires
They described permanent highlights after the context menu work and asked for library and tier lists to act like standard file explorers: single selection per click, clearing when other lists or empty areas are clicked, and maintaining drag-and-drop functionality.

## Actions Taken
- Updated `gui.py — MainWindow.__init__` and `_rebuild_tier_widgets` to register every song list with new shared selection-handling helpers and to install a global event filter.
- Added `gui.py — MainWindow._register_song_list`, `_iter_song_lists`, `_clear_all_song_selections`, `_clear_other_list_selections`, `_on_song_selection_changed`, `_find_song_list_for_widget`, `_ensure_song_item_selected`, and an `eventFilter` override to coordinate single-selection behavior across the library and all tiers.
- Enhanced `gui.py — MainWindow._on_song_context_menu` so right-clicking selects the target song before showing the menu, preserving the existing context menu workflow.
- Recompiled the GUI package via `python -m compileall ch_career_mode` to confirm the refactor remains syntax-safe.

## Helpful Hints
The event filter now clears selections whenever the user clicks outside the lists or on empty list space, while right-clicks explicitly select their item before opening the context menu, ensuring drag-and-drop and context actions continue to work with single-selection semantics.

---
# Session 35 — 2025-10-07 09:45

## Topic
Refined every spin box control so arrows, styling, and feedback match the modern dark theme.

## User Desires
The user wanted all QSpinBox widgets to feel intuitive and professional with consistent vertical arrows, clear affordances, and feedback aligned with the rest of the UI.

## Specifics of User Desires
They emphasized keeping the up arrow increasing and down arrow decreasing everywhere, stacking the buttons on the right, introducing clearer chevron icons with hover/press accents, preserving keyboard and scroll interactions, and fitting the controls within the sleek dark surface treatment.

## Actions Taken
- Added themed chevron SVG assets under `ch_career_mode/assets/icons` and wired their paths into `APP_STYLE_TEMPLATE` so QSpinBox arrow states load crisp vector art.
- Reworked the stylesheet’s spin box block to apply the new background, borders, padding, hover/press feedback, and stacked button layout while keeping focus rings on brand.
- Introduced `MainWindow._configure_spinboxes` to left-align values, enforce vertical arrows, and enable acceleration on every relevant spin box created in `MainWindow.__init__`.
- Ran `python -m compileall ch_career_mode` to confirm the module compiles cleanly after the styling refactor.

## Helpful Hints
Chevron icons now live beside the Python package under `assets/icons`; when adjusting colors, update both default and accent variants together. Use `_configure_spinboxes` whenever adding a new QSpinBox so alignment and button symbols stay consistent without duplicating setup code.

---
# Session 36 — 2025-10-07 10:20

## Topic
Prevented duration spin boxes from truncating suffix labels while keeping the refreshed styling intact.

## User Desires
The user asked for the duration filters to show full words like "seconds" and "minutes" without clipping while preserving the modern spin box behavior introduced earlier.

## Specifics of User Desires
They highlighted that the text field failed to resize when the suffix changed length, leading to truncated labels, and requested wider controls, padding adjustments, and dynamic recalculation whenever the suffix toggles between seconds and minutes.

## Actions Taken
- Declared `gui.py — DURATION_SPIN_MIN_WIDTH` and applied it to the short- and long-song spin boxes during construction so they always start wide enough for longer suffixes.
- Added `gui.py — MainWindow._refresh_spinbox_width` and called it from `_set_short_song_spinbox_display_from_seconds` and the long-song constructor path to remeasure width after any suffix update.
- Increased the shared QSS padding inside `APP_STYLE_TEMPLATE` to keep suffix text from colliding with the stacked arrow column on every QSpinBox.
- Recompiled the GUI package with `python -m compileall ch_career_mode` to verify the adjustments remain syntax-safe.

## Helpful Hints
`_refresh_spinbox_width` blocks shrinking below the 150 px baseline while still honoring the control's `sizeHint`, so switching the short-song filter between seconds and minutes expands the field before signals resume.

---
# Session 37 — 2025-10-07 11:05

## Topic
Aligned the Filters tab spin boxes to a uniform width while guaranteeing suffix text stays fully visible.

## User Desires
The user wanted every filter spin control to share the same footprint and keep words like "seconds" and "minutes" readable without clipping when the suffix toggles.

## Specifics of User Desires
They emphasized locking all Filters tab spin boxes to a shared constant width, refreshing the layout after suffix changes, increasing padding near the arrow column, and keeping numeric text aligned cleanly with the suffix.

## Actions Taken
- Introduced `gui.py — FILTERS_SPINBOX_STANDARD_WIDTH`, helper accessors, and `_apply_filters_spinbox_width` so the artist limit and duration spin boxes all snap to the same fixed width and react to updated size hints.
- Updated `gui.py — MainWindow._style_filters_spinboxes` and initialization flow to apply the window font, right alignment, and fixed width enforcement both before and after the widgets join the Filters form layout.
- Expanded the QSS padding-right inside `APP_STYLE_TEMPLATE` and set `QFormLayout` growth policies to maintain balanced spacing while suffix recalculations trigger `updateGeometry()` and layout activation.

## Helpful Hints
When adjusting filter spin boxes in the future, reuse `_filters_spinboxes()` to keep width enforcement and alignment changes centralized, and call `_refresh_spinbox_width()` after tweaking suffix text so the layout reactivates immediately.

---
