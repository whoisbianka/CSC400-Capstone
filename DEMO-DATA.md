# Demo program search

All 15 records in `assets/data/demo-programs.js` are fictional UI test fixtures. The browser matcher in `assets/js/demo-search.js` is deterministic, not an AI or real database integration. Replace it with the team's backend query results later. No rankings, ratings, admission odds, or verified salary claims are supplied.

## Sample questions and expected results

- Which colleges offer computer science? — 3 computer science rows.
- Show nursing programs in Connecticut — 1 nursing row.
- Show online business programs under $20,000 — 1 business row.
- Compare psychology and sociology — 3 rows across both majors.
- Show public engineering programs under $20,000 — 1 mechanical engineering row.
- I enjoy drawing and graphic design — 1 graphic design row.
- Show computer science programs in Texas — no matches (no Texas fixtures).
- Show all programs — 15 rows.

Filters: full US state names (or CT, NY, MA, CA), Public/Private, Online/Campus/Hybrid, and tuition limits written as “under $20,000” or “up to 20k.” Multiple subjects or locations are OR matches; different filter types are AND matches. Each query is independent. Negation, ambiguous place names, conversational follow-ups, real-time facts, and arbitrary natural-language constraints are not supported by this demo. The optional guided questionnaire remains a separate preview pending your recommendation logic.

The table reports annual tuition test values, not total cost of attendance. Results are ordered by matched topic count and then tuition, not by college quality.
