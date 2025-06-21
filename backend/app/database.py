"""Database configuration and models for Document AI MVP."""

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import aiofiles
import asyncio
from app.config import settings
from app.models.schemas import ProcessingStatus, DocumentType, ExtractedField
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DocumentRecord:
    """Document record for file-based storage."""
    id: str
    filename: str
    document_type: str
    status: str
    extracted_fields: Dict[str, Any]
    confidence_score: float
    processing_time: float
    created_at: str
    updated_at: str
    file_size: int
    validation_errors: List[str]
    metadata: Dict[str, Any]


@dataclass
class BatchRecord:
    """Batch record for file-based storage."""
    id: str
    document_ids: List[str]
    status: str
    progress: int
    total_documents: int
    processed_documents: int
    failed_documents: int
    created_at: str
    updated_at: str
    results: Dict[str, Any]


class FileDatabase:
    """File-based database implementation for development/demo purposes."""
    
    def __init__(self):
        self.data_dir = Path(settings.upload_dir) / "database"
        self.documents_dir = self.data_dir / "documents"
        self.batches_dir = self.data_dir / "batches"
        self._ensure_directories()
        self._lock = asyncio.Lock()
    
    def _ensure_directories(self):
        """Create necessary directories."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.batches_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_document(self, document: DocumentRecord) -> bool:
        """Save document record to file."""
        try:
            async with self._lock:
                file_path = self.documents_dir / f"{document.id}.json"
                async with aiofiles.open(file_path, 'w') as f:
                    await f.write(json.dumps(asdict(document), indent=2, default=str))
                logger.info(f"Document {document.id} saved to database")
                return True
        except Exception as e:
            logger.error(f"Failed to save document {document.id}: {e}")
            return False
    
    async def get_document(self, document_id: str) -> Optional[DocumentRecord]:
        """Get document record by ID."""
        try:
            file_path = self.documents_dir / f"{document_id}.json"
            if not file_path.exists():
                return None
            
            async with aiofiles.open(file_path, 'r') as f:
                data = json.loads(await f.read())
                return DocumentRecord(**data)
        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {e}")
            return None
    
    async def update_document(self, document_id: str, updates: Dict[str, Any]) -> bool:
        """Update document record."""
        try:
            document = await self.get_document(document_id)
            if not document:
                return False
            
            # Update fields
            for key, value in updates.items():
                if hasattr(document, key):
                    setattr(document, key, value)
            
            document.updated_at = datetime.utcnow().isoformat()
            return await self.save_document(document)
        except Exception as e:
            logger.error(f"Failed to update document {document_id}: {e}")
            return False
    
    async def list_documents(
        self, 
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[DocumentRecord]:
        """List documents with optional filtering."""
        try:
            documents = []
            files = list(self.documents_dir.glob("*.json"))
            
            for file_path in files[offset:offset + limit]:
                async with aiofiles.open(file_path, 'r') as f:
                    data = json.loads(await f.read())
                    document = DocumentRecord(**data)
                    
                    if status is None or document.status == status:
                        documents.append(document)
            
            return documents
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return []
    
    async def save_batch(self, batch: BatchRecord) -> bool:
        """Save batch record to file."""
        try:
            async with self._lock:
                file_path = self.batches_dir / f"{batch.id}.json"
                async with aiofiles.open(file_path, 'w') as f:
                    await f.write(json.dumps(asdict(batch), indent=2, default=str))
                logger.info(f"Batch {batch.id} saved to database")
                return True
        except Exception as e:
            logger.error(f"Failed to save batch {batch.id}: {e}")
            return False
    
    async def get_batch(self, batch_id: str) -> Optional[BatchRecord]:
        """Get batch record by ID."""
        try:
            file_path = self.batches_dir / f"{batch_id}.json"
            if not file_path.exists():
                return None
            
            async with aiofiles.open(file_path, 'r') as f:
                data = json.loads(await f.read())
                return BatchRecord(**data)
        except Exception as e:
            logger.error(f"Failed to get batch {batch_id}: {e}")
            return None
    
    async def update_batch(self, batch_id: str, updates: Dict[str, Any]) -> bool:
        """Update batch record."""
        try:
            batch = await self.get_batch(batch_id)
            if not batch:
                return False
            
            # Update fields
            for key, value in updates.items():
                if hasattr(batch, key):
                    setattr(batch, key, value)
            
            batch.updated_at = datetime.utcnow().isoformat()
            return await self.save_batch(batch)
        except Exception as e:
            logger.error(f"Failed to update batch {batch_id}: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        try:
            documents = await self.list_documents()
            
            stats = {
                "total_documents": len(documents),
                "processed": len([d for d in documents if d.status == ProcessingStatus.COMPLETED]),
                "processing": len([d for d in documents if d.status == ProcessingStatus.PROCESSING]),
                "failed": len([d for d in documents if d.status == ProcessingStatus.FAILED]),
                "by_type": {},
                "avg_confidence": 0.0,
                "avg_processing_time": 0.0
            }
            
            # Calculate averages and type distribution
            if documents:
                total_confidence = sum(d.confidence_score for d in documents)
                total_time = sum(d.processing_time for d in documents)
                stats["avg_confidence"] = total_confidence / len(documents)
                stats["avg_processing_time"] = total_time / len(documents)
                
                # Count by document type
                for doc in documents:
                    doc_type = doc.document_type
                    stats["by_type"][doc_type] = stats["by_type"].get(doc_type, 0) + 1
            
            return stats
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}


# Global database instance
db = FileDatabase()
