import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tcx2ics import Tcx2Ics

FIXTURES_DIR = Path(__file__).parent / "fixtures"
OUTPUT_DIR = Path(__file__).parent / "out"


class TestTcx2IcsExamples(unittest.TestCase):
    def test_convert_with_sample_tcx(self) -> None:
        tcx_path = FIXTURES_DIR / "activity_12171312300.tcx"
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ics_path = OUTPUT_DIR / f"{tcx_path.stem}.ics"
        Tcx2Ics().convert(str(tcx_path), str(ics_path))
        ics = ics_path.read_text(encoding="utf-8")

        self.assertIn("BEGIN:VCALENDAR\n", ics)
        self.assertIn("END:VCALENDAR\n", ics)
        self.assertIn("DTSTART:20231004T142725Z\n", ics)
        self.assertIn("DTEND:20231004T155135Z\n", ics)
        self.assertIn("SUMMARY:Biking - 30.35 km\n", ics)
        self.assertIn(
            "DESCRIPTION:Sport: Biking\\nTotal duration: 1:24:10\\nDistance: 30.35 km\n",
            ics,
        )
        self.assertIn("UID:activity_12171312300-20231004T142725Z@tcx2ics\n", ics)
        self.assertRegex(ics, r"DTSTAMP:\d{8}T\d{6}Z\n")

    def test_convert_with_second_sample_tcx(self) -> None:
        tcx_path = FIXTURES_DIR / "activity_12171312300.tcx"
        with tempfile.TemporaryDirectory() as tmp_dir:
            ics_path = Path(tmp_dir) / "sample_swim.ics"
            Tcx2Ics().convert(str(tcx_path), str(ics_path))
            ics = ics_path.read_text(encoding="utf-8")

        self.assertIn("DTSTART:20231004T142725Z\n", ics)
        self.assertIn("DTEND:20231004T155135Z\n", ics)
        self.assertIn("SUMMARY:Biking - 30.35 km\n", ics)
        self.assertIn(
            "DESCRIPTION:Sport: Biking\\nTotal duration: 1:24:10\\nDistance: 30.35 km\n",
            ics,
        )
        self.assertIn("UID:activity_12171312300-20231004T142725Z@tcx2ics\n", ics)

    def test_convert_raises_when_start_time_missing(self) -> None:
        converter = Tcx2Ics()
        converter.reader.read = lambda _: SimpleNamespace(
            activity_type="Biking",
            start_time=None,
            duration=0,
            distance=0,
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            ics_path = Path(tmp_dir) / "missing.ics"
            with self.assertRaises(ValueError):
                converter.convert("missing.tcx", str(ics_path))


if __name__ == "__main__":
    unittest.main()
