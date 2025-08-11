"""Mission constants and normalization helpers.

Preserve the external API shape: students can pass strings or ints.
Populate/adjust the mappings below to mirror your current missions.
"""

# Example mapping — replace with your real mission map
MISSION_BY_NAME = {
    # "mission_name": 1,
    # "another": 2,
}

MISSION_BY_ID = {v: k for (k, v) in MISSION_BY_NAME.items()}


def normalize_mission(m):
    """Accept int/str/enum-like, return canonical mission id or name as needed.

    Current client uses the *value* directly in hello(). If you prefer strings,
    switch accordingly.
    """
    if m is None:
        return None
    # If int-like
    try:
        mi = int(m)
        return mi
    except Exception:
        pass
    # If string-like name
    name = str(m).strip()
    return MISSION_BY_NAME.get(name, name)
