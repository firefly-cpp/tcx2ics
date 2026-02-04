from datetime import datetime, timedelta, timezone
from pathlib import Path
from tcxreader.tcxreader import TCXReader


class Tcx2Ics:
    def __init__(self):
        self.reader = TCXReader()

    def convert(self, tcx_file: str, ics_file: str):
        ex = self.reader.read(tcx_file)

        sport = getattr(ex, "activity_type", None) or getattr(ex, "sport", None) or "Workout"
        start = getattr(ex, "start_time", None)
        duration = float(getattr(ex, "duration", 0) or 0)   # seconds
        distance = float(getattr(ex, "distance", 0) or 0)   # meters

        if not isinstance(start, datetime):
            raise ValueError("No start_time found in TCX")

        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        else:
            start = start.astimezone(timezone.utc)

        end = start + timedelta(seconds=duration)

        dist_km = distance / 1000.0
        dur_h = int(duration) // 3600
        dur_m = (int(duration) % 3600) // 60
        dur_s = int(duration) % 60

        summary = f"{sport} - {dist_km:.2f} km"
        desc = f"Sport: {sport}\\nTotal duration: {dur_h}:{dur_m:02d}:{dur_s:02d}\\nDistance: {dist_km:.2f} km"

        uid = f"{Path(tcx_file).stem}-{start.strftime('%Y%m%dT%H%M%SZ')}@tcx2ics"
        now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        ics = (
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "PRODID:-//tcx2ics//EN\r\n"
            "BEGIN:VEVENT\r\n"
            f"UID:{uid}\r\n"
            f"DTSTAMP:{now}\r\n"
            f"DTSTART:{start.strftime('%Y%m%dT%H%M%SZ')}\r\n"
            f"DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}\r\n"
            f"SUMMARY:{summary}\r\n"
            f"DESCRIPTION:{desc}\r\n"
            "END:VEVENT\r\n"
            "END:VCALENDAR\r\n"
        )

        Path(ics_file).write_text(ics, encoding="utf-8")
