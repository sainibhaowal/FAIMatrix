"""
FAIM Image Understanding - AGI Feature #5

NEW MODULE - Does not modify any existing code.
Extracts and understands images from documents.

Features:
- Image extraction from PDFs
- Vision API integration for image understanding
- Creates nodes from image descriptions
- Links images to parent documents

Usage:
    POST /api/v1/images/process  - Process images from a file
    GET /api/v1/images/{image_id}  - Get image metadata
"""

import base64
import hashlib
import logging
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/images", tags=["Image Understanding"])


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class ImageInfo:
    """Information about an extracted image."""

    image_id: str
    filename: str
    page_number: Optional[int] = None
    description: str = ""
    objects_detected: List[str] = field(default_factory=list)
    text_extracted: str = ""
    node_id: Optional[str] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class ImageProcessRequest(BaseModel):
    """Request to process images."""

    graph_id: str = "MAIN"
    create_nodes: bool = True
    use_vision_api: bool = True


# In-memory image storage
_images: Dict[str, ImageInfo] = {}


# =============================================================================
# Image Extraction
# =============================================================================


def extract_images_from_pdf(pdf_path: str) -> List[Tuple[bytes, int]]:
    """
    Extract images from a PDF file.

    Returns list of (image_bytes, page_number).
    """
    images = []

    try:
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)

        for page_num, page in enumerate(doc):
            image_list = page.get_images(full=True)

            for _img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    images.append((image_bytes, page_num + 1))
                except Exception as e:
                    logger.warning(f"Failed to extract image from page {page_num}: {e}")

        doc.close()

    except ImportError:
        logger.warning("PyMuPDF not installed, image extraction unavailable")
    except Exception as e:
        logger.error(f"PDF image extraction failed: {e}")

    return images


def extract_images_from_docx(docx_path: str) -> List[Tuple[bytes, int]]:
    """
    Extract images from a DOCX file.

    Returns list of (image_bytes, index).
    """
    images = []

    try:
        from docx import Document

        doc = Document(docx_path)

        for i, rel in enumerate(doc.part.rels.values()):
            if "image" in rel.target_ref:
                try:
                    image_bytes = rel.target_part.blob
                    images.append((image_bytes, i + 1))
                except Exception as e:
                    logger.warning(f"Failed to extract image {i}: {e}")

    except ImportError:
        logger.warning("python-docx not installed, DOCX image extraction unavailable")
    except Exception as e:
        logger.error(f"DOCX image extraction failed: {e}")

    return images


# =============================================================================
# Image Understanding
# =============================================================================


def understand_image_with_vision_api(
    image_bytes: bytes,
    api_type: str = "openai",
) -> Tuple[str, List[str]]:
    """
    Understand an image using a vision API.

    Returns (description, objects_detected).
    """
    description = ""
    objects = []

    # Encode image to base64
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    # Try OpenAI Vision API
    if api_type == "openai":
        try:
            import openai

            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                client = openai.OpenAI(api_key=api_key)

                response = client.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Describe this image in detail. List the main objects, people, text, diagrams, or concepts visible. Format: DESCRIPTION: <detailed description>\nOBJECTS: <comma-separated list>",
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                                },
                            ],
                        }
                    ],
                    max_tokens=500,
                )

                result = response.choices[0].message.content

                for line in result.split("\n"):
                    if line.startswith("DESCRIPTION:"):
                        description = line.replace("DESCRIPTION:", "").strip()
                    elif line.startswith("OBJECTS:"):
                        objects_str = line.replace("OBJECTS:", "").strip()
                        objects = [o.strip() for o in objects_str.split(",") if o.strip()]

                return description, objects

        except Exception as e:
            logger.warning(f"OpenAI Vision API failed: {e}")

    # Fallback: Use Groq (text-only, describe what we can detect)
    try:
        from groq import Groq

        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            client = Groq(api_key=api_key)

            # Note: Groq doesn't support images directly, so this is a placeholder
            # In production, you'd use a proper vision API
            description = "[Image extracted - vision API not configured]"

    except Exception as e:
        logger.warning(f"Groq fallback failed: {e}")

    if not description:
        description = "[Image extracted but not analyzed - configure OPENAI_API_KEY for vision]"

    return description, objects


def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Extract text from an image using OCR.
    """
    try:
        import io

        import pytesseract
        from PIL import Image

        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)
        return text.strip()

    except ImportError:
        logger.warning("pytesseract/PIL not installed, OCR unavailable")
    except Exception as e:
        logger.warning(f"OCR failed: {e}")

    return ""


# =============================================================================
# Processing Pipeline
# =============================================================================


async def process_document_images(
    file_path: str,
    filename: str,
    graph_id: str,
    create_nodes: bool = True,
    use_vision_api: bool = True,
) -> List[ImageInfo]:
    """
    Process all images from a document.

    Returns list of ImageInfo objects.
    """
    images_info = []

    # Determine file type and extract images
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        images = extract_images_from_pdf(file_path)
    elif ext in [".docx", ".doc"]:
        images = extract_images_from_docx(file_path)
    else:
        return []

    logger.info(f"Extracted {len(images)} images from {filename}")

    for image_bytes, page_num in images:
        # Generate image ID from content hash
        image_hash = hashlib.sha256(image_bytes).hexdigest()[:12]
        image_id = f"img_{image_hash}"

        # Skip if already processed
        if image_id in _images:
            images_info.append(_images[image_id])
            continue

        # Understand image
        description = ""
        objects = []
        text = ""

        if use_vision_api:
            description, objects = understand_image_with_vision_api(image_bytes)

        # Always try OCR for text in images
        text = extract_text_from_image(image_bytes)

        if text and not description:
            description = f"Image containing text: {text[:200]}..."

        # Create image info
        info = ImageInfo(
            image_id=image_id,
            filename=filename,
            page_number=page_num,
            description=description,
            objects_detected=objects,
            text_extracted=text,
        )

        # Create node if requested
        if create_nodes and (description or text):
            try:
                from faim.api.production_state import get_faim_context

                ctx = get_faim_context(graph_id)
                engine = ctx.get("engine")

                if engine:
                    payload = f"[Image from {filename}, page {page_num}]\n\n"
                    payload += f"Description: {description}\n\n"
                    if objects:
                        payload += f"Objects: {', '.join(objects)}\n\n"
                    if text:
                        payload += f"Text in image: {text}\n"

                    node_id = engine.add_memory(
                        graph_id=graph_id,
                        payload=payload,
                    )
                    info.node_id = str(node_id) if node_id else None

            except Exception as e:
                logger.warning(f"Failed to create node for image: {e}")

        _images[image_id] = info
        images_info.append(info)

    return images_info


# =============================================================================
# API Endpoints
# =============================================================================


@router.post("/process")
async def process_images(
    file: UploadFile = File(...),
    graph_id: str = Form(default="MAIN"),
    create_nodes: bool = Form(default=True),
    use_vision_api: bool = Form(default=True),
):
    """
    Process images from an uploaded document.
    
    Extracts images, analyzes them with vision AI, and creates memory nodes.
    
    Example:
        curl -X POST http://localhost:8000/api/v1/images/process \
            -F "file=@document.pdf" \
            -F "graph_id=MAIN" \
            -F "use_vision_api=true"
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Save to temp file
    ext = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        images_info = await process_document_images(
            file_path=tmp_path,
            filename=file.filename,
            graph_id=graph_id,
            create_nodes=create_nodes,
            use_vision_api=use_vision_api,
        )

        return {
            "filename": file.filename,
            "images_found": len(images_info),
            "images": [
                {
                    "image_id": info.image_id,
                    "page": info.page_number,
                    "description": info.description[:200] if info.description else None,
                    "objects": info.objects_detected,
                    "has_text": bool(info.text_extracted),
                    "node_id": info.node_id,
                }
                for info in images_info
            ],
        }

    finally:
        os.unlink(tmp_path)


@router.get("/{image_id}")
async def get_image_info(image_id: str):
    """
    Get information about a processed image.
    """
    info = _images.get(image_id)
    if not info:
        raise HTTPException(status_code=404, detail="Image not found")

    return {
        "image_id": info.image_id,
        "filename": info.filename,
        "page": info.page_number,
        "description": info.description,
        "objects": info.objects_detected,
        "text": info.text_extracted,
        "node_id": info.node_id,
        "created_at": info.created_at.isoformat() if info.created_at else None,
    }


@router.get("/")
async def list_images(limit: int = 50):
    """
    List all processed images.
    """
    images = list(_images.values())[:limit]

    return {
        "count": len(images),
        "images": [
            {
                "image_id": info.image_id,
                "filename": info.filename,
                "page": info.page_number,
                "has_description": bool(info.description),
                "node_id": info.node_id,
            }
            for info in images
        ],
    }
