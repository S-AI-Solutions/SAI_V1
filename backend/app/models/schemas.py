from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    INVOICE = "invoice"
    RECEIPT = "receipt"
    BUSINESS_CARD = "business_card"
    FORM = "form"
    CONTRACT = "contract"
    CUSTOM = "custom"


class ConfidenceLevel(str, Enum):
    HIGH = "high"  # >90%
    MEDIUM = "medium"  # 70-90%
    LOW = "low"  # <70%


class BoundingBox(BaseModel):
    """Spatial bounding box coordinates."""
    x1: int = Field(..., description="Left coordinate")
    y1: int = Field(..., description="Top coordinate")
    x2: int = Field(..., description="Right coordinate")
    y2: int = Field(..., description="Bottom coordinate")
    
    @property
    def width(self) -> int:
        return self.x2 - self.x1
    
    @property
    def height(self) -> int:
        return self.y2 - self.y1
    
    @property
    def center(self) -> tuple:
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)


class TextBlock(BaseModel):
    """Individual text block with spatial information."""
    text: str = Field(..., description="Extracted text")
    confidence: float = Field(..., ge=0, le=1, description="OCR confidence")
    bounding_box: BoundingBox = Field(..., description="Spatial coordinates")
    font_size: int = Field(default=12, description="Estimated font size")
    line_number: int = Field(..., description="Line number in document")


class LayoutElement(BaseModel):
    """Document layout element (header, paragraph, table, etc.)."""
    element_type: str = Field(..., description="Type of layout element")
    bounding_box: BoundingBox = Field(..., description="Spatial coordinates")
    text: str = Field(..., description="Combined text content")
    confidence: float = Field(..., ge=0, le=1, description="Detection confidence")
    text_blocks: List[TextBlock] = Field(default_factory=list, description="Component text blocks")


class FieldLocation(BaseModel):
    x: float = Field(..., description="X coordinate as percentage")
    y: float = Field(..., description="Y coordinate as percentage")
    width: float = Field(..., description="Width as percentage")
    height: float = Field(..., description="Height as percentage")
    
    @classmethod
    def from_dict(cls, data: dict) -> 'FieldLocation':
        """Create FieldLocation from dictionary."""
        return cls(
            x=data.get('x', 0.0),
            y=data.get('y', 0.0),
            width=data.get('width', 0.0),
            height=data.get('height', 0.0)
        )


class ExtractedField(BaseModel):
    value: Any = Field(..., description="Extracted field value")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
    confidence_level: ConfidenceLevel = Field(..., description="Confidence category")
    location: Optional[FieldLocation] = Field(None, description="Field location in document")
    original_text: Optional[str] = Field(None, description="Original text from document")
    validation_errors: List[str] = Field(default_factory=list, description="Validation issues")


class DocumentMetadata(BaseModel):
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    file_type: str = Field(..., description="MIME type")
    dimensions: Optional[Dict[str, int]] = Field(None, description="Image dimensions")
    page_count: Optional[int] = Field(None, description="Number of pages for PDFs")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATING = "validating"


class DocumentProcessingRequest(BaseModel):
    document_type: Optional[DocumentType] = Field(None, description="Document type hint")
    enhance_image: bool = Field(True, description="Apply image enhancement")
    custom_fields: Optional[List[str]] = Field(None, description="Custom fields to extract")


class DocumentProcessingResult(BaseModel):
    id: str = Field(..., description="Unique document ID")
    status: ProcessingStatus = Field(..., description="Processing status")
    document_type: DocumentType = Field(..., description="Detected document type")
    document_type_confidence: float = Field(..., description="Document type confidence")
    metadata: DocumentMetadata = Field(..., description="Document metadata")
    extracted_data: Dict[str, ExtractedField] = Field(..., description="Extracted fields")
    overall_confidence: float = Field(..., description="Overall extraction confidence")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    error_message: Optional[str] = Field(None, description="Error message if failed")


class ValidationRequest(BaseModel):
    field_name: str = Field(..., description="Field to validate/correct")
    new_value: Any = Field(..., description="Corrected value")
    confidence_override: Optional[float] = Field(None, description="Manual confidence override")


class BatchProcessingRequest(BaseModel):
    document_type: Optional[DocumentType] = Field(None, description="Document type for all files")
    enhance_images: bool = Field(True, description="Apply image enhancement")
    custom_fields: Optional[List[str]] = Field(None, description="Custom fields to extract")


class BatchProcessingResult(BaseModel):
    batch_id: str = Field(..., description="Unique batch ID")
    total_documents: int = Field(..., description="Total number of documents")
    processed_documents: int = Field(..., description="Number of processed documents")
    failed_documents: int = Field(..., description="Number of failed documents")
    results: List[DocumentProcessingResult] = Field(..., description="Individual results")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class APIResponse(BaseModel):
    success: bool = Field(..., description="Request success status")
    message: str = Field(..., description="Response message")
    data: Optional[Any] = Field(None, description="Response data")
    errors: Optional[List[str]] = Field(None, description="Error messages")


class HealthCheck(BaseModel):
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(..., description="API version")
    gemini_status: str = Field(..., description="Gemini API status")
    redis_status: str = Field(..., description="Redis status")


class ProcessingStats(BaseModel):
    total_documents: int = Field(..., description="Total processed documents")
    success_rate: float = Field(..., description="Success rate percentage")
    average_confidence: float = Field(..., description="Average confidence score")
    average_processing_time: float = Field(..., description="Average processing time")
    documents_by_type: Dict[str, int] = Field(..., description="Documents count by type")
    hourly_stats: List[Dict[str, Any]] = Field(..., description="Hourly processing stats")
