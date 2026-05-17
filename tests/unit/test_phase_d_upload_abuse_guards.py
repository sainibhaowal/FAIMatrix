"""Phase D: upload abuse protection tests."""

from __future__ import annotations

from fastapi import HTTPException


def test_validate_upload_size_rejects_oversize():
    from api.validators import validate_upload_size
    from api.validators.input_limits import MAX_UPLOAD_SIZE

    try:
        validate_upload_size(MAX_UPLOAD_SIZE + 1)
        raise AssertionError("Expected oversize rejection")
    except HTTPException as exc:
        assert exc.status_code == 413


def test_sanitize_filename_rejects_path_traversal_variants():
    from api.validators import sanitize_filename

    invalid = [
        "../secrets.txt",
        "..\\secrets.txt",
        "/etc/passwd",
        "nested/folder/file.txt",
        "nested\\folder\\file.txt",
    ]
    for name in invalid:
        try:
            sanitize_filename(name)
            raise AssertionError(f"Expected filename rejection for {name!r}")
        except HTTPException as exc:
            assert exc.status_code == 400


def test_validate_mime_extension_match_rejects_mismatch():
    from api.validators import validate_mime_extension_match

    try:
        validate_mime_extension_match("report.pdf", "text/plain")
        raise AssertionError("Expected MIME/extension mismatch rejection")
    except HTTPException as exc:
        assert exc.status_code == 415
        assert "does not match file extension" in str(exc.detail)


def test_validate_mime_extension_match_allows_expected_pairs():
    from api.validators import validate_mime_extension_match

    validate_mime_extension_match("report.pdf", "application/pdf")
    validate_mime_extension_match("image.png", "image/png")
    validate_mime_extension_match("archive.bin", "application/octet-stream")
