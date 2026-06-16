import pytest
import pathlib

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_tcx():
    """Path to a minimal but valid TCX fixture file."""
    return str(FIXTURES_DIR / "sample.tcx")


@pytest.fixture
def sample_tcx_content():
    """Raw text content of the sample TCX fixture."""
    return (FIXTURES_DIR / "sample.tcx").read_text()
