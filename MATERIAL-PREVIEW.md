# Material expressive preview

This opt-in study uses the real application in `/Users/biankaedouard/CSC400-Capstone` on `merging-features-bianka`, including its live catalog and existing account, saved-item, and chat flows. It does not substitute demo data or replace the app's JavaScript.

Run the app normally and visit `http://127.0.0.1:8000/?material=on`. Preview mode follows navigation within the same browser tab using session storage. Select **Current UI** or visit `?material=off` to return to the existing design. Outside preview mode, the small color-token stylesheet is inert; the loader does not fetch preview layout styles or interaction code. No production deployment was made.

## What to try

- **Replay**: an optional manual spring-motion demonstration. Normal navigation, reloads, back/forward navigation, and scrolling do not animate page or card entrances.
- Hover over the homepage cards for lift, corner changes, moving arrows, and responsive illustrations.
- Press buttons for shape and ripple feedback. Keyboard activation also receives a centered ripple.
- Open Explore filters and major details for content entrance motion.
- Save an item through the existing app for a confirmation response; animations follow server-confirmed pressed state.
- Scroll an Explore page to see the app bar gain surface emphasis.
- Use **Motion off** to pause motion while keeping the visual study. The system's reduced-motion preference takes priority and disables Replay.
- **Colors & details** opens an accessible native dialog explaining the study.

## Design choices

The current preview restores the original green accent (#b7dba5), navy surfaces, and warm text, retaining the Material shapes and interaction motion. Uses large rounded cards, shaped illustration containers, pill-shaped filled and tonal controls, segmented navigation, an emphasized headline scale, and surface hierarchy. Controls retain their existing actions and accessible names. Native form validation, focus indicators, dialog Escape behavior, and existing selection labels remain available.

This is a web interpretation of Material Expressive, not Google's Material component library. Physics values are authored for this preview. Cross-page navigation remains the existing server-rendered navigation; no artificial loading time or navigation interception is added.

## References

- https://m3.material.io/
- https://m3.material.io/styles/motion
- https://m3.material.io/styles/typography/applying-type
- https://m3.material.io/styles/color/the-color-system
- https://m3.material.io/components/app-bars/

## Verification

JavaScript syntax checks, the existing favorites and comparison UI tests, and all seven offline Explore tests pass. Browser checks cover the opt-in homepage, live Explore search and filter expansion, Replay, motion pause, the help dialog, and mobile layout without horizontal overflow. Account-dependent save animations are implemented against existing state changes and covered by existing behavior tests; no real saved items were changed during preview QA.

## Color study update

The current preview coordinates the original green primary roles, blue-gray secondary roles, tan tertiary roles, and navy surfaces. The optional light mode uses matching green roles on pale neutral surfaces. It provides complete light/dark role mappings plus standard, medium, and high contrast under **Colors & details**. **Use device setting** follows the system theme. The system's higher-contrast preference takes priority over a lower preview contrast choice. Settings persist only for the current browser session, and the ordinary UI remains unchanged outside preview mode.

Card footers now use a neutral surface with primary-colored actions, reserving strong fills for major actions. Filter chips and selected navigation share secondary containers. Illustration strokes use the foreground paired with their fill. Control outlines and decorative dividers use different roles. Save notifications use inverse surface/on-surface/primary roles. These are hand-authored accessible schemes; no dynamic wallpaper color extraction or Material Theme Builder generation is claimed.

## Navigation motion

Automatic page/card entrance animations and back/forward replay were removed at the user’s request. Hover, press, ripple, filter expansion, dialog, chat response, and confirmed save feedback remain. Replay is manual only.

## Theme loading

The selected preview theme is initialized synchronously at the start of the document head, with a matching canvas color. A parser-loaded color-token stylesheet supplies the full palette before body content renders. The layout and motion assets remain opt-in. This removes the dark-background flash caused by the earlier deferred preview loader during light-mode navigation.

## Jade green variant

The opt-in preview now tries a cooler jade primary (#8ed8bb in dark mode, #246b52 in light mode) with paired green containers and foregrounds. Navy surfaces, blue-gray secondary roles, tan accents, and on-page motion remain. The ordinary UI retains its original green.

## Periwinkle variant

The opt-in preview now uses periwinkle primary roles (#bdc2ff on navy in dark mode, #535a92 in light mode), violet containers, blue-gray secondary controls, and warm tan accents. Light surfaces use pale lavender neutrals. Existing shapes, accessibility safeguards, and interaction motion remain. The ordinary UI retains its green palette.

## Selected lavender periwinkle

Lavender periwinkle (#d1c0ff) is now the primary accent in the current preview, paired with deep violet text and containers. Light mode uses #69548e with white text. Navy surfaces, blue-gray secondary roles, warm tan accents, accessibility settings, and interaction motion are retained.

## Production rollout

Lavender periwinkle is now the default palette in theme.css, including the favicon. Shared interaction-motion assets supply hover/press, ripples, expanding content, and confirmed save/chat feedback. Production templates load _site_enhancements.html instead of preview assets, so query parameters and old session preview settings no longer activate the study toolbar or heading/tab styling. Explore headings and tabs retain their original production typography and layout. No automatic page-entry or navigation animation is installed. Reduced-motion settings disable interaction animations.
