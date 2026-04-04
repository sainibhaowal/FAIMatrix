"""Phase I unit tests: OCR extraction wiring and fallbacks."""

from __future__ import annotations


def _settings(*, enabled: bool, fail_closed: bool):
    from perception.extract.ocr_service import OCRSettings

    return OCRSettings(
        enabled=enabled,
        engine="tesseract",
        fail_closed=fail_closed,
        languages="eng",
        timeout_seconds=10,
        max_image_pixels=10_000_000,
        pdf_render_dpi=180,
        min_text_chars=2,
        tesseract_config="--oem 1 --psm 6",
    )


def test_image_extractor_returns_stub_when_ocr_disabled(monkeypatch):
    from perception.extract import ocr_service
    from perception.extract.extractors_faim import extract_image_stub

    monkeypatch.setattr(ocr_service, "get_ocr_settings", lambda: _settings(enabled=False, fail_closed=False))

    blocks = extract_image_stub(b"not-an-image", "raw-1", filename="sample.png")
    assert len(blocks) == 1
    assert blocks[0].block_type == "image_stub"
    assert blocks[0].metadata and blocks[0].metadata.get("ocr_pending") is True


def test_image_extractor_falls_back_to_stub_when_ocr_unavailable(monkeypatch):
    from perception.extract import ocr_service
    from perception.extract.extractors_faim import extract_image_stub

    monkeypatch.setattr(ocr_service, "get_ocr_settings", lambda: _settings(enabled=True, fail_closed=False))

    def _raise_unavailable(*_args, **_kwargs):
        raise ocr_service.OCRUnavailableError("missing OCR runtime")

    monkeypatch.setattr(ocr_service, "extract_text_from_image_bytes", _raise_unavailable)

    blocks = extract_image_stub(b"fake-image", "raw-2", filename="fallback.png")
    assert len(blocks) == 1
    assert blocks[0].block_type == "image_stub"
    assert "missing OCR runtime" in str(blocks[0].metadata.get("ocr_error"))


def test_image_extractor_fail_closed_raises_on_ocr_error(monkeypatch):
    from perception.extract import ocr_service
    from perception.extract.extractors_faim import extract_image_stub

    monkeypatch.setattr(ocr_service, "get_ocr_settings", lambda: _settings(enabled=True, fail_closed=True))

    def _raise_processing(*_args, **_kwargs):
        raise ocr_service.OCRProcessingError("ocr processing failed")

    monkeypatch.setattr(ocr_service, "extract_text_from_image_bytes", _raise_processing)

    try:
        extract_image_stub(b"fake-image", "raw-3", filename="fail-closed.png")
        assert False, "Expected OCR error to propagate in fail-closed mode"
    except ocr_service.OCRProcessingError:
        pass
