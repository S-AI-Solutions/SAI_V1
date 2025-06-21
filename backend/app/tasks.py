"""Background tasks for document processing."""

import asyncio
from typing import Optional, List, Tuple
from app.celery_app import celery_app
from app.services.document_service import DocumentProcessingService
from app.models.schemas import DocumentType
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Create service instance
document_service = DocumentProcessingService()


@celery_app.task(bind=True)
def process_document_task(self, file_data: bytes, filename: str, document_type: Optional[str] = None):
    """Process a single document in background."""
    try:
        # Convert string back to enum if provided
        doc_type = DocumentType(document_type) if document_type else None
        
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            document_service.process_document(file_data, filename, doc_type)
        )
        
        loop.close()
        
        # Return serializable result
        return {
            "document_id": result.document_id,
            "filename": result.filename,
            "status": result.status.value,
            "extracted_data": {
                name: {
                    "value": field.value,
                    "confidence": field.confidence,
                    "confidence_level": field.confidence_level.value
                }
                for name, field in result.extracted_data.items()
            },
            "overall_confidence": result.overall_confidence
        }
        
    except Exception as e:
        logger.error(f"Document processing task failed: {e}")
        self.retry(countdown=60, max_retries=3)


@celery_app.task(bind=True)
def process_batch_task(self, files_data: List[Tuple[bytes, str]], document_type: Optional[str] = None):
    """Process multiple documents in background."""
    try:
        # Convert string back to enum if provided
        doc_type = DocumentType(document_type) if document_type else None
        
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            document_service.process_batch(files_data, doc_type)
        )
        
        loop.close()
        
        # Return serializable result
        return {
            "batch_id": result.batch_id,
            "total_documents": result.total_documents,
            "processed_documents": result.processed_documents,
            "failed_documents": result.failed_documents
        }
        
    except Exception as e:
        logger.error(f"Batch processing task failed: {e}")
        self.retry(countdown=60, max_retries=3)
