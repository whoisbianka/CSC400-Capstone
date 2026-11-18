"""Normalize legacy guest evidence and accumulate distinct full messages."""

def evidence_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)) or any(not isinstance(item, str) for item in value):
        raise ValueError("Evidence must be a list of messages.")
    return list(dict.fromkeys(item for item in value if item.strip()))


def merge_evidence(existing, incoming):
    return list(dict.fromkeys(evidence_list(existing) + evidence_list(incoming)))
