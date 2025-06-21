"""Enhanced Document Processing Service with enterprise-grade capabilities."""

import asyncio
import uuid
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
from PIL import Image, ImageEnhance, ImageFilter
import io

from app.models.schemas import (
    DocumentType, DocumentProcessingResult, ExtractedField,
    DocumentMetadata, ProcessingStatus, BatchProcessingResult,
    FieldLocation, BoundingBox
)
from app.services.gemini_service import GeminiService
from app.utils.logging import get_logger
from app.utils.helpers import measure_time

logger = get_logger(__name__)


class EnterpriseDocumentService:
    """Enterprise-grade document processing service with advanced capabilities."""
    
    def __init__(self):
        self.gemini_service = GeminiService()
        
        # Try to initialize enhanced services
        try:
            from app.services.enhanced_ocr_service import EnhancedOCRService
            from app.services.enhanced_gemini_service import EnhancedGeminiService
            
            self.enhanced_ocr = EnhancedOCRService()
            self.enhanced_gemini = EnhancedGeminiService()
            self.use_enhanced = True
            logger.info("Enhanced processing services initialized")
            
        except ImportError as e:
            logger.warning(f"Enhanced services not available: {e}")
            self.enhanced_ocr = None
            self.enhanced_gemini = None
            self.use_enhanced = False
        
        # Simple in-memory storage for demo
        self.documents: Dict[str, DocumentProcessingResult] = {}
        self.batches: Dict[str, BatchProcessingResult] = {}
        self.processing_stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "avg_confidence": 0.0,
            "avg_processing_time": 0.0
        }

    @measure_time
    async def process_document_enterprise(
        self,
        file_data: bytes,
        filename: str,
        document_type: Optional[DocumentType] = None,
        enhance_image: bool = True,
        custom_fields: Optional[List[str]] = None,
        quality_mode: str = "balanced"  # "fast", "balanced", "high_accuracy"
    ) -> DocumentProcessingResult:
        """Enterprise-grade document processing with multiple quality modes."""
        
        document_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Step 1: Image preprocessing
            if enhance_image:
                file_data = await self._enhance_image_enterprise(file_data, quality_mode)
            
            # Step 2: Document type detection
            if not document_type:
                document_type, type_confidence = await self._detect_document_type_enterprise(file_data)
            else:
                type_confidence = 0.95  # User-specified type
            
            # Step 3: Choose processing pipeline based on mode
            if self.use_enhanced and quality_mode in ["balanced", "high_accuracy"]:
                extracted_data, ocr_results = await self._process_with_enhanced_pipeline(
                    file_data, document_type, quality_mode
                )
            else:
                # Fallback to standard processing
                extracted_data = await self._process_with_standard_pipeline(
                    file_data, document_type
                )
                ocr_results = None
            
            # Step 4: Post-processing and validation
            extracted_data = await self._post_process_fields(extracted_data, document_type)
            
            # Step 5: Calculate metrics
            overall_confidence = self._calculate_overall_confidence(extracted_data)
            processing_time = time.time() - start_time
            
            # Step 6: Create metadata
            metadata = await self._create_enhanced_metadata(
                filename, file_data, processing_time, ocr_results
            )
            
            # Step 7: Create result
            result = DocumentProcessingResult(
                id=document_id,
                status=ProcessingStatus.COMPLETED,
                document_type=document_type,
                document_type_confidence=type_confidence,
                metadata=metadata,
                extracted_data=extracted_data,
                overall_confidence=overall_confidence,
                error_message=None
            )
            
            # Store result
            self.documents[document_id] = result
            
            # Update stats
            await self._update_processing_stats(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Enterprise document processing failed: {e}")
            
            # Create failed result
            result = DocumentProcessingResult(
                id=document_id,
                status=ProcessingStatus.FAILED,
                document_type=document_type or DocumentType.CUSTOM,
                document_type_confidence=0.0,
                metadata=DocumentMetadata(
                    filename=filename,
                    file_size=len(file_data),
                    file_type="unknown",
                    dimensions=None,
                    page_count=None,
                    processing_time=time.time() - start_time
                ),
                extracted_data={},
                overall_confidence=0.0,
                error_message=str(e)
            )
            
            self.documents[document_id] = result
            return result

    async def _enhance_image_enterprise(self, image_data: bytes, quality_mode: str) -> bytes:
        """Enterprise-grade image enhancement."""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Apply enhancements based on quality mode
            if quality_mode == "high_accuracy":
                # Maximum enhancement for best OCR results
                image = await self._apply_advanced_enhancement(image)
            elif quality_mode == "balanced":
                # Balanced enhancement
                image = await self._apply_standard_enhancement(image)
            # "fast" mode - minimal enhancement
            
            # Convert back to bytes
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=95)
            return output.getvalue()
            
        except Exception as e:
            logger.warning(f"Image enhancement failed: {e}")
            return image_data

    async def _apply_advanced_enhancement(self, image: Image.Image) -> Image.Image:
        """Apply advanced image enhancement for maximum OCR accuracy."""
        try:
            # Enhance contrast more aggressively
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.3)
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.2)
            
            # Enhance brightness if needed
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.1)
            
            # Apply denoising
            image = image.filter(ImageFilter.MedianFilter(size=3))
            
            return image
            
        except Exception as e:
            logger.warning(f"Advanced enhancement failed: {e}")
            return image

    async def _apply_standard_enhancement(self, image: Image.Image) -> Image.Image:
        """Apply standard image enhancement."""
        try:
            # Moderate contrast enhancement
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)
            
            # Moderate sharpness enhancement
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.1)
            
            return image
            
        except Exception as e:
            logger.warning(f"Standard enhancement failed: {e}")
            return image

    async def _detect_document_type_enterprise(self, image_data: bytes) -> Tuple[DocumentType, float]:
        """Enterprise document type detection."""
        try:
            if self.use_enhanced and self.enhanced_gemini:
                # Use enhanced Gemini service - fallback to standard detection since method doesn't exist
                return await self.gemini_service.detect_document_type(image_data)
            else:
                # Fallback to standard detection
                return await self.gemini_service.detect_document_type(image_data)
                
        except Exception as e:
            logger.error(f"Document type detection failed: {e}")
            return DocumentType.CUSTOM, 0.5

    async def _process_with_enhanced_pipeline(
        self, 
        image_data: bytes, 
        document_type: DocumentType,
        quality_mode: str
    ) -> Tuple[Dict[str, ExtractedField], Dict]:
        """Process document using enhanced pipeline with OCR and multi-pass extraction."""
        try:
            # Step 1: Enhanced OCR extraction
            if self.enhanced_ocr:
                ocr_results = await self.enhanced_ocr.extract_text_with_layout(image_data)
            else:
                ocr_results = {}
            
            # Step 2: Enhanced Gemini processing
            if self.enhanced_gemini:
                processing_results = await self.enhanced_gemini.process_document_enhanced(
                    image_data, document_type, ocr_results, accuracy_mode=quality_mode
                )
                return processing_results["extracted_data"], ocr_results
            else:
                # Fallback to standard pipeline
                extracted_data = await self._process_with_standard_pipeline(image_data, document_type)
                return extracted_data, ocr_results
            
        except Exception as e:
            logger.error(f"Enhanced pipeline failed, falling back to standard: {e}")
            # Fallback to standard pipeline
            extracted_data = await self._process_with_standard_pipeline(image_data, document_type)
            return extracted_data, {}

    async def _process_with_standard_pipeline(
        self, 
        image_data: bytes, 
        document_type: DocumentType
    ) -> Dict[str, ExtractedField]:
        """Process document using standard Gemini service."""
        return await self.gemini_service.extract_fields(image_data, document_type)

    async def _post_process_fields(
        self, 
        extracted_data: Dict[str, ExtractedField], 
        document_type: DocumentType
    ) -> Dict[str, ExtractedField]:
        """Post-process extracted fields for consistency and quality."""
        
        processed_fields = {}
        
        for field_name, field in extracted_data.items():
            # Clean and normalize field values
            cleaned_value = await self._clean_field_value(field_name, field.value)
            
            # Validate field format
            validation_errors = await self._validate_field_format(field_name, cleaned_value, document_type)
            
            # Adjust confidence based on validation
            adjusted_confidence = field.confidence
            if validation_errors:
                adjusted_confidence *= 0.8
            
            # Create processed field
            processed_fields[field_name] = ExtractedField(
                value=cleaned_value,
                confidence=adjusted_confidence,
                confidence_level=self._get_confidence_level(adjusted_confidence),
                location=field.location,
                original_text=field.original_text,
                validation_errors=validation_errors
            )
        
        return processed_fields

    async def _clean_field_value(self, field_name: str, value: Any) -> Any:
        """Clean and normalize field value."""
        if not value:
            return value
        
        value_str = str(value).strip()
        
        # Currency field cleaning
        if any(curr in field_name.lower() for curr in ['amount', 'total', 'price', 'cost']):
            # Remove extra spaces, normalize currency format
            value_str = ' '.join(value_str.split())
            # Ensure proper decimal formatting
            import re
            value_str = re.sub(r'(\d),(\d{3})', r'\1,\2', value_str)
        
        # Date field cleaning
        if any(date_word in field_name.lower() for date_word in ['date', 'due', 'created']):
            # Normalize date separators
            value_str = value_str.replace('/', '-').replace('.', '-')
        
        # Name field cleaning
        if any(name_word in field_name.lower() for name_word in ['name', 'vendor', 'customer', 'company']):
            # Proper case for names
            value_str = ' '.join(word.capitalize() for word in value_str.split())
        
        return value_str

    async def _validate_field_format(self, field_name: str, value: Any, document_type: DocumentType) -> List[str]:
        """Validate field format and content."""
        errors = []
        
        if not value:
            return errors
        
        value_str = str(value).strip()
        
        # Currency validation
        if any(curr in field_name.lower() for curr in ['amount', 'total', 'price', 'cost']):
            import re
            if not re.search(r'[\d,]+\.?\d*', value_str):
                errors.append(f"Invalid currency format")
        
        # Email validation
        if 'email' in field_name.lower():
            import re
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value_str):
                errors.append(f"Invalid email format")
        
        # Phone validation
        if 'phone' in field_name.lower():
            import re
            # Remove all non-digits and check length
            digits_only = re.sub(r'[^\d]', '', value_str)
            if len(digits_only) < 7 or len(digits_only) > 15:
                errors.append(f"Invalid phone number length")
        
        return errors

    async def _create_enhanced_metadata(
        self, 
        filename: str, 
        file_data: bytes, 
        processing_time: float,
        ocr_results: Optional[Dict] = None
    ) -> DocumentMetadata:
        """Create enhanced metadata with OCR information."""
        
        # Basic metadata
        file_size = len(file_data)
        file_type = self._detect_file_type(filename, file_data)
        
        # Image dimensions if available
        dimensions = None
        try:
            image = Image.open(io.BytesIO(file_data))
            dimensions = {"width": image.width, "height": image.height}
        except Exception:
            pass
        
        # OCR statistics if available
        if ocr_results:
            # Add OCR confidence to metadata
            ocr_confidence = ocr_results.get('confidence', 0.0)
            text_blocks_count = len(ocr_results.get('text_blocks', []))
            
            # Note: In a real implementation, you'd store these in a custom metadata field
            # For now, we'll use the standard metadata structure
        
        return DocumentMetadata(
            filename=filename,
            file_size=file_size,
            file_type=file_type,
            dimensions=dimensions,
            page_count=1,  # For images; would be different for PDFs
            processing_time=processing_time
        )

    def _detect_file_type(self, filename: str, file_data: bytes) -> str:
        """Detect file MIME type."""
        try:
            # Simple detection based on file signature
            if file_data.startswith(b'\xff\xd8\xff'):
                return 'image/jpeg'
            elif file_data.startswith(b'\x89PNG'):
                return 'image/png'
            elif file_data.startswith(b'%PDF'):
                return 'application/pdf'
            elif filename.lower().endswith('.tiff') or filename.lower().endswith('.tif'):
                return 'image/tiff'
            else:
                return 'application/octet-stream'
        except Exception:
            return 'application/octet-stream'

    def _get_confidence_level(self, confidence: float):
        """Convert confidence score to confidence level."""
        from app.models.schemas import ConfidenceLevel
        if confidence >= 0.9:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.7:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def _calculate_overall_confidence(self, extracted_data: Dict[str, ExtractedField]) -> float:
        """Calculate overall confidence score."""
        if not extracted_data:
            return 0.0
        
        confidences = [field.confidence for field in extracted_data.values()]
        return sum(confidences) / len(confidences)

    async def _update_processing_stats(self, result: DocumentProcessingResult):
        """Update processing statistics."""
        self.processing_stats["total_processed"] += 1
        
        if result.status == ProcessingStatus.COMPLETED:
            self.processing_stats["successful"] += 1
            
            # Update running averages
            total = self.processing_stats["total_processed"]
            current_avg_conf = self.processing_stats["avg_confidence"]
            current_avg_time = self.processing_stats["avg_processing_time"]
            
            # Incremental average calculation
            self.processing_stats["avg_confidence"] = (
                (current_avg_conf * (total - 1) + result.overall_confidence) / total
            )
            
            if result.metadata.processing_time:
                self.processing_stats["avg_processing_time"] = (
                    (current_avg_time * (total - 1) + result.metadata.processing_time) / total
                )
        else:
            self.processing_stats["failed"] += 1

    async def get_processing_stats_enterprise(self) -> Dict[str, Any]:
        """Get comprehensive processing statistics."""
        base_stats = self.processing_stats.copy()
        
        # Add additional enterprise metrics
        total = base_stats["total_processed"]
        base_stats.update({
            "success_rate": (base_stats["successful"] / total * 100) if total > 0 else 0,
            "failure_rate": (base_stats["failed"] / total * 100) if total > 0 else 0,
            "documents_by_type": self._get_type_distribution(),
            "confidence_distribution": self._get_confidence_distribution(),
            "processing_mode": "enhanced" if self.use_enhanced else "standard"
        })
        
        return base_stats

    def _get_type_distribution(self) -> Dict[str, int]:
        """Get distribution of document types processed."""
        type_counts = {}
        for doc in self.documents.values():
            doc_type = doc.document_type.value
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
        return type_counts

    def _get_confidence_distribution(self) -> Dict[str, int]:
        """Get distribution of confidence levels."""
        confidence_counts = {"high": 0, "medium": 0, "low": 0}
        
        for doc in self.documents.values():
            if doc.overall_confidence >= 0.9:
                confidence_counts["high"] += 1
            elif doc.overall_confidence >= 0.7:
                confidence_counts["medium"] += 1
            else:
                confidence_counts["low"] += 1
        
        return confidence_counts

    # Batch processing methods
    async def process_batch_enterprise(
        self,
        files_data: List[Tuple[bytes, str]],
        document_type: Optional[DocumentType] = None,
        quality_mode: str = "balanced",
        max_concurrent: int = 3
    ) -> BatchProcessingResult:
        """Enterprise batch processing with concurrency control."""
        
        batch_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single(file_data: bytes, filename: str) -> DocumentProcessingResult:
            async with semaphore:
                return await self.process_document_enterprise(
                    file_data, filename, document_type, 
                    enhance_image=True, quality_mode=quality_mode
                )
        
        # Process all files concurrently
        tasks = [
            process_single(file_data, filename) 
            for file_data, filename in files_data
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Separate successful and failed results
        successful_results = []
        failed_count = 0
        
        for result in results:
            if isinstance(result, Exception):
                failed_count += 1
                logger.error(f"Batch processing error: {result}")
            elif isinstance(result, DocumentProcessingResult):
                successful_results.append(result)
                # Check if the processing result failed
                if result.status == ProcessingStatus.FAILED:
                    failed_count += 1
            else:
                # Handle unexpected result types
                failed_count += 1
                logger.error(f"Unexpected result type: {type(result)}")
        
        # Create batch result
        batch_result = BatchProcessingResult(
            batch_id=batch_id,
            total_documents=len(files_data),
            processed_documents=len(successful_results),
            failed_documents=failed_count,
            results=successful_results
        )
        
        self.batches[batch_id] = batch_result
        
        logger.info(f"Batch {batch_id} completed: {len(successful_results)}/{len(files_data)} successful")
        
        return batch_result
