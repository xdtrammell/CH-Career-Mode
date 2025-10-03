# Session 1 — 2025-09-25 11:10

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

# Session 3 — 2025-09-25 09:38

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

---

# Session 4 — 2025-09-25 10:15

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

# Session 5 — 2025-09-25 10:45

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

# Session 7 — 2025-10-02 09:55

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

# Session 8 — 2025-10-02 10:25

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

# Session 9 — 2025-10-02 09:51

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

# Session 10 — 2025-10-02 10:20

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
