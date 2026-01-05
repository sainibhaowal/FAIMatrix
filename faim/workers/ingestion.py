import time

from sqlalchemy.orm import Session

from faim.db import SessionLocal
from faim.models_sql import Document

# This would ideally be a Celery task or separate process.
# For MVP, we call it via BackgroundTasks.

def ingest_document_task(document_id: str):
    db: Session = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return

        doc.status = "processing"
        db.commit()

        # Simulate Processing (Download S3 -> Parse -> FAIM Engine)
        print(f"[FAIM INGEST] Processing doc {doc.filename} ({doc.id}) from {doc.s3_key}")
        time.sleep(2) # Mock heavy work

        # Success
        doc.status = "completed"
        # doc.graph_id = ... (if creating new graph)
        db.commit()

    except Exception as e:
        print(f"[FAIM INGEST] Failed: {e}")
        if doc:
            doc.status = "failed"
            db.commit()
    finally:
        db.close()
