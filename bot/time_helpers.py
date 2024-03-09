from datetime import datetime, timedelta, timezone


def get_time(time_offset: timedelta | None = None) -> str:
    """
    Function to get the time in the format HH:MM:SS.

    Args:
        time_offset (timedelta | None): time offset
    Returns:
        str: time in the format DD.MM.YYYY HH:MM
    """
    current_time_utc = datetime.now(timezone.utc)
    utc_offset = timedelta(hours=3)
    current_time_utc3 = current_time_utc + utc_offset
    if time_offset is not None:
        current_time_utc3 += time_offset
    formatted_time = current_time_utc3.strftime('%d.%m.%Y %H:%M')
    return formatted_time
