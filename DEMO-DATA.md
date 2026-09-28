# Demo program data

The 15 records in `degree_path/data/demo_programs.json` are fictional UI fixtures. They are read by `degree_path/repositories/programs.py` and matched by `degree_path/services/search.py`. No rankings, admission odds, reviews, or verified salary claims are supplied.

Supported filters: major/keywords/careers, college names, US state names (or fixture state codes such as CT), Public/Private, Online/Campus/Hybrid, and tuition limits such as “under $20,000” or “up to 20k.” Multiple subjects and locations use OR; different filter types use AND. Each search is independent. Negation, conversational follow-ups, and arbitrary natural-language constraints are unsupported.

Annual tuition values are test values, not total cost of attendance. Matching orders records by matched topic count, then tuition; results are not ranked by college quality. The questionnaire joins its five answers into a demo search.

Program details use persistent demo IDs, for example `/programs/demo-1`. Missing information is labeled unavailable. See [Python demo setup](PYTHON-DEMO.md) for sample queries and implementation details.
