import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET

TCX_NS = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"

@dataclass
class TcxData:
    """Structured result from parsing a TCX file."""

    start_time: datetime
    duration_seconds: float
    distance_km: float
    sport: str

    @property
    def end_time(self) -> datetime:
        return self.start_time + timedelta(seconds=self.duration_seconds)


class Tcx2Ics:
    """Convert a TCX workout file to an ICS calendar event."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert(self, tcx_path: str, ics_path: str) -> None:
        """
        Parse *tcx_path* and write a calendar event to *ics_path*.

        Raises
        ------
        FileNotFoundError
            If *tcx_path* does not exist on disk.
        ValueError
            If *tcx_path* does not have a .tcx extension.
        """
        self._validate_input(tcx_path)
        data = self._parse(tcx_path)
        self._write_ics(data, ics_path)

    def parse(self, tcx_path: str) -> TcxData:
        """
        Parse *tcx_path* and return a :class:`TcxData` instance.

        Raises
        ------
        FileNotFoundError
            If *tcx_path* does not exist on disk.
        ValueError
            If *tcx_path* does not have a .tcx extension.
        """
        self._validate_input(tcx_path)
        return self._parse(tcx_path)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_input(tcx_path: str) -> None:
        """Raise early with clear messages on bad input."""
        if not tcx_path.lower().endswith(".tcx"):
            raise ValueError(
                f"Expected a .tcx file, got: '{tcx_path}'. "
                "Please supply a Garmin TCX file."
            )
        if not os.path.isfile(tcx_path):
            raise FileNotFoundError(
                f"TCX file not found: '{tcx_path}'. "
                "Check that the path is correct."
            )

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _ns(tag: str) -> str:
        return f"{{{TCX_NS}}}{tag}"

    def _parse(self, tcx_path: str) -> TcxData:
        tree = ET.parse(tcx_path)
        root = tree.getroot()

        activity = root.find(f".//{self._ns('Activity')}")
        if activity is None:
            raise ValueError("No <Activity> element found in TCX file.")

        sport = activity.get("Sport", "Workout")

        # Start time from the first Lap's StartTime attribute
        lap = activity.find(self._ns("Lap"))
        if lap is None:
            raise ValueError("No <Lap> element found in TCX file.")

        start_time_str = lap.get("StartTime") or ""
        start_time = self._parse_datetime(start_time_str)

        total_seconds = float(
            self._find_text(lap, "TotalTimeSeconds") or "0"
        )

        distance_m = float(
            self._find_text(lap, "DistanceMeters") or "0"
        )
        distance_km = distance_m / 1000.0

        return TcxData(
            start_time=start_time,
            duration_seconds=total_seconds,
            distance_km=distance_km,
            sport=sport,
        )

    def _find_text(self, parent: ET.Element, tag: str) -> str | None:
        el = parent.find(self._ns(tag))
        return el.text if el is not None else None

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        """Parse ISO-8601 string to timezone-aware datetime."""
        value = value.rstrip("Z")
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    # ------------------------------------------------------------------
    # ICS output
    # ------------------------------------------------------------------

    @staticmethod
    def _fmt_dt(dt: datetime) -> str:
        """Format datetime as iCalendar UTC timestamp (YYYYMMDDTHHMMSSZ)."""
        utc = dt.astimezone(timezone.utc)
        return utc.strftime("%Y%m%dT%H%M%SZ")

    def _write_ics(self, data: TcxData, ics_path: str) -> None:
        summary = (
            f"{data.sport} — "
            f"{data.distance_km:.1f} km, "
            f"{int(data.duration_seconds // 60)} min"
        )
        description = (
            f"Sport: {data.sport}\\n"
            f"Distance: {data.distance_km:.2f} km\\n"
            f"Duration: {int(data.duration_seconds // 60)} min"
        )
        uid = str(uuid.uuid4())
        now = self._fmt_dt(datetime.now(tz=timezone.utc))

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//tcx2ics//tcx2ics//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now}",
            f"DTSTART:{self._fmt_dt(data.start_time)}",
            f"DTEND:{self._fmt_dt(data.end_time)}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{description}",
            "END:VEVENT",
            "END:VCALENDAR",
        ]

        with open(ics_path, "w", encoding="utf-8") as fh:
            fh.write("\r\n".join(lines) + "\r\n")
