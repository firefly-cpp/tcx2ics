import pathlib
from datetime import datetime, timedelta, timezone

import pytest

from tcx2ics import Tcx2Ics, TcxData


BASE_START = datetime(2023, 6, 1, 7, 0, 0, tzinfo=timezone.utc)

def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _lap_xml(start: datetime, seconds: int, metres: int, points: int = 3) -> str:
    rows = [
        f'      <Lap StartTime="{_iso(start)}">',
        f"        <TotalTimeSeconds>{seconds}</TotalTimeSeconds>",
        f"        <DistanceMeters>{metres}</DistanceMeters>",
        "        <Track>",
    ]
    for i in range(points):
        frac = i / (points - 1) if points > 1 else 0.0
        t = start + timedelta(seconds=seconds * frac)
        d = metres * frac
        lat = 46.500 + 0.001 * i
        lon = 15.600 + 0.001 * i
        rows.append(
            f"          <Trackpoint><Time>{_iso(t)}</Time>"
            f"<Position><LatitudeDegrees>{lat}</LatitudeDegrees>"
            f"<LongitudeDegrees>{lon}</LongitudeDegrees></Position>"
            f"<DistanceMeters>{d}</DistanceMeters></Trackpoint>"
        )
    rows.append("        </Track>")
    rows.append("      </Lap>")
    return "\n".join(rows)


def _write_tcx(tmp_path: pathlib.Path, sport: str, laps_xml: str, name="workout.tcx") -> str:
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<TrainingCenterDatabase "
        'xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">\n'
        "  <Activities>\n"
        f'    <Activity Sport="{sport}">\n'
        "      <Id>2023-06-01T07:00:00Z</Id>\n"
        f"{laps_xml}\n"
        "    </Activity>\n"
        "  </Activities>\n"
        "</TrainingCenterDatabase>\n"
    )
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return str(path)


def _make_tcx(tmp_path: pathlib.Path, sport="Biking", seconds=3600, metres=30000) -> str:
    """Write a minimal valid single-lap TCX file and return its path."""
    return _write_tcx(tmp_path, sport, _lap_xml(BASE_START, seconds, metres))


def _make_multilap_tcx(tmp_path: pathlib.Path, laps) -> str:
    """Write a multi-lap TCX file. *laps* is a list of (start, seconds, metres)."""
    laps_xml = "\n".join(_lap_xml(start, seconds, metres) for start, seconds, metres in laps)
    return _write_tcx(tmp_path, "Running", laps_xml, name="multilap.tcx")

def test_missing_file_raises_error():
    """convert() must raise FileNotFoundError when the .tcx path does not exist."""
    with pytest.raises(FileNotFoundError, match="not found"):
        Tcx2Ics().convert("does_not_exist.tcx", "out.ics")


def test_missing_file_raises_error_on_parse():
    """parse() must raise FileNotFoundError when the .tcx path does not exist."""
    with pytest.raises(FileNotFoundError):
        Tcx2Ics().parse("does_not_exist.tcx")

def test_wrong_extension_raises_error(tmp_path):
    """convert() must raise ValueError for a non-.tcx file extension."""
    bad = tmp_path / "workout.gpx"
    bad.write_text("<gpx/>", encoding="utf-8")
    with pytest.raises(ValueError, match=r"\.tcx"):
        Tcx2Ics().convert(str(bad), "out.ics")


def test_wrong_extension_on_parse(tmp_path):
    """parse() must raise ValueError for a non-.tcx file extension."""
    bad = tmp_path / "workout.xml"
    bad.write_text("<foo/>", encoding="utf-8")
    with pytest.raises(ValueError):
        Tcx2Ics().parse(str(bad))


def test_no_extension_raises_error(tmp_path):
    """Files with no extension must also be rejected."""
    bad = tmp_path / "workout"
    bad.write_text("<foo/>", encoding="utf-8")
    with pytest.raises(ValueError):
        Tcx2Ics().convert(str(bad), "out.ics")


def test_malformed_xml_raises_value_error(tmp_path):
    """Well-formed extension but broken XML must raise ValueError, not crash."""
    bad = tmp_path / "broken.tcx"
    bad.write_text("<TrainingCenterDatabase><Activities>", encoding="utf-8")
    with pytest.raises(ValueError):
        Tcx2Ics().parse(str(bad))


def test_no_timing_data_raises_value_error(tmp_path):
    """A file without usable trackpoint timing must raise a clear ValueError."""
    path = tmp_path / "empty.tcx"
    path.write_text(
        '<?xml version="1.0"?>\n'
        '<TrainingCenterDatabase '
        'xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">'
        "<Activities></Activities></TrainingCenterDatabase>",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        Tcx2Ics().parse(str(path))


def test_start_time_is_datetime(sample_tcx):
    result = Tcx2Ics().parse(sample_tcx)
    assert isinstance(result.start_time, datetime), (
        f"Expected datetime, got {type(result.start_time)}"
    )


def test_start_time_is_timezone_aware(sample_tcx):
    result = Tcx2Ics().parse(sample_tcx)
    assert result.start_time.tzinfo is not None, "start_time must be timezone-aware"


def test_start_time_value(sample_tcx):
    """The fixture activity starts at 2023-06-01T07:00:00Z."""
    result = Tcx2Ics().parse(sample_tcx)
    assert result.start_time.year == 2023
    assert result.start_time.month == 6
    assert result.start_time.day == 1
    assert result.start_time.hour == 7

def test_distance_is_positive_float(sample_tcx):
    result = Tcx2Ics().parse(sample_tcx)
    assert isinstance(result.distance_km, float), (
        f"Expected float, got {type(result.distance_km)}"
    )
    assert result.distance_km > 0, "distance_km must be positive"


def test_distance_km_value(tmp_path):
    """30 000 metres should come back as 30.0 km."""
    path = _make_tcx(tmp_path, metres=30000)
    result = Tcx2Ics().parse(path)
    assert abs(result.distance_km - 30.0) < 0.001


def test_distance_zero_metres(tmp_path):
    """Zero-metre activities should give 0.0 km, not crash."""
    path = _make_tcx(tmp_path, metres=0)
    result = Tcx2Ics().parse(path)
    assert result.distance_km == 0.0


def test_duration_value(tmp_path):
    path = _make_tcx(tmp_path, seconds=3600)
    result = Tcx2Ics().parse(path)
    assert result.duration_seconds == 3600.0


def test_multilap_sums_duration_and_distance(tmp_path):
    """Duration spans all laps; distance is summed across every lap."""
    path = _make_multilap_tcx(
        tmp_path,
        laps=[
            (BASE_START, 1800, 5000),
            (BASE_START + timedelta(minutes=30), 1800, 5000),
        ],
    )
    result = Tcx2Ics().parse(path)
    assert result.duration_seconds == 3600.0
    assert abs(result.distance_km - 10.0) < 0.001


def test_multilap_start_time_from_first_lap(tmp_path):
    """start_time must come from the first lap."""
    path = _make_multilap_tcx(
        tmp_path,
        laps=[
            (BASE_START, 1800, 5000),
            (BASE_START + timedelta(minutes=30), 1800, 5000),
        ],
    )
    result = Tcx2Ics().parse(path)
    assert result.start_time.hour == 7
    assert result.start_time.minute == 0

def test_sport_is_nonempty_string(sample_tcx):
    result = Tcx2Ics().parse(sample_tcx)
    assert isinstance(result.sport, str), f"Expected str, got {type(result.sport)}"
    assert len(result.sport) > 0, "sport must not be empty"


@pytest.mark.parametrize("sport", ["Biking", "Running", "Swimming", "Other"])
def test_sport_values(tmp_path, sport):
    path = _make_tcx(tmp_path, sport=sport)
    result = Tcx2Ics().parse(path)
    assert result.sport == sport

def test_output_ics_file_is_created(sample_tcx, tmp_path):
    out = tmp_path / "workout.ics"
    Tcx2Ics().convert(sample_tcx, str(out))
    assert out.exists(), "ICS file was not created"


def test_output_ics_is_valid_calendar(sample_tcx, tmp_path):
    out = tmp_path / "workout.ics"
    Tcx2Ics().convert(sample_tcx, str(out))
    content = out.read_text(encoding="utf-8")
    assert "BEGIN:VCALENDAR" in content, "Missing BEGIN:VCALENDAR"
    assert "END:VCALENDAR" in content, "Missing END:VCALENDAR"


def test_ics_version_field(sample_tcx, tmp_path):
    out = tmp_path / "workout.ics"
    Tcx2Ics().convert(sample_tcx, str(out))
    content = out.read_text(encoding="utf-8")
    assert "VERSION:2.0" in content, "ICS must declare VERSION:2.0"

def test_vevent_present(sample_tcx, tmp_path):
    out = tmp_path / "workout.ics"
    Tcx2Ics().convert(sample_tcx, str(out))
    content = out.read_text(encoding="utf-8")
    assert "BEGIN:VEVENT" in content, "Missing BEGIN:VEVENT"
    assert "END:VEVENT" in content, "Missing END:VEVENT"


def test_vevent_has_dtstart(sample_tcx, tmp_path):
    out = tmp_path / "workout.ics"
    Tcx2Ics().convert(sample_tcx, str(out))
    assert "DTSTART" in out.read_text(encoding="utf-8")


def test_vevent_has_dtend(sample_tcx, tmp_path):
    out = tmp_path / "workout.ics"
    Tcx2Ics().convert(sample_tcx, str(out))
    assert "DTEND" in out.read_text(encoding="utf-8")


def test_vevent_has_summary(sample_tcx, tmp_path):
    out = tmp_path / "workout.ics"
    Tcx2Ics().convert(sample_tcx, str(out))
    assert "SUMMARY" in out.read_text(encoding="utf-8")


def test_vevent_summary_contains_sport(tmp_path):
    """SUMMARY should include the sport name."""
    path = _make_tcx(tmp_path, sport="Running")
    out = tmp_path / "workout.ics"
    Tcx2Ics().convert(path, str(out))
    content = out.read_text(encoding="utf-8")
    summary_line = next(
        (l for l in content.splitlines() if l.startswith("SUMMARY:")), ""
    )
    assert "Running" in summary_line, (
        f"SUMMARY should contain sport name. Got: {summary_line!r}"
    )


def test_summary_comma_is_escaped(tmp_path):
    """RFC 5545 TEXT values must escape commas."""
    path = _make_tcx(tmp_path, sport="Running")
    out = tmp_path / "workout.ics"
    Tcx2Ics().convert(path, str(out))
    summary_line = next(
        l for l in out.read_text(encoding="utf-8").splitlines()
        if l.startswith("SUMMARY:")
    )
    assert "\\," in summary_line, "comma in SUMMARY must be escaped as \\,"


def test_dtend_is_after_dtstart(sample_tcx, tmp_path):
    """DTEND must be strictly after DTSTART."""
    out = tmp_path / "workout.ics"
    Tcx2Ics().convert(sample_tcx, str(out))
    content = out.read_text(encoding="utf-8")
    lines = {l.split(":")[0]: l.split(":", 1)[1] for l in content.splitlines() if ":" in l}
    dtstart = datetime.strptime(lines["DTSTART"], "%Y%m%dT%H%M%SZ")
    dtend = datetime.strptime(lines["DTEND"], "%Y%m%dT%H%M%SZ")
    assert dtend > dtstart, "DTEND must be after DTSTART"

def test_tcxdata_end_time_computed(sample_tcx):
    """end_time should equal start_time + duration."""
    result = Tcx2Ics().parse(sample_tcx)
    expected_end = result.start_time + timedelta(seconds=result.duration_seconds)
    assert result.end_time == expected_end
