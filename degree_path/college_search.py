
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


def find_matching_colleges(
    major_cipcode,
    state=None,
    school_size=None,
    limit=10,
):
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

            if limit is not None and len(colleges) >= limit:
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


def rank_colleges_by_enrollment(colleges, largest=False, limit=3):
    """Rank colleges using verified enrollment numbers."""

    valid_colleges = [
        college for college in colleges
        if type(college.get("enrollment")) is int
        and college["enrollment"] >= 0
    ]

    ranked_colleges = sorted(
        valid_colleges,
        key=lambda college: college["enrollment"],
        reverse=largest,
    )

    return ranked_colleges[:limit]


def get_previous_college_results(messages):
    """Retrieve the most recent saved college search results."""
    import re

    for message in reversed(messages):
        if message.get("role") != "assistant":
            continue

        content = message.get("content", "")


        metadata_marker = "Pathfinder search metadata: "

        if metadata_marker in content:
            import json

            metadata_line = content.split(
                metadata_marker, 1
            )[1].splitlines()[0]

            try:
                metadata = json.loads(metadata_line)

                if metadata is None:
                    return []

                return restore_college_search(metadata)

            except (ValueError, KeyError, TypeError, IndexError):
                return []


        if "Pathfinder database results (not ranked):" not in content:
            continue

        results = content.split(
            "Pathfinder database results (not ranked):", 1
        )[1]

        colleges = []

        for line in results.splitlines():
            match = re.fullmatch(
                r"- (.+) \((.*), (.*)\) \| Major: (.*) \| Enrollment: (.*)",
                line.strip(),
            )

            if match is None:
                continue

            name, city, state, major, enrollment = match.groups()

            colleges.append({
                "name": name,
                "city": city,
                "state": state,
                "major": major,
                "enrollment": (
                    int(enrollment) if enrollment.isdigit() else None
                ),
            })

        return colleges

    return []


def build_college_search_metadata(
    cipcode,
    state=None,
    school_size=None,
    limit=10,
):
    """Store the parameters needed to repeat a college search."""

    return {
        "cipcode": cipcode,
        "state": state,
        "school_size": school_size,
        "limit": limit,
    }


def restore_college_search(metadata):
    """Retrieve college results using saved search parameters."""

    return find_matching_colleges(
        major_cipcode=metadata["cipcode"],
        state=metadata.get("state"),
        school_size=metadata.get("school_size"),
        limit=metadata.get("limit", 10),
    )


def restore_college_chat_history(messages):
    """Restore college cards and clean saved chat messages."""
    import json

    restored_messages = []
    previous_colleges = []

    search_marker = "\n\nPathfinder search metadata: "
    ranking_marker = "\n\nPathfinder ranking metadata: "

    for message in messages:
        restored_message = dict(message)
        content = message.get("content", "")

        if message.get("role") != "assistant":
            restored_messages.append(restored_message)
            continue

        if search_marker in content:
            reply, metadata_text = content.split(search_marker, 1)
            restored_message["content"] = reply
            previous_colleges = []

            try:
                metadata = json.loads(
                    metadata_text.splitlines()[0]
                )

                if metadata is not None:
                    previous_colleges = restore_college_search(
                        metadata
                    )

                restored_message["college_recommendations"] = (
                    previous_colleges
                )

            except (ValueError, KeyError, TypeError, IndexError):
                previous_colleges = []

        elif ranking_marker in content:
            reply, metadata_text = content.split(ranking_marker, 1)
            restored_message["content"] = reply

            try:
                metadata = json.loads(
                    metadata_text.splitlines()[0]
                )

                direction = metadata["direction"]
                limit = metadata["limit"]

                if direction in ("lowest", "highest"):
                    ranked = rank_colleges_by_enrollment(
                        previous_colleges,
                        largest=direction == "highest",
                        limit=limit,
                    )

                    restored_message["college_recommendations"] = ranked
                    restored_message["college_ranking_direction"] = direction

            except (ValueError, KeyError, TypeError, IndexError):
                pass

        restored_messages.append(restored_message)

    return restored_messages
