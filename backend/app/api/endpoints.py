from fastapi import APIRouter, HTTPException, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import Optional, List
import json

from app.models.schemas import (
    DocumentType, APIResponse, DocumentProcessingRequest,
    ValidationRequest, BatchProcessingRequest, ProcessingStats, HealthCheck
)
from app.services.document_service import DocumentProcessingService
from app.services.production_document_service import ProductionDocumentService
from app.services.universal_extraction_service import UniversalExtractionService
from app.utils.logging import get_logger
from app.config import settings

logger = get_logger(__name__)
router = APIRouter()

# Initialize document processing services
document_service = DocumentProcessingService()
production_service = ProductionDocumentService()
# Initialize universal extraction service
universal_service = UniversalExtractionService()

# WebSocket connections for real-time updates
active_connections: List[WebSocket] = []


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Connection might be closed
                pass


connection_manager = ConnectionManager()


@router.post("/process", response_model=APIResponse)
async def process_document(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(None),
    enhance_image: bool = Form(True),
    custom_fields: Optional[str] = Form(None)
):
    """Process a single document and extract data."""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file size
        file_data = await file.read()
        if len(file_data) > settings.max_file_size:
            raise HTTPException(status_code=413, detail="File too large")
        
        # Validate file type
        file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        if file_extension not in settings.allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Allowed: {', '.join(settings.allowed_extensions)}"
            )
        
        # Parse document type
        doc_type = None
        if document_type:
            try:
                doc_type = DocumentType(document_type)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid document type")
        
        # Parse custom fields
        custom_fields_list = None
        if custom_fields:
            try:
                custom_fields_list = json.loads(custom_fields)
            except json.JSONDecodeError:
                custom_fields_list = [field.strip() for field in custom_fields.split(',') if field.strip()]
        
        # Process document
        result = await document_service.process_document(
            file_data=file_data,
            filename=file.filename,
            document_type=doc_type,
            enhance_image=enhance_image,
            custom_fields=custom_fields_list
        )
        
        # Broadcast processing complete via WebSocket
        await connection_manager.broadcast(json.dumps({
            "type": "document_processed",
            "document_id": result.id,
            "status": result.status.value,
            "confidence": result.overall_confidence
        }))
        
        return APIResponse(
            success=True,
            message="Document processed successfully",
            data=result.dict(),
            errors=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document processing failed: {e}")
        return APIResponse(
            success=False,
            message="Document processing failed",
            data=None,
            errors=[str(e)]
        )


@router.post("/process-production", response_model=APIResponse)
async def process_document_production(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(None),
    enhance_image: bool = Form(True),
    custom_fields: Optional[str] = Form(None),
    accuracy_mode: str = Form("high")  # "fast", "balanced", "high"
):
    """Process document with production-grade accuracy (Google Document AI parity)."""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file size
        file_data = await file.read()
        if len(file_data) > settings.max_file_size:
            raise HTTPException(status_code=413, detail="File too large")
        
        # Validate file type
        file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        if file_extension not in settings.allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Allowed: {', '.join(settings.allowed_extensions)}"
            )
        
        # Validate accuracy mode
        if accuracy_mode not in ["fast", "balanced", "high"]:
            raise HTTPException(status_code=400, detail="Invalid accuracy mode")
        
        # Parse document type
        doc_type = None
        if document_type:
            try:
                doc_type = DocumentType(document_type)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid document type")
        
        # Parse custom fields
        custom_fields_list = None
        if custom_fields:
            try:
                custom_fields_list = json.loads(custom_fields)
            except json.JSONDecodeError:
                custom_fields_list = [field.strip() for field in custom_fields.split(',') if field.strip()]
        
        # Process document with production service
        result = await production_service.process_document_production(
            file_data=file_data,
            filename=file.filename,
            document_type=doc_type,
            enhance_image=enhance_image,
            custom_fields=custom_fields_list,
            accuracy_mode=accuracy_mode
        )
        
        # Broadcast processing complete via WebSocket
        await connection_manager.broadcast(json.dumps({
            "type": "document_processed",
            "document_id": result.id,
            "status": result.status.value,
            "confidence": result.overall_confidence,
            "accuracy_mode": accuracy_mode,
            "field_count": len(result.extracted_data)
        }))
        
        return APIResponse(
            success=True,
            message=f"Document processed successfully with {accuracy_mode} accuracy",
            data=result.dict(),
            errors=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Production document processing failed: {e}")
        return APIResponse(
            success=False,
            message="Production document processing failed",
            data=None,
            errors=[str(e)]
        )


@router.post("/batch", response_model=APIResponse)
async def process_batch(
    files: List[UploadFile] = File(...),
    document_type: Optional[str] = Form(None),
    enhance_images: bool = Form(True),
    custom_fields: Optional[str] = Form(None)
):
    """Process multiple documents in batch."""
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        
        # Validate files
        files_data = []
        total_size = 0
        
        for file in files:
            if not file.filename:
                continue
                
            file_data = await file.read()
            total_size += len(file_data)
            
            # Check individual file size
            if len(file_data) > settings.max_file_size:
                raise HTTPException(
                    status_code=413, 
                    detail=f"File {file.filename} too large"
                )
            
            # Validate file type
            file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
            if file_extension not in settings.allowed_extensions:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type in {file.filename}"
                )
            
            files_data.append((file_data, file.filename))
        
        # Check total batch size
        if total_size > settings.max_file_size * 10:  # Allow 10x individual limit for batch
            raise HTTPException(status_code=413, detail="Batch size too large")
        
        # Parse document type
        doc_type = None
        if document_type:
            try:
                doc_type = DocumentType(document_type)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid document type")
        
        # Parse custom fields
        custom_fields_list = None
        if custom_fields:
            try:
                custom_fields_list = json.loads(custom_fields)
            except json.JSONDecodeError:
                custom_fields_list = [field.strip() for field in custom_fields.split(',') if field.strip()]
        
        # Process batch
        result = await document_service.process_batch(
            files=files_data,
            document_type=doc_type,
            enhance_images=enhance_images
        )
        
        # Broadcast batch completion
        await connection_manager.broadcast(json.dumps({
            "type": "batch_processed",
            "batch_id": result.batch_id,
            "total_documents": result.total_documents,
            "processed_documents": result.processed_documents,
            "failed_documents": result.failed_documents
        }))
        
        return APIResponse(
            success=True,
            message="Batch processed successfully",
            data=result.dict(),
            errors=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch processing endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}", response_model=APIResponse)
async def get_document_result(document_id: str):
    """Retrieve processing result by document ID."""
    try:
        result = await document_service.get_document_result(document_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return APIResponse(
            success=True,
            message="Document result retrieved successfully",
            data=result.dict(),
            errors=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document result error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate", response_model=APIResponse)
async def validate_field(request: ValidationRequest, document_id: str):
    """Validate and correct an extracted field."""
    try:
        result = await document_service.validate_document_fields(
            document_id=document_id,
            field_updates={request.field_name: request.new_value}
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Document or field not found")
        
        # Get updated result
        result = await document_service.get_document_result(document_id)
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated result")
        
        return APIResponse(
            success=True,
            message="Field validated and updated successfully",
            data=result.dict(),
            errors=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Field validation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/document-types", response_model=APIResponse)
async def get_document_types():
    """List supported document types."""
    try:
        document_types = [
            {
                "value": doc_type.value,
                "name": doc_type.value.replace('_', ' ').title(),
                "description": f"Extract data from {doc_type.value.replace('_', ' ')} documents"
            }
            for doc_type in DocumentType
        ]
        
        return APIResponse(
            success=True,
            message="Document types retrieved successfully",
            data=document_types,
            errors=None
        )
        
    except Exception as e:
        logger.error(f"Get document types error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=APIResponse)
async def get_processing_stats():
    """Get processing statistics."""
    try:
        stats = await document_service.get_processing_stats()
        
        return APIResponse(
            success=True,
            message="Processing statistics retrieved successfully",
            data=stats,
            errors=None
        )
        
    except Exception as e:
        logger.error(f"Get processing stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint."""
    try:
        # Check Gemini API status (mock for now)
        gemini_status = "ok" if settings.gemini_api_key else "not_configured"
        
        # Check Redis status (mock for now)
        redis_status = "ok"  # Would check actual Redis connection
        
        return HealthCheck(
            status="healthy",
            version=settings.version,
            gemini_status=gemini_status,
            redis_status=redis_status
        )
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return HealthCheck(
            status="unhealthy",
            version=settings.version,
            gemini_status="error",
            redis_status="error"
        )


@router.websocket("/ws/progress")
async def websocket_progress(websocket: WebSocket):
    """WebSocket endpoint for real-time processing updates."""
    await connection_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        connection_manager.disconnect(websocket)


@router.get("/production-stats", response_model=APIResponse)
async def get_production_stats():
    """Get comprehensive production processing statistics."""
    try:
        stats = await production_service.get_production_stats()
        
        return APIResponse(
            success=True,
            message="Production statistics retrieved successfully",
            data=stats,
            errors=None
        )
        
    except Exception as e:
        logger.error(f"Failed to get production stats: {e}")
        return APIResponse(
            success=False,
            message="Failed to retrieve production statistics",
            data=None,
            errors=[str(e)]
        )


@router.get("/compare-services")
async def compare_services():
    """Compare standard vs production service capabilities."""
    try:
        standard_stats = await document_service.get_processing_stats()
        production_stats = await production_service.get_production_stats()
        
        comparison = {
            "standard_service": {
                "total_processed": standard_stats.get("total_documents", 0),
                "avg_confidence": standard_stats.get("avg_confidence", 0.0),
                "avg_processing_time": standard_stats.get("avg_processing_time", 0.0),
                "features": ["basic_extraction", "image_enhancement"]
            },
            "production_service": {
                "total_processed": production_stats.get("total_processed", 0),
                "avg_confidence": production_stats.get("avg_confidence", 0.0),
                "avg_processing_time": production_stats.get("avg_processing_time", 0.0),
                "features": production_stats.get("features", {}),
                "confidence_distribution": production_stats.get("confidence_distribution", {}),
                "document_types": production_stats.get("by_type", {})
            },
            "comparison_metrics": {
                "confidence_improvement": (
                    production_stats.get("avg_confidence", 0.0) - 
                    standard_stats.get("avg_confidence", 0.0)
                ) * 100,
                "production_advantages": [
                    "Multi-pass extraction for higher accuracy",
                    "Advanced field validation and auto-correction", 
                    "Spatial coordinate detection",
                    "Enhanced confidence calibration",
                    "Document-specific prompting",
                    "Cross-field validation"
                ]
            }
        }
        
        return APIResponse(
            success=True,
            message="Service comparison completed",
            data=comparison,
            errors=None
        )
        
    except Exception as e:
        logger.error(f"Service comparison failed: {e}")
        return APIResponse(
            success=False,
            message="Service comparison failed",
            data=None,
            errors=[str(e)]
        )


@router.post("/extract-universal", response_model=APIResponse)
async def extract_universal(
    file: UploadFile = File(..., description="Document image to extract all information from"),
    extraction_mode: str = Form("comprehensive", description="Extraction mode: basic, comprehensive, or detailed"),
    include_ocr: bool = Form(True, description="Include raw OCR data in response"),
    include_analysis: bool = Form(True, description="Include document structure analysis")
):
    """
    Universal document extraction - extracts ALL information from any document type.
    
    This endpoint can handle any document type and extracts every piece of visible information
    including text, numbers, tables, metadata, parties, and structural elements.
    
    Perfect for documents like:
    - E-way bills, GST invoices, transport documents
    - Government forms, certificates, permits
    - Financial statements, bank documents
    - Medical reports, lab results
    - Legal documents, contracts
    - Any structured or unstructured document
    """
    try:
        # Validate file
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Only image files are supported")
        
        # Validate extraction mode
        if extraction_mode not in ["basic", "comprehensive", "detailed"]:
            raise HTTPException(status_code=400, detail="Invalid extraction mode. Use: basic, comprehensive, or detailed")
        
        # Read file data
        file_data = await file.read()
        if len(file_data) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")
        
        logger.info(f"Starting universal extraction for {file.filename} in {extraction_mode} mode")
        
        # Perform universal extraction
        extraction_results = await universal_service.extract_everything(
            file_data, extraction_mode
        )
        
        # Prepare response data
        response_data = {
            "extraction_results": extraction_results["extracted_data"],
            "metadata": extraction_results["extraction_metadata"],
            "filename": file.filename,
            "extraction_mode": extraction_mode
        }
        
        # Include optional data based on parameters
        if include_analysis:
            response_data["document_analysis"] = extraction_results["document_analysis"]
        
        if include_ocr:
            response_data["raw_ocr"] = extraction_results["raw_ocr"]
        
        # Add extraction summary
        extracted_data = extraction_results["extracted_data"]
        response_data["summary"] = {
            "total_fields_extracted": len(extracted_data),
            "document_type": extraction_results.get("document_analysis", {}).get("structure_type", "unknown"),
            "confidence": extraction_results["extraction_metadata"].get("confidence", 0.0),
            "field_categories": list(set([
                field_name.split('_')[0] for field_name in extracted_data.keys()
            ]))
        }
        
        logger.info(f"Universal extraction completed: {len(extracted_data)} fields extracted")
        
        return APIResponse(
            success=True,
            message=f"Universal extraction completed successfully with {extraction_mode} mode",
            data=response_data,
            errors=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Universal extraction failed: {e}")
        return APIResponse(
            success=False,
            message="Universal extraction failed",
            data=None,
            errors=[str(e)]
        )
