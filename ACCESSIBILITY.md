# Material preview accessibility

Implemented in `/Users/biankaedouard/CSC400-Capstone`, branch `merging-features-bianka`.

This preview uses Material accessibility principles with WCAG 2.2 AA as the evaluation target. This record describes verified improvements; it is not a declaration that the entire application conforms.

## Changes

- Shared keyboard focus indicators, underlined text links, and selected-tab cues in addition to color.
- Skip-to-content links focus the main region, including the guided questionnaire. The conversation log is keyboard focusable.
- Preview toolbar is in document flow. Sticky-header offsets and focus scrolling help keep controls visible. Save feedback reserves scrolling clearance.
- Buttons, selects, summaries, navigation, favorite icons, and checkbox labels have larger targets (48 CSS pixels for the targeted controls). Inline text links retain normal text layout. WCAG AA target minimum is 24 CSS pixels with exceptions; 48 is the chosen usability target.
- Native modal settings dialog has a named close button, initial heading focus, Escape support, and focus return. Motion toggle has a stable accessible name and pressed state.
- Save feedback persists until dismissed or replaced. Undo has no time limit. Dismissal returns focus to its originating save control when focus was inside the notification.
- Reduced-motion and forced-colors safeguards. No automatic page navigation animations.
- Existing jade green palette retained, with coordinated light/dark and adjustable contrast settings.

## Verification (2026-10-31)

- Browser: keyboard skip link moves focus to `main-content`; modal initially focuses its heading; Escape returns focus to settings trigger; visible keyboard focus on search.
- Browser: programs page and settings dialog reflow at a 320-pixel viewport override without horizontal overflow. Viewport override reset afterwards.
- Browser: all Explore form controls have programmatic labels; favorite buttons measure approximately 48 × 48 CSS pixels.
- Color-role audit: seven foreground/container pairs across light/dark × standard/medium/high settings. Lowest checked pair 6.36:1 (AA normal-text requirement 4.5:1). Rendered text checks found no failures on light Explore programs and dark Explore majors, using nearest opaque backgrounds; these checks do not cover images or all interactive states.
- JavaScript syntax checks passed for accessibility, preview, and save-feedback scripts.
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
