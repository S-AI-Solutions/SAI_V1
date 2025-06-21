"""Simple Document Processing Service that works with the current schema."""

import asyncio
import uuid
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image, ImageEnhance, ImageFilter
import io

from app.models.schemas import (
    DocumentType, DocumentProcessingResult, ExtractedField,
    DocumentMetadata, ProcessingStatus, BatchProcessingResult
)
from app.services.gemini_service import GeminiService
from app.utils.logging import get_logger
from app.utils.helpers import measure_time

logger = get_logger(__name__)


class DocumentProcessingService:
    """Simple document processing service."""
    
    def __init__(self):
        self.gemini_service = GeminiService()
        # Simple in-memory storage for demo
        self.documents: Dict[str, DocumentProcessingResult] = {}
        self.batches: Dict[str, BatchProcessingResult] = {}
    
    @measure_time
    async def process_document(
        self,
        file_data: bytes,
        filename: str,
        document_type: Optional[DocumentType] = None,
        enhance_image: bool = True,
        custom_fields: Optional[List[str]] = None
    ) -> DocumentProcessingResult:
        """Process a single document and extract data."""
        
        document_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Enhance image if requested
            if enhance_image:
                file_data = await self._enhance_image(file_data)
            
            # Auto-detect document type if not provided
            if not document_type:
                detected_type, type_confidence = await self.gemini_service.detect_document_type(file_data)
                document_type = detected_type
            else:
                type_confidence = 0.9
            
            # Ensure we have a valid document type
            if document_type is None:
                document_type = DocumentType.CUSTOM
                type_confidence = 0.5
            
            # Extract fields using Gemini
            extracted_fields = await self.gemini_service.extract_fields(
                file_data, 
                document_type,
                custom_fields
            )
            
            # Validate extracted fields
            validated_fields = await self.gemini_service.validate_extraction(
                extracted_fields,
                document_type
            )
            
            # Calculate overall confidence
            overall_confidence = self._calculate_overall_confidence(validated_fields)
            processing_time = time.time() - start_time
            
            # Create result
            result = DocumentProcessingResult(
                id=document_id,
                status=ProcessingStatus.COMPLETED,
                document_type=document_type,
                document_type_confidence=type_confidence,
                metadata=DocumentMetadata(
                    filename=filename,
                    file_size=len(file_data),
                    file_type="image/jpeg",  # Default
                    dimensions=None,
                    page_count=None,
                    processing_time=processing_time
                ),
                extracted_data=validated_fields,
                overall_confidence=overall_confidence,
                error_message=None
            )
            
            # Store result
            self.documents[document_id] = result
            
            logger.info(f"Document {document_id} processed successfully in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            error_result = DocumentProcessingResult(
                id=document_id,
                status=ProcessingStatus.FAILED,
                document_type=document_type or DocumentType.CUSTOM,
                document_type_confidence=0.0,
                metadata=DocumentMetadata(
                    filename=filename,
                    file_size=len(file_data),
                    file_type="image/jpeg",
                    dimensions=None,
                    page_count=None,
                    processing_time=time.time() - start_time
                ),
                extracted_data={},
                overall_confidence=0.0,
                error_message=f"Processing failed: {str(e)}"
            )
            
            self.documents[document_id] = error_result
            logger.error(f"Document processing failed for {document_id}: {e}")
            return error_result
    
    async def process_batch(
        self,
        files: List[Tuple[bytes, str]],
        document_type: Optional[DocumentType] = None,
        enhance_images: bool = True
    ) -> BatchProcessingResult:
        """Process multiple documents in batch."""
        
        batch_id = str(uuid.uuid4())
        results = []
        failed_count = 0
        
        try:
            # Process documents with limited concurrency
            semaphore = asyncio.Semaphore(3)
            
            async def process_single(file_data: bytes, filename: str) -> DocumentProcessingResult:
                async with semaphore:
                    return await self.process_document(
                        file_data, filename, document_type, enhance_images
                    )
            
            # Create tasks
            tasks = [process_single(file_data, filename) for file_data, filename in files]
            
            # Process and collect results
            for task in asyncio.as_completed(tasks):
                result = await task
                results.append(result)
                if result.status == ProcessingStatus.FAILED:
                    failed_count += 1
            
            # Create batch result
            batch_result = BatchProcessingResult(
                batch_id=batch_id,
                total_documents=len(files),
                processed_documents=len(results),
                failed_documents=failed_count,
                results=results
            )
            
            # Store batch result
            self.batches[batch_id] = batch_result
            
            logger.info(f"Batch {batch_id} completed: {len(results) - failed_count}/{len(files)} successful")
            return batch_result
            
        except Exception as e:
            logger.error(f"Batch processing failed for {batch_id}: {e}")
            # Return empty batch result on error
            return BatchProcessingResult(
                batch_id=batch_id,
                total_documents=len(files),
                processed_documents=0,
                failed_documents=len(files),
                results=[]
            )
    
    async def get_document_result(self, document_id: str) -> Optional[DocumentProcessingResult]:
        """Get document processing result by ID."""
        return self.documents.get(document_id)
    
    async def get_batch_result(self, batch_id: str) -> Optional[BatchProcessingResult]:
        """Get batch processing result by ID."""
        return self.batches.get(batch_id)
    
    async def validate_document_fields(
        self,
        document_id: str,
        field_updates: Dict[str, str]
    ) -> Optional[DocumentProcessingResult]:
        """Validate and update document fields."""
        try:
            result = self.documents.get(document_id)
            if not result:
                return None
            
            # Update fields with user corrections
            for field_name, new_value in field_updates.items():
                if field_name in result.extracted_data:
                    result.extracted_data[field_name].value = new_value
                    result.extracted_data[field_name].confidence = 1.0  # User-validated
                    result.extracted_data[field_name].validation_errors = []
            
            # Recalculate overall confidence
            result.overall_confidence = self._calculate_overall_confidence(result.extracted_data)
            
            # Update stored result
            self.documents[document_id] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Field validation failed for {document_id}: {e}")
            return None
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        try:
            total_docs = len(self.documents)
            completed_docs = sum(1 for doc in self.documents.values() if doc.status == ProcessingStatus.COMPLETED)
            failed_docs = sum(1 for doc in self.documents.values() if doc.status == ProcessingStatus.FAILED)
            
            stats = {
                "total_documents": total_docs,
                "processed": completed_docs,
                "failed": failed_docs,
                "success_rate": (completed_docs / total_docs * 100) if total_docs > 0 else 0,
                "by_type": {},
                "avg_confidence": 0.0,
                "avg_processing_time": 0.0
            }
            
            if self.documents:
                # Calculate averages
                confidences = [doc.overall_confidence for doc in self.documents.values() if doc.overall_confidence > 0]
                processing_times = [doc.metadata.processing_time for doc in self.documents.values() if doc.metadata.processing_time]
                
                if confidences:
                    stats["avg_confidence"] = sum(confidences) / len(confidences)
                if processing_times:
                    stats["avg_processing_time"] = sum(processing_times) / len(processing_times)
                
                # Count by document type
                for doc in self.documents.values():
                    doc_type = doc.document_type.value
                    stats["by_type"][doc_type] = stats["by_type"].get(doc_type, 0) + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
    
    async def cleanup_old_results(self, days: int = 7) -> int:
        """Clean up old processing results."""
        # Simple cleanup - remove all results older than X days
        # In production, this would check timestamps
        try:
            old_count = len(self.documents)
            # For now, just clear everything as a demo
            if days <= 0:
                self.documents.clear()
                self.batches.clear()
                return old_count
            return 0
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return 0
    
    # Helper methods
    
    async def _enhance_image(self, image_data: bytes) -> bytes:
        """Enhance image quality for better OCR."""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Enhance contrast and sharpness
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)
            
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.1)
            
            # Apply slight denoising
            image = image.filter(ImageFilter.MedianFilter(size=3))
            
            # Convert back to bytes
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=95)
            return output.getvalue()
            
        except Exception as e:
            logger.warning(f"Image enhancement failed: {e}")
            return image_data  # Return original if enhancement fails
    
    def _calculate_overall_confidence(self, extracted_data: Dict[str, ExtractedField]) -> float:
        """Calculate overall confidence score."""
        if not extracted_data:
            return 0.0
        
        confidences = [field.confidence for field in extracted_data.values()]
        return sum(confidences) / len(confidences)
