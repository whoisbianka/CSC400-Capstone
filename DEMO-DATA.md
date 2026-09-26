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

## Data-driven prompts and card integration

Responses now group matching programs into college cards with major tags, location, college type, tuition, study format, and expandable program details. No invented grades, reviews, or rankings are displayed.

`assets/js/program-catalog.js` owns the active records. Suggested prompts are derived from the majors and formats actually present in those records; they are not fixed in HTML. For integration, normalize API records to the fixture field names and call:

```js
window.programCatalog.setPrograms(apiRecords, { demo: false });
```

This replaces the active search records and refreshes the suggested prompts, including the empty-data state. `college` and `major` are required strings. Optional fields are `state`, `stateCode`, `type`, `format`, `tuition` (annual numeric value or null), `keywords` and `careers` (string arrays). Missing costs display “Not available,” never zero. Normalize formats to Online, Campus, or Hybrid. Historical response cards retain the data and demo label from the time the question was asked. Replace `demoSearch` with backend natural-language retrieval separately; the adapter does not itself connect a database or implement AI.
