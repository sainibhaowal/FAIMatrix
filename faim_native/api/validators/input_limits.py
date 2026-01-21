"""
FAIM-Native Input Limits (Stage-11).

Security-focused input validation:
- Upload size limits
- Content type validation
- Filename sanitization
- Request body size limits
"""

from __future__ import annotations

import re
from typing import Optional, Set

from fastapi import HTTPException, UploadFile

# =============================================================================
# Configuration
# =============================================================================

# Maximum upload file size (10 MB default)
MAX_UPLOAD_SIZE = 10 * 1024 * 1024

# Maximum request body size for JSON (1 MB)
MAX_JSON_BODY_SIZE = 1 * 1024 * 1024

# Maximum single field size (matches Stage-9 payload bounds)
MAX_FIELD_SIZE = 4096

# Allowed content types for file uploads
ALLOWED_CONTENT_TYPES: Set[str] = {
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
    "application/pdf",
    "application/octet-stream",  # Generic binary
}

# Allowed file extensions
ALLOWED_EXTENSIONS: Set[str] = {
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".pdf",
}

# Dangerous filename patterns
DANGEROUS_FILENAME_PATTERNS = [
    r"\.\.",  # Path traversal
    r"^/",  # Absolute path
    r"^~",  # Home directory
    r"[<>:\"|?*]",  # Windows reserved
    r"[\x00-\x1f]",  # Control characters
]

# Compiled dangerous patterns
_dangerous_patterns = [re.compile(p) for p in DANGEROUS_FILENAME_PATTERNS]


# =============================================================================
# Validation Functions
# =============================================================================


def validate_upload_size(size: int) -> None:
    """
    Validate upload file size.

    Args:
        size: File size in bytes.

    Raises:
        HTTPException: If file is too large.
    """
    if size > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024*1024)} MB.",
        )


def validate_content_type(content_type: Optional[str]) -> None:
    """
    Validate content type.

    Args:
        content_type: MIME type string.

    Raises:
        HTTPException: If content type is not allowed.
    """
    if not content_type:
        return  # Allow missing content type

    # Normalize (remove charset etc.)
    base_type = content_type.split(";")[0].strip().lower()

    if base_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported content type: {base_type}",
        )


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename for safe storage.

    Args:
        filename: The original filename.

    Returns:
        Sanitized filename.

    Raises:
        HTTPException: If filename is dangerous.
    """
    if not filename:
        return "unnamed"

    # Check for dangerous patterns
    for pattern in _dangerous_patterns:
        if pattern.search(filename):
            raise HTTPException(
                status_code=400,
                detail="Invalid filename",
            )

    # Keep only safe characters
    safe_name = re.sub(r"[^\w\-_\. ]", "_", filename)

    # Limit length
    if len(safe_name) > 200:
        safe_name = safe_name[:200]

    return safe_name.strip() or "unnamed"


def validate_file_extension(filename: str) -> None:
    """
    Validate file extension.

    Args:
        filename: The filename to check.

    Raises:
        HTTPException: If extension is not allowed.
    """
    # Extract extension
    parts = filename.rsplit(".", 1)
    if len(parts) < 2:
        return  # No extension, allow

    ext = "." + parts[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"File extension '{ext}' is not allowed",
        )


async def validate_upload_file(file: UploadFile) -> None:
    """
    Validate an uploaded file.

    Combines all upload validations:
    - Content type
    - Filename sanitization
    - File extension
    - Size (requires reading file)

    Args:
        file: The uploaded file.

    Raises:
        HTTPException: If validation fails.
    """
    # Validate content type
    validate_content_type(file.content_type)

    # Sanitize and validate filename
    if file.filename:
        sanitize_filename(file.filename)
        validate_file_extension(file.filename)


def validate_json_size(content_length: Optional[int]) -> None:
    """
    Validate JSON request body size.

    Args:
        content_length: Content-Length header value.

    Raises:
        HTTPException: If body is too large.
    """
    if content_length and content_length > MAX_JSON_BODY_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Request body too large. Maximum size is {MAX_JSON_BODY_SIZE // 1024} KB.",
        )


def validate_text_field(text: str, field_name: str = "text") -> str:
    """
    Validate a text field (e.g., query, node text).

    Args:
        text: The text to validate.
        field_name: Name of the field for error messages.

    Returns:
        Validated text.

    Raises:
        HTTPException: If text is too long.
    """
    if len(text) > MAX_FIELD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} exceeds maximum length of {MAX_FIELD_SIZE} characters",
        )

    return text


def validate_nested_depth(
    data: dict, max_depth: int = 10, current_depth: int = 0
) -> None:
    """
    Validate that JSON data doesn't exceed maximum nesting depth.

    Prevents stack overflow attacks from deeply nested JSON.

    Args:
        data: Dictionary to check.
        max_depth: Maximum allowed nesting depth.
        current_depth: Current depth (for recursion).

    Raises:
        HTTPException: If depth exceeds limit.
    """
    if current_depth > max_depth:
        raise HTTPException(
            status_code=400,
            detail="Request body is too deeply nested",
        )

    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, (dict, list)):
                validate_nested_depth(value, max_depth, current_depth + 1)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                validate_nested_depth(item, max_depth, current_depth + 1)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "MAX_UPLOAD_SIZE",
    "MAX_JSON_BODY_SIZE",
    "MAX_FIELD_SIZE",
    "ALLOWED_CONTENT_TYPES",
    "ALLOWED_EXTENSIONS",
    "validate_upload_size",
    "validate_content_type",
    "sanitize_filename",
    "validate_file_extension",
    "validate_upload_file",
    "validate_json_size",
    "validate_text_field",
    "validate_nested_depth",
]
