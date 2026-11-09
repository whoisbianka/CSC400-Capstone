# Pathfinder accessibility

This record describes accessibility improvements in Pathfinder. WCAG 2.2 AA was the evaluation target.

## Changes

- Shared keyboard focus indicators, underlined text links, and selected-tab cues in addition to color.
- Skip-to-content links focus the main region, including the guided questionnaire. The conversation log is keyboard focusable.
- Sticky-header offsets and focus scrolling help keep controls visible. Save feedback reserves scrolling clearance.
- Buttons, selects, summaries, navigation, favorite icons, and checkbox labels have larger targets (48 CSS pixels for the targeted controls). Inline text links retain normal text layout. WCAG AA target minimum is 24 CSS pixels with exceptions; 48 is the chosen usability target.
- Save feedback persists until dismissed or replaced. Undo has no time limit. Dismissal returns focus to its originating save control when focus was inside the notification.
- Reduced-motion and forced-colors safeguards. No automatic page navigation animations.

## Verification (2026-10-31)

- Browser: keyboard skip link moves focus to `main-content`. Search shows visible keyboard focus.
- Browser: the programs page reflows at a 320-pixel viewport without horizontal overflow.
- Browser: all Explore form controls have programmatic labels; favorite buttons measure approximately 48 × 48 CSS pixels.
- JavaScript syntax checks passed for accessibility and save-feedback scripts.
- `node tests/test_accessible_save_feedback.js`: persistent Undo and keyboard focus restoration.
- Existing favorites, comparison, and save-prompt JavaScript checks passed.
- Seven Explore Python tests passed.
- `git diff --check` passed.

## Remaining audit scope

A full conformance assessment still needs assistive-technology testing (VoiceOver/NVDA), authenticated profile and saved-library flows, all errors and dynamic chat states, text-spacing and 200% text resizing, and all browser/OS combinations. Reduced-motion and forced-colors CSS is implemented but those OS settings were not manually exercised in this session. No automated axe scan or certification was performed.

## Guidance

- [Material accessibility principles](https://m3.material.io/foundations/overview/principles)
- [Material applying typography](https://m3.material.io/styles/typography/applying-type)
- [Material color system](https://m3.material.io/styles/color/the-color-system)
- [WCAG 2.2 focus not obscured](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum)
- [WCAG 2.2 target size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum)
