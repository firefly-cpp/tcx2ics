import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET

from tcxreader.tcxreader import TCXReader


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

    def convert(self, tcx_path: str, ics_path: str) -> None:
        """
        Parse *tcx_path* and write a calendar event to *ics_path*.

        Raises
        ------
        FileNotFoundError
            If *tcx_path* does not exist on disk.
        ValueError
            If *tcx_path* does not have a .tcx extension, is not
            well-formed XML, or lacks the timing data needed to build
            an event.
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
            If *tcx_path* does not have a .tcx extension, is not
            well-formed XML, or lacks the timing data needed to build
            an event.
        """
        self._validate_input(tcx_path)
        return self._parse(tcx_path)

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

    def _parse(self, tcx_path: str) -> TcxData:

        try:
            exercise = TCXReader().read(tcx_path, only_gps=False)
        except ET.ParseError as exc:
            raise ValueError(f"Malformed TCX/XML file: {exc}") from exc

        if exercise.start_time is None:
            raise ValueError(
                "TCX file has no usable trackpoint timing "
                "(need at least three timed trackpoints)."
            )

        start_time = self._ensure_utc(exercise.start_time)
        duration_seconds = float(exercise.duration or 0.0)
        distance_km = float(exercise.distance or 0.0) / 1000.0
        sport = exercise.activity_type or "Workout"

        return TcxData(
            start_time=start_time,
            duration_seconds=duration_seconds,
            distance_km=distance_km,
            sport=sport,
        )

    @staticmethod
    def _ensure_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    @staticmethod
    def _fmt_dt(dt: datetime) -> str:
        """Format datetime as iCalendar UTC timestamp (YYYYMMDDTHHMMSSZ)."""
        utc = dt.astimezone(timezone.utc)
        return utc.strftime("%Y%m%dT%H%M%SZ")

    @staticmethod
    def _escape_text(value: str) -> str:
        """Escape a value for an iCalendar TEXT field (RFC 5545 §3.3.11)."""
        return (
            value.replace("\\", "\\\\")
            .replace(";", "\\;")
            .replace(",", "\\,")
            .replace("\n", "\\n")
        )

    @staticmethod
    def _fold_line(line: str) -> str:
        if len(line.encode("utf-8")) <= 75:
            return line
        chunks: list[bytes] = []
        current = b""
        for ch in line:
            ch_bytes = ch.encode("utf-8")

            limit = 75 if not chunks else 74
            if len(current) + len(ch_bytes) > limit:
                chunks.append(current)
                current = ch_bytes
            else:
                current += ch_bytes
        chunks.append(current)
        return "\r\n ".join(chunk.decode("utf-8") for chunk in chunks)

    def _write_ics(self, data: TcxData, ics_path: str) -> None:
        minutes = int(data.duration_seconds // 60)
        summary = self._escape_text(
            f"{data.sport} — {data.distance_km:.1f} km, {minutes} min"
        )
        description = self._escape_text(
            f"Sport: {data.sport}\n"
            f"Distance: {data.distance_km:.2f} km\n"
            f"Duration: {minutes} min"
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

        folded = [self._fold_line(line) for line in lines]
        with open(ics_path, "w", encoding="utf-8") as fh:
            fh.write("\r\n".join(folded) + "\r\n")
