from __future__ import annotations

import os
from datetime import date

import pytest

from app.services import HttpWeedDiagnosisClient


pytestmark = pytest.mark.skipif(
    not os.environ.get("CROPFLOW_REAL_WEED_API_BASE_URL"),
    reason="Set CROPFLOW_REAL_WEED_API_BASE_URL to run real weed API integration tests.",
)


def test_real_injury_mitigation_api_contract() -> None:
    client = HttpWeedDiagnosisClient(os.environ["CROPFLOW_REAL_WEED_API_BASE_URL"])

    result = client.diagnose_injury_mitigation(
        survey_date=date(2026, 4, 22),
        rice_injury_level="无",
    )

    assert isinstance(result.need_mitigation, bool)
    assert isinstance(result.measures, list)
    assert isinstance(result.raw_response, dict)
