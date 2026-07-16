from datetime import datetime, timezone


def calculate_age(dob_str: str) -> int:
    if not dob_str:
        return 0
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
        today = datetime.now(timezone.utc).date()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except (ValueError, TypeError):
        return 0
