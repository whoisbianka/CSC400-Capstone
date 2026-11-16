
"""Helpers for database-backed college recommendations."""


def matches_school_size(enrollment, school_size):
    """Check enrollment against Pathfinder's size categories."""

    if school_size is None:
        return True

    if enrollment is None:
        return False

    if type(enrollment) is not int or enrollment < 0:
        return False

    if school_size == "small":
        return enrollment < 3000

    if school_size == "medium":
        return 3000 <= enrollment < 15000

    if school_size == "large":
        return enrollment >= 15000

    raise ValueError("Unknown school size category.")


def find_matching_colleges(major_cipcode, state=None, school_size=None):
    """Find colleges offering a major that match student preferences."""
    import db_functions

    filters = {"cipcode": major_cipcode}

    if state:
        filters["state"] = state

    colleges = []
    seen_schools = set()
    page = 1

    while True:
        result = db_functions.get_page_programs(
            page=page,
            page_count=100,
            filters=filters,
        )

        for program in result["rows"]:
            enrollment = program.get("enrollment")

            if not matches_school_size(enrollment, school_size):
                continue

            school_id = program["unitid"]

            if school_id in seen_schools:
                continue

            seen_schools.add(school_id)

            colleges.append({
                "name": program["college"],
                "city": program["city"],
                "state": program["state"],
                "major": program["major"],
                "enrollment": enrollment,
                "website": program["website"],
            })

            if len(colleges) >= 10:
                return colleges

        if not result["has_next"]:
            break

        page += 1

    return colleges


def find_major_cipcode(major_name):
    """Find the exact CIP code for a major in the database."""
    import db_functions

    if not isinstance(major_name, str) or not major_name.strip():
        return None

    requested = major_name.strip().rstrip(".").casefold()

    suggestions = db_functions.get_major_name_suggestions(
        major_name.strip()
    )

    for major in suggestions:
        database_name = major["name"].strip().rstrip(".").casefold()

        if database_name == requested:
            return int(major["cipcode"])

    return None
