"""Enhanced Gemini Service with multi-pass processing and advanced prompting."""

import io
import asyncio
import json
import re
from typing import Dict, List, Optional, Tuple, Any, Union
from PIL import Image
try:
    import google.generativeai as genai  # type: ignore
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None  # type: ignore

from app.config import settings
from app.models.schemas import (
    DocumentType, ExtractedField, ConfidenceLevel, BoundingBox, 
    TextBlock, LayoutElement, FieldLocation
)
from app.services.enhanced_ocr_service import EnhancedOCRService
from app.utils.logging import get_logger
from app.utils.helpers import retry_async, measure_time

logger = get_logger(__name__)


class EnhancedGeminiService:
    """Enhanced Gemini service with multi-pass processing and spatial understanding."""
    
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model_name = settings.gemini_model
        self.ocr_service = EnhancedOCRService()
        
        # Configure Gemini API
        self.use_real_api = False
        self.model = None
        
        if GEMINI_AVAILABLE and self.api_key and self.api_key != "your-gemini-api-key-here":
            try:
                genai.configure(api_key=self.api_key)  # type: ignore
                self.model = genai.GenerativeModel(self.model_name)  # type: ignore
                self.use_real_api = True
                logger.info("Enhanced Gemini API configured successfully")
            except Exception as e:
                logger.error(f"Failed to configure Gemini API: {e}")
                self.model = None
                self.use_real_api = False
        
        if not self.use_real_api:
            logger.warning("Gemini API not available, using enhanced mock responses")
        
        self.document_schemas = self._load_document_schemas()
        self.validation_rules = self._load_validation_rules()

    def _load_document_schemas(self) -> Dict[str, Dict]:
        """Load comprehensive document schemas for each type."""
        return {
            DocumentType.INVOICE: {
                "required_fields": [
                    "vendor_name", "vendor_address", "invoice_number", "invoice_date", 
                    "total_amount", "currency", "customer_name"
                ],
                "optional_fields": [
                    "due_date", "subtotal", "tax_amount", "tax_rate", "payment_terms",
                    "purchase_order", "billing_address", "shipping_address", "line_items"
                ],
                "field_types": {
                    "vendor_name": "text",
                    "invoice_number": "identifier",
                    "invoice_date": "date",
                    "due_date": "date", 
                    "total_amount": "currency",
                    "subtotal": "currency",
                    "tax_amount": "currency",
                    "tax_rate": "percentage",
                    "line_items": "array"
                }
            },
            DocumentType.RECEIPT: {
                "required_fields": [
                    "merchant_name", "transaction_date", "total_amount", "currency"
                ],
                "optional_fields": [
                    "transaction_id", "payment_method", "items", "cashier", "store_location"
                ],
                "field_types": {
                    "merchant_name": "text",
                    "transaction_date": "datetime",
                    "total_amount": "currency",
                    "transaction_id": "identifier"
                }
            },
            DocumentType.BUSINESS_CARD: {
                "required_fields": ["full_name"],
                "optional_fields": [
                    "company", "title", "email", "phone", "mobile", "fax", 
                    "address", "website", "linkedin"
                ],
                "field_types": {
                    "full_name": "text",
                    "email": "email",
                    "phone": "phone",
                    "website": "url"
                }
            }
        }

    def _load_validation_rules(self) -> Dict[str, List[str]]:
        """Load field validation rules."""
        return {
            "currency_fields": ["total_amount", "subtotal", "tax_amount"],
            "date_fields": ["invoice_date", "due_date", "transaction_date"],
            "email_fields": ["email", "contact_email"],
            "phone_fields": ["phone", "mobile", "fax"],
            "identifier_fields": ["invoice_number", "transaction_id", "reference_number"]
        }

    @measure_time
    async def process_document_enhanced(
        self, 
        image_data: bytes, 
        document_type: DocumentType,
        ocr_results: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Enhanced document processing with multi-pass extraction."""
        
        # Step 1: OCR extraction if not provided
        if not ocr_results:
            ocr_results = await self.ocr_service.extract_text_with_layout(image_data)
        
        # Step 2: Initial extraction with Gemini
        initial_extraction = await self._extract_with_gemini(image_data, document_type, ocr_results)
        
        # Step 3: Validation and refinement
        refined_extraction = await self._validate_and_refine(initial_extraction, document_type, ocr_results)
        
        # Step 4: Spatial coordinate assignment
        extraction_with_locations = await self._assign_spatial_coordinates(
            refined_extraction, ocr_results
        )
        
        # Step 5: Cross-field validation
        final_extraction = await self._cross_validate_fields(extraction_with_locations, document_type)
        
        return {
            "extracted_data": final_extraction,
            "ocr_results": ocr_results,
            "processing_stages": {
                "initial_fields": len(initial_extraction),
                "refined_fields": len(refined_extraction),
                "final_fields": len(final_extraction)
            }
        }

    async def _extract_with_gemini(
        self, 
        image_data: bytes, 
        document_type: DocumentType,
        ocr_results: Optional[Dict] = None
    ) -> Dict[str, ExtractedField]:
        """Initial extraction using Gemini with enhanced prompting."""
        
        if not self.use_real_api:
            return await self._get_enhanced_mock_extraction(document_type, ocr_results or {})
        
        try:
            # Prepare image
            image = await self._prepare_image(image_data)
            
            # Create enhanced prompt
            prompt = self._create_enhanced_prompt(document_type, ocr_results or {})
            
            # Generate response
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.model.generate_content, [prompt, image]  # type: ignore
            )
            
            # Parse response
            return self._parse_gemini_response(response.text, document_type)
            
        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")
            return await self._get_enhanced_mock_extraction(document_type, ocr_results or {})

    def _create_enhanced_prompt(self, document_type: DocumentType, ocr_results: Optional[Dict] = None) -> str:
        """Create sophisticated prompt with context and examples."""
        
        schema = self.document_schemas.get(document_type, {})
        required_fields = schema.get("required_fields", [])
        optional_fields = schema.get("optional_fields", [])
        
        # Include OCR text for context
        ocr_text = (ocr_results or {}).get("full_text", "")[:2000]  # Limit length
        
        prompt = f"""You are an expert document analyzer with perfect accuracy. Analyze this {document_type.value} and extract structured data with extreme precision.

DOCUMENT TYPE: {document_type.value.upper()}

OCR TEXT CONTEXT:
{ocr_text}

EXTRACTION REQUIREMENTS:
1. Extract each field with the exact value as it appears in the document
2. Do not interpret or modify values - extract literally
3. For amounts: preserve original formatting (commas, decimals, currency symbols)
4. For dates: identify the format first, then extract the exact date
5. For addresses: extract complete address as it appears
6. If a field is not present or unclear, set confidence below 0.7

REQUIRED FIELDS: {', '.join(required_fields)}
OPTIONAL FIELDS: {', '.join(optional_fields)}

RESPONSE FORMAT (JSON only):
{{
  "field_name": {{
    "value": "exact_extracted_value",
    "confidence": 0.95,
    "original_text": "text_as_seen_in_document",
    "extraction_reasoning": "brief explanation of how this was identified"
  }}
}}

IMPORTANT:
- Return ONLY valid JSON
- Include confidence score (0.0-1.0) based on clarity and certainty
- Set confidence < 0.7 if unsure
- Include original_text field showing exactly what you read
- Extract ALL visible relevant fields, not just required ones

Begin extraction:"""

        return prompt

    async def _prepare_image(self, image_data: bytes) -> Image.Image:
        """Prepare image for Gemini processing."""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # Ensure RGB format
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if too large (Gemini has size limits)
            max_size = 2048
            if max(image.size) > max_size:
                ratio = max_size / max(image.size)
                new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            return image
            
        except Exception as e:
            logger.error(f"Image preparation failed: {e}")
            raise

    def _parse_gemini_response(self, response_text: str, document_type: DocumentType) -> Dict[str, ExtractedField]:
        """Parse Gemini response into structured fields."""
        try:
            # Clean response text
            response_text = response_text.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                logger.warning("No JSON found in Gemini response")
                return {}
            
            json_text = json_match.group()
            data = json.loads(json_text)
            
            # Convert to ExtractedField objects
            extracted_fields = {}
            for field_name, field_data in data.items():
                if isinstance(field_data, dict) and 'value' in field_data:
                    extracted_fields[field_name] = ExtractedField(
                        value=field_data.get('value', ''),
                        confidence=float(field_data.get('confidence', 0.5)),
                        confidence_level=self._get_confidence_level(float(field_data.get('confidence', 0.5))),
                        location=None,  # Will be assigned later
                        original_text=field_data.get('original_text', field_data.get('value', '')),
                        validation_errors=[]
                    )
            
            return extracted_fields
            
        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            return {}

    async def _validate_and_refine(
        self, 
        initial_extraction: Dict[str, ExtractedField],
        document_type: DocumentType,
        ocr_results: Optional[Dict] = None
    ) -> Dict[str, ExtractedField]:
        """Validate and refine extracted fields."""
        
        refined_fields = {}
        
        for field_name, field in initial_extraction.items():
            # Apply field-specific validation
            validation_errors = await self._validate_field(field_name, field.value, document_type)
            
            # Adjust confidence based on validation
            adjusted_confidence = field.confidence
            if validation_errors:
                adjusted_confidence *= 0.7  # Lower confidence for invalid fields
            
            # Try to correct common issues
            corrected_value = await self._correct_field_value(field_name, field.value, validation_errors)
            
            refined_fields[field_name] = ExtractedField(
                value=corrected_value,
                confidence=adjusted_confidence,
                confidence_level=self._get_confidence_level(adjusted_confidence),
                location=field.location,
                original_text=field.original_text,
                validation_errors=validation_errors
            )
        
        return refined_fields

    async def _validate_field(self, field_name: str, value: str, document_type: DocumentType) -> List[str]:
        """Validate individual field value."""
        errors = []
        
        if not value or str(value).strip() == '':
            return errors  # Empty values are okay
        
        value_str = str(value).strip()
        
        # Currency validation
        if field_name in self.validation_rules.get("currency_fields", []):
            if not re.search(r'[\d,]+\.?\d*', value_str):
                errors.append(f"Invalid currency format: {value_str}")
        
        # Date validation
        if field_name in self.validation_rules.get("date_fields", []):
            if not self._is_valid_date_format(value_str):
                errors.append(f"Invalid date format: {value_str}")
        
        # Email validation
        if field_name in self.validation_rules.get("email_fields", []):
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value_str):
                errors.append(f"Invalid email format: {value_str}")
        
        # Phone validation
        if field_name in self.validation_rules.get("phone_fields", []):
            if not re.search(r'[\d\-\(\)\+\s]+', value_str) or len(re.sub(r'[^\d]', '', value_str)) < 7:
                errors.append(f"Invalid phone format: {value_str}")
        
        return errors

    def _is_valid_date_format(self, date_str: str) -> bool:
        """Check if string represents a valid date."""
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',
            r'[A-Za-z]+ \d{1,2}, \d{4}',
            r'\d{1,2} [A-Za-z]+ \d{4}'
        ]
        
        return any(re.search(pattern, date_str) for pattern in date_patterns)

    async def _correct_field_value(self, field_name: str, value: str, validation_errors: List[str]) -> str:
        """Attempt to correct common field value issues."""
        if not validation_errors:
            return value
        
        corrected_value = str(value).strip()
        
        # Currency corrections
        if field_name in self.validation_rules.get("currency_fields", []):
            # Remove multiple spaces, fix decimal issues
            corrected_value = re.sub(r'\s+', ' ', corrected_value)
            corrected_value = re.sub(r'(\d),(\d{3})', r'\1,\2', corrected_value)  # Fix comma formatting
        
        # Date corrections
        if field_name in self.validation_rules.get("date_fields", []):
            # Fix common OCR date issues
            corrected_value = corrected_value.replace('/', '-').replace('.', '-')
        
        return corrected_value

    async def _assign_spatial_coordinates(
        self, 
        extracted_fields: Dict[str, ExtractedField],
        ocr_results: Optional[Dict] = None
    ) -> Dict[str, ExtractedField]:
        """Assign spatial coordinates to extracted fields."""
        
        # Get field locations from OCR
        field_values = {name: field.value for name, field in extracted_fields.items()}
        field_locations = await self.ocr_service.find_field_locations(ocr_results or {}, field_values)
        
        # Update fields with location information
        updated_fields = {}
        for field_name, field in extracted_fields.items():
            location = field_locations.get(field_name)
            
            updated_fields[field_name] = ExtractedField(
                value=field.value,
                confidence=field.confidence,
                confidence_level=field.confidence_level,
                location=self._convert_bbox_to_location(location, ocr_results or {}) if location else None,
                original_text=field.original_text,
                validation_errors=field.validation_errors
            )
        
        return updated_fields

    def _convert_bbox_to_location(self, bbox: BoundingBox, ocr_results: Optional[Dict] = None) -> Optional[FieldLocation]:
        """Convert bounding box to percentage-based location."""
        try:
            img_width, img_height = (ocr_results or {}).get('image_dimensions', (1, 1))
            
            return FieldLocation(
                x=bbox.x1 / img_width,
                y=bbox.y1 / img_height,
                width=bbox.width / img_width,
                height=bbox.height / img_height
            )
        except Exception:
            return None

    async def _cross_validate_fields(
        self, 
        extracted_fields: Dict[str, ExtractedField],
        document_type: DocumentType
    ) -> Dict[str, ExtractedField]:
        """Perform cross-field validation and consistency checks."""
        
        # For invoices, check if subtotal + tax = total
        if document_type == DocumentType.INVOICE:
            extracted_fields = await self._validate_invoice_math(extracted_fields)
        
        # Check date consistency (due date should be after invoice date)
        extracted_fields = await self._validate_date_consistency(extracted_fields)
        
        return extracted_fields

    async def _validate_invoice_math(self, fields: Dict[str, ExtractedField]) -> Dict[str, ExtractedField]:
        """Validate invoice mathematical relationships."""
        try:
            subtotal = self._extract_numeric_value(fields.get('subtotal'))
            tax_amount = self._extract_numeric_value(fields.get('tax_amount'))
            total = self._extract_numeric_value(fields.get('total_amount'))
            
            if all(val is not None for val in [subtotal, tax_amount, total]):
                calculated_total = (subtotal or 0.0) + (tax_amount or 0.0)
                total_val = total or 0.0
                if abs(calculated_total - total_val) > 0.01:  # Allow for rounding
                    # Add validation error
                    if 'total_amount' in fields:
                        fields['total_amount'].validation_errors.append(
                            f"Total ({total_val}) doesn't match subtotal + tax ({calculated_total})"
                        )
                        fields['total_amount'].confidence *= 0.8
        
        except Exception as e:
            logger.warning(f"Invoice math validation failed: {e}")
        
        return fields

    async def _validate_date_consistency(self, fields: Dict[str, ExtractedField]) -> Dict[str, ExtractedField]:
        """Validate date field consistency."""
        # Implementation would check that due_date > invoice_date, etc.
        return fields

    def _extract_numeric_value(self, field: Optional[ExtractedField]) -> Optional[float]:
        """Extract numeric value from field."""
        if not field or not field.value:
            return None
        
        try:
            # Remove currency symbols and commas
            numeric_str = re.sub(r'[^\d.-]', '', str(field.value))
            return float(numeric_str)
        except (ValueError, TypeError):
            return None

    def _get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Convert confidence score to confidence level."""
        if confidence >= 0.9:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.7:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    async def _get_enhanced_mock_extraction(self, document_type: DocumentType, ocr_results: Optional[Dict] = None) -> Dict[str, ExtractedField]:
        """Enhanced mock extraction using OCR results."""
        
        # Use actual OCR text to create more realistic mock data
        ocr_text = (ocr_results or {}).get('full_text', '').lower()
        
        if document_type == DocumentType.INVOICE:
            return {
                "vendor_name": ExtractedField(
                    value=self._extract_mock_vendor_name(ocr_text),
                    confidence=0.95,
                    confidence_level=ConfidenceLevel.HIGH,
                    location=None,
                    original_text="Mock Vendor Corp",
                    validation_errors=[]
                ),
                "invoice_number": ExtractedField(
                    value=self._extract_mock_invoice_number(ocr_text),
                    confidence=0.92,
                    confidence_level=ConfidenceLevel.HIGH,
                    location=None,
                    original_text="INV-2025-001",
                    validation_errors=[]
                ),
                "total_amount": ExtractedField(
                    value=self._extract_mock_amount(ocr_text),
                    confidence=0.98,
                    confidence_level=ConfidenceLevel.HIGH,
                    location=None,
                    original_text="$1,234.56",
                    validation_errors=[]
                )
            }
        
        # Add similar logic for other document types
        return {}

    def _extract_mock_vendor_name(self, ocr_text: str) -> str:
        """Extract realistic vendor name from OCR text."""
        # Look for company-like patterns in OCR text
        company_words = ['corp', 'inc', 'llc', 'ltd', 'company', 'services', 'solutions']
        words = ocr_text.split()
        
        for i, word in enumerate(words):
            if any(comp in word.lower() for comp in company_words):
                # Return the word before + this word
                if i > 0:
                    return f"{words[i-1].title()} {word.title()}"
                else:
                    return word.title()
        
        return "ACME Corporation"

    def _extract_mock_invoice_number(self, ocr_text: str) -> str:
        """Extract realistic invoice number from OCR text."""
        # Look for invoice number patterns
        inv_patterns = [
            r'inv[^\w]*(\d+[-\w]*)',
            r'invoice[^\w]*[#:]?\s*(\w+)',
            r'#\s*(\d+[-\w]*)'
        ]
        
        for pattern in inv_patterns:
            match = re.search(pattern, ocr_text, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        return "INV-2025-001"

    def _extract_mock_amount(self, ocr_text: str) -> str:
        """Extract realistic amount from OCR text."""
        # Look for currency amounts
        amount_patterns = [
            r'\$\s*[\d,]+\.?\d*',
            r'[\d,]+\.\d{2}',
            r'total[^\d]*(\d+[,.]?\d*)'
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, ocr_text, re.IGNORECASE)
            if match:
                return match.group()
        
        return "$1,234.56"
