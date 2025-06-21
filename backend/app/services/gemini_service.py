import io
import asyncio
import base64
from typing import Optional, Tuple, Dict, Any
from PIL import Image
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None
from app.config import settings
from app.models.schemas import DocumentType, ExtractedField, ConfidenceLevel
from app.utils.logging import get_logger
from app.utils.helpers import retry_async, measure_time
import json
import re

logger = get_logger(__name__)


class GeminiService:
    """Service for interacting with Google Gemini API for document processing."""
    
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model_name = settings.gemini_model
        
        # Configure Gemini API
        self.use_real_api = False
        self.model = None
        
        if GEMINI_AVAILABLE and self.api_key and self.api_key != "your-gemini-api-key-here":
            try:
                # Try to configure and initialize Gemini
                if hasattr(genai, 'configure'):
                    genai.configure(api_key=self.api_key)  # type: ignore
                if hasattr(genai, 'GenerativeModel'):
                    self.model = genai.GenerativeModel(self.model_name)  # type: ignore
                self.use_real_api = True
                logger.info("Gemini API configured successfully")
            except Exception as e:
                logger.error(f"Failed to configure Gemini API: {e}")
                self.model = None
                self.use_real_api = False
        
        if not self.use_real_api:
            if not GEMINI_AVAILABLE:
                logger.warning("google-generativeai package not available, using mock responses")
            else:
                logger.warning("Gemini API key not configured, using mock responses")
        
        self.document_type_prompts = self._load_document_type_prompts()
    
    def _load_document_type_prompts(self) -> Dict[str, str]:
        """Load document type-specific extraction prompts."""
        return {
            DocumentType.INVOICE: """
            Analyze this invoice document and extract the following fields with precision:
            
            Required fields: vendor_name, invoice_number, invoice_date, total_amount, currency
            Optional fields: vendor_address, customer_name, due_date, subtotal, tax_amount, items
            
            Return JSON format:
            {
              "vendor_name": {"value": "Company Name", "confidence": 0.95},
              "invoice_number": {"value": "INV-123", "confidence": 0.90},
              "total_amount": {"value": "1234.56", "confidence": 0.95}
            }
            """,
            
            DocumentType.RECEIPT: """
            Analyze this receipt and extract: merchant_name, transaction_date, total_amount, 
            payment_method, items (if visible). Return in JSON format with confidence scores.
            """,
            
            DocumentType.BUSINESS_CARD: """
            Extract contact information: full_name, company, title, email, phone, address.
            Return in JSON format with confidence scores.
            """,
            
            DocumentType.CUSTOM: """
            Analyze this document and extract all meaningful data as key-value pairs.
            Focus on names, dates, amounts, addresses, and other important information.
            Return in JSON format with confidence scores.
            """
        }
    
    @measure_time
    async def detect_document_type(self, image_data: bytes) -> Tuple[DocumentType, float]:
        """Detect document type using image analysis."""
        try:
            if self.use_real_api and self.model:
                # Convert image to format Gemini can process
                image = await self._prepare_image(image_data)
                
                prompt = """
                Analyze this document image and classify it as one of the following types:
                - INVOICE (bills, invoices with vendor information and line items)
                - RECEIPT (store receipts, payment confirmations)
                - BUSINESS_CARD (contact cards with name, company, contact details)
                - ID_CARD (identification documents, licenses)
                - CUSTOM (any other document type)
                
                Return only the document type and confidence score in this exact JSON format:
                {"document_type": "INVOICE", "confidence": 0.95}
                """
                
                response = await self._generate_content(prompt, image)
                result = self._parse_json_response(response)
                
                if result:
                    doc_type_str = result.get('document_type', 'CUSTOM')
                    confidence = float(result.get('confidence', 0.0))
                    
                    # Convert string to DocumentType enum
                    try:
                        doc_type = DocumentType(doc_type_str)
                    except ValueError:
                        doc_type = DocumentType.CUSTOM
                    
                    return doc_type, confidence
            
            # Fallback to mock detection
            logger.info("Using mock document type detection")
            return DocumentType.INVOICE, 0.85
            
        except Exception as e:
            logger.error(f"Document type detection failed: {e}")
            return DocumentType.CUSTOM, 0.0
    
    @measure_time
    async def extract_fields(
        self, 
        image_data: bytes, 
        document_type: DocumentType,
        custom_fields: Optional[list] = None
    ) -> Dict[str, ExtractedField]:
        """Extract fields from document using Gemini API or mock processing."""
        try:
            if self.use_real_api and self.model:
                # Use real Gemini API
                image = await self._prepare_image(image_data)
                prompt = self._build_extraction_prompt(document_type, custom_fields)
                
                response = await self._generate_content(prompt, image)
                result = self._parse_json_response(response)
                
                if result:
                    return self._convert_to_extracted_fields(result)
            
            # Fallback to mock extraction
            logger.info("Using mock field extraction")
            mock_data = await self._get_mock_extraction(document_type)
            
            # Convert to ExtractedField format
            extracted_fields = {}
            for field_name, field_data in mock_data.items():
                extracted_fields[field_name] = ExtractedField(
                    value=field_data.get('value', ''),
                    confidence=field_data.get('confidence', 0.5),
                    confidence_level=self._get_confidence_level(field_data.get('confidence', 0.5)),
                    location=None,
                    original_text=field_data.get('value', ''),
                    validation_errors=[]
                )
            
            return extracted_fields
            
        except Exception as e:
            logger.error(f"Field extraction failed: {e}")
            return {}
    
    def _get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Convert confidence score to confidence level."""
        if confidence >= 0.9:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.7:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    async def _get_mock_extraction(self, document_type: DocumentType) -> Dict[str, Any]:
        """Return mock extraction data for development."""
        if document_type == DocumentType.INVOICE:
            return {
                "vendor_name": {"value": "ACME Corporation", "confidence": 0.95},
                "invoice_number": {"value": "INV-2024-001", "confidence": 0.90},
                "invoice_date": {"value": "2024-01-15", "confidence": 0.92},
                "total_amount": {"value": "1,234.56", "confidence": 0.95},
                "currency": {"value": "USD", "confidence": 0.88},
                "vendor_address": {"value": "123 Business St, City, State 12345", "confidence": 0.85},
                "subtotal": {"value": "1,134.56", "confidence": 0.90},
                "tax_amount": {"value": "100.00", "confidence": 0.88}
            }
        elif document_type == DocumentType.RECEIPT:
            return {
                "merchant_name": {"value": "Coffee Shop", "confidence": 0.92},
                "transaction_date": {"value": "2024-01-15", "confidence": 0.90},
                "total_amount": {"value": "15.50", "confidence": 0.95},
                "payment_method": {"value": "Credit Card", "confidence": 0.85}
            }
        elif document_type == DocumentType.BUSINESS_CARD:
            return {
                "full_name": {"value": "John Smith", "confidence": 0.95},
                "company": {"value": "Tech Solutions Inc", "confidence": 0.90},
                "title": {"value": "Software Engineer", "confidence": 0.88},
                "email": {"value": "john.smith@techsolutions.com", "confidence": 0.92},
                "phone": {"value": "+1 (555) 123-4567", "confidence": 0.90}
            }
        else:
            return {
                "document_content": {"value": "Sample extracted content", "confidence": 0.75}
            }
    
    async def validate_extraction(
        self, 
        extracted_fields: Dict[str, ExtractedField],
        document_type: DocumentType
    ) -> Dict[str, ExtractedField]:
        """Validate and enhance extracted fields."""
        for field_name, field in extracted_fields.items():
            # Apply field-specific validation
            if 'date' in field_name.lower():
                field = await self._validate_date_field(field)
            elif any(keyword in field_name.lower() for keyword in ['amount', 'total', 'price']):
                field = await self._validate_amount_field(field)
            elif 'email' in field_name.lower():
                field = await self._validate_email_field(field)
            elif 'phone' in field_name.lower():
                field = await self._validate_phone_field(field)
            
            # Update confidence level based on validation
            field.confidence_level = self._get_confidence_level(field.confidence)
        
        return extracted_fields
    
    async def _validate_date_field(self, field: ExtractedField) -> ExtractedField:
        """Validate date field format."""
        import datetime
        
        if not field.value:
            return field
        
        try:
            # Try parsing common date formats
            date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%B %d, %Y']
            for fmt in date_formats:
                try:
                    datetime.datetime.strptime(str(field.value), fmt)
                    field.confidence = min(field.confidence + 0.05, 1.0)
                    break
                except ValueError:
                    continue
            else:
                field.validation_errors.append("Invalid date format")
                field.confidence = max(field.confidence - 0.1, 0.0)
        except Exception as e:
            field.validation_errors.append(f"Date validation error: {str(e)}")
            field.confidence = max(field.confidence - 0.1, 0.0)
        
        return field
    
    async def _validate_amount_field(self, field: ExtractedField) -> ExtractedField:
        """Validate amount field format."""
        if not field.value:
            return field
        
        try:
            # Extract numeric value from amount string
            amount_str = str(field.value).replace(',', '').replace('$', '').replace('€', '')
            amount_match = re.search(r'[\d.]+', amount_str)
            
            if amount_match:
                numeric_value = float(amount_match.group())
                if numeric_value >= 0:
                    field.confidence = min(field.confidence + 0.05, 1.0)
                else:
                    field.validation_errors.append("Negative amount detected")
            else:
                field.validation_errors.append("No numeric value found")
                field.confidence = max(field.confidence - 0.1, 0.0)
        except Exception as e:
            field.validation_errors.append(f"Amount validation error: {str(e)}")
            field.confidence = max(field.confidence - 0.1, 0.0)
        
        return field
    
    async def _validate_email_field(self, field: ExtractedField) -> ExtractedField:
        """Validate email field format."""
        if not field.value:
            return field
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, str(field.value)):
            field.confidence = min(field.confidence + 0.05, 1.0)
        else:
            field.validation_errors.append("Invalid email format")
            field.confidence = max(field.confidence - 0.1, 0.0)
        
        return field
    
    async def _validate_phone_field(self, field: ExtractedField) -> ExtractedField:
        """Validate phone field format."""
        if not field.value:
            return field
        
        # Basic phone validation
        digits_only = re.sub(r'\D', '', str(field.value))
        if len(digits_only) >= 10:
            field.confidence = min(field.confidence + 0.05, 1.0)
        else:
            field.validation_errors.append("Phone number too short")
            field.confidence = max(field.confidence - 0.05, 0.0)
        
        return field

    async def _prepare_image(self, image_data: bytes) -> Any:
        """Prepare image for Gemini API processing."""
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if too large (Gemini has size limits)
            max_size = (2048, 2048)
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Return PIL Image directly (Gemini API expects PIL Image, not bytes)
            return image
            
        except Exception as e:
            logger.error(f"Failed to prepare image: {e}")
            raise
    
    async def _generate_content(self, prompt: str, image_data: Any = None) -> str:
        """Generate content using Gemini API."""
        try:
            if not self.model:
                raise ValueError("Gemini model not initialized")
            
            if image_data:
                # For image + text input
                # Note: Actual implementation depends on google-generativeai API
                # This is a placeholder that would need to be adapted
                response = self.model.generate_content([prompt, image_data])  # type: ignore
            else:
                # For text-only input
                response = self.model.generate_content(prompt)  # type: ignore
            
            return response.text if hasattr(response, 'text') else str(response)
            
        except Exception as e:
            logger.error(f"Failed to generate content: {e}")
            raise
    
    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON response from Gemini API."""
        try:
            # Clean up response text
            response = response.strip()
            
            # Find JSON in response (sometimes wrapped in markdown)
            if '```json' in response:
                start = response.find('```json') + 7
                end = response.find('```', start)
                response = response[start:end].strip()
            elif '{' in response and '}' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                response = response[start:end]
            
            return json.loads(response)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response was: {response}")
            return None
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return None

    def _build_extraction_prompt(self, document_type: DocumentType, custom_fields: Optional[list] = None) -> str:
        """Build extraction prompt based on document type."""
        base_prompt = self.document_type_prompts.get(document_type, self.document_type_prompts[DocumentType.CUSTOM])
        
        if custom_fields:
            fields_list = ", ".join(custom_fields)
            base_prompt += f"\n\nAdditionally extract these custom fields: {fields_list}"
        
        base_prompt += """
        
        IMPORTANT: Return the response as valid JSON only, with each field having 'value' and 'confidence' properties.
        Example format:
        {
            "field_name": {"value": "extracted_value", "confidence": 0.95},
            "another_field": {"value": "another_value", "confidence": 0.87}
        }
        """
        
        return base_prompt
    
    def _convert_to_extracted_fields(self, result: Dict[str, Any]) -> Dict[str, ExtractedField]:
        """Convert API response to ExtractedField objects."""
        extracted_fields = {}
        
        for field_name, field_data in result.items():
            if isinstance(field_data, dict):
                value = field_data.get('value', '')
                confidence = float(field_data.get('confidence', 0.5))
            else:
                # Handle simple string values
                value = str(field_data)
                confidence = 0.7
            
            extracted_fields[field_name] = ExtractedField(
                value=value,
                confidence=confidence,
                confidence_level=self._get_confidence_level(confidence),
                location=None,
                original_text=value,
                validation_errors=[]
            )
        
        return extracted_fields

    async def _get_gemini_response_simple(self, image: Image.Image, prompt: str) -> str:
        """Get simple text response from Gemini API."""
        try:
            if self.use_real_api and self.model:
                # Use real Gemini API
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self.model.generate_content, [prompt, image]
                )
                return response.text
            else:
                # Mock response for development/testing
                return await self._get_mock_simple_response(prompt)
                
        except Exception as e:
            logger.error(f"Gemini simple response failed: {e}")
            return await self._get_mock_simple_response(prompt)
    
    async def _get_mock_simple_response(self, prompt: str) -> str:
        """Generate mock response for development."""
        if "document type" in prompt.lower():
            return "INVOICE|0.95"
        elif "extract" in prompt.lower():
            return '''
            {
              "vendor_name": {"value": "ACME Corporation", "confidence": 0.95, "original_text": "ACME Corporation"},
              "invoice_number": {"value": "INV-2025-001", "confidence": 0.92, "original_text": "INV-2025-001"},
              "total_amount": {"value": "$1,234.56", "confidence": 0.98, "original_text": "$1,234.56"},
              "invoice_date": {"value": "2025-06-18", "confidence": 0.90, "original_text": "18/06/2025"}
            }
            '''
        else:
            return "Mock response for: " + prompt[:50] + "..."
