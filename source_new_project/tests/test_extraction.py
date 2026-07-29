from pathlib import Path

import pytest
import requests

from pipeline.extract import ExtractionError, IstacExtractor


class Response:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def iter_lines(self, decode_unicode: bool = False):
        yield from self.text.splitlines()


class Session:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def extractor(session: Session, retries: int = 0) -> IstacExtractor:
    return IstacExtractor(
        "https://example.test/api",
        {"airport_passengers": "C00017A_000004"},
        session=session,
        retries=retries,
        backoff_factor=0,
    )


def test_success_filters_month_and_normalizes_operation_code() -> None:
    response = Response("TIME_PERIOD_CODE,AEROPUERTO_ORIGEN_DESTINO_CODE,OBS_VALUE,Extra\n2026-06,ES_GCTS,2,x\n2026-05,ES_GCTS,3,x\n")
    session = Session([response])

    rows = list(extractor(session).fetch("airport_passengers", "2026-06"))

    assert rows == [{"TIME_PERIOD_CODE": "2026-06", "AEROPUERTO_ORIGEN_DESTINO_CODE": "ES_GCTS", "AEROPUERTO_ESCALA_CODE": "ES_GCTS", "OBS_VALUE": "2", "Extra": "x"}]
    assert "2026-06" in session.calls[0][0]


def test_null_measure_is_preserved() -> None:
    response = Response("TIME_PERIOD_CODE,OBS_VALUE\n2026-06,\n")
    assert list(extractor(Session([response])).fetch("airport_passengers", "2026-06"))[0]["OBS_VALUE"] is None


def test_malformed_and_missing_columns_fail() -> None:
    with pytest.raises(ExtractionError, match="malformed"):
        list(extractor(Session([Response("TIME_PERIOD_CODE,OBS_VALUE\n\"2026-06,1\n")])).fetch("airport_passengers", "2026-06"))
    with pytest.raises(ExtractionError, match="required columns"):
        list(extractor(Session([Response("TIME_PERIOD_CODE\n2026-06\n")])).fetch("airport_passengers", "2026-06"))


def test_retries_retryable_status_and_timeout() -> None:
    session = Session([Response("", 503), Response("TIME_PERIOD_CODE,OBS_VALUE\n2026-06,1\n")])
    rows = list(extractor(session, retries=1).fetch("airport_passengers", "2026-06"))
    assert rows[0]["OBS_VALUE"] == "1"

    timeout_session = Session([requests.Timeout(), requests.Timeout()])
    with pytest.raises(ExtractionError, match="exhausted"):
        list(extractor(timeout_session, retries=1).fetch("airport_passengers", "2026-06"))


def test_non_retryable_status_fails_without_retry() -> None:
    session = Session([Response("", 404), Response("TIME_PERIOD_CODE,OBS_VALUE\n2026-06,1\n")])
    with pytest.raises(ExtractionError, match="non-retryable"):
        list(extractor(session, retries=1).fetch("airport_passengers", "2026-06"))
    assert len(session.calls) == 1
