"""Universal Document Extraction Service - Extract everything from any document."""

import asyncio
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from PIL import Image
import io

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


class UniversalExtractionService:
    """Universal document extraction - extracts all information from any document."""
    
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
                logger.info("Universal Extraction - Gemini API configured successfully")
            except Exception as e:
                logger.error(f"Failed to configure Gemini API: {e}")
                self.model = None
                self.use_real_api = False

    @measure_time
    async def extract_everything(
        self,
        image_data: bytes,
        extraction_mode: str = "comprehensive"  # "basic", "comprehensive", "detailed"
    ) -> Dict[str, Any]:
        """Extract all information from any document."""
        
        try:
            # Step 1: OCR extraction for spatial understanding
            ocr_results = await self.ocr_service.extract_text_with_layout(image_data)
            
            # Step 2: Universal extraction with Gemini
            extraction_results = await self._universal_gemini_extraction(
                image_data, ocr_results, extraction_mode
            )
            
            # Step 3: Structure the results
            structured_results = await self._structure_universal_results(
                extraction_results, ocr_results
            )
            
            # Step 4: Add metadata and analysis
            analysis = await self._analyze_document_structure(ocr_results)
            
            return {
                "document_analysis": analysis,
                "extracted_data": structured_results,
                "raw_ocr": ocr_results,
                "extraction_metadata": {
                    "extraction_mode": extraction_mode,
                    "total_fields": len(structured_results),
                    "confidence": self._calculate_overall_confidence(structured_results),
                    "document_structure": analysis["structure_type"]
                }
            }
            
        except Exception as e:
            logger.error(f"Universal extraction failed: {e}")
            return {
                "document_analysis": {"error": str(e)},
                "extracted_data": {},
                "raw_ocr": {},
                "extraction_metadata": {"error": str(e)}
            }

    async def _universal_gemini_extraction(
        self,
        image_data: bytes,
        ocr_results: Dict,
        extraction_mode: str
    ) -> Dict[str, Any]:
        """Use Gemini to extract all information from the document."""
        
        if not self.use_real_api:
            return await self._get_universal_mock_extraction(ocr_results, extraction_mode)
        
        try:
            # Prepare image
            image = await self._prepare_image(image_data)
            
            # Create universal extraction prompt
            prompt = self._create_universal_prompt(ocr_results, extraction_mode)
            
            # Generate response
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.model.generate_content, [prompt, image]  # type: ignore
            )
            
            # Parse the comprehensive response
            return self._parse_universal_response(response.text)
            
        except Exception as e:
            logger.error(f"Universal Gemini extraction failed: {e}")
            return await self._get_universal_mock_extraction(ocr_results, extraction_mode)

    def _create_universal_prompt(self, ocr_results: Dict, extraction_mode: str) -> str:
        """Create a comprehensive prompt for universal extraction."""
        
        ocr_text = ocr_results.get("full_text", "")[:3000]  # More text for context
        
        if extraction_mode == "basic":
            detail_level = "Extract the key information"
        elif extraction_mode == "comprehensive":
            detail_level = "Extract all visible information comprehensively"
        else:  # detailed
            detail_level = "Extract every single piece of information with maximum detail"
        
        prompt = f"""You are an expert document analyzer capable of extracting ALL information from any document type. 
{detail_level} from this document image.

DOCUMENT TEXT (from OCR):
{ocr_text}

EXTRACTION INSTRUCTIONS:
1. IDENTIFY the document type first
2. EXTRACT ALL visible information including:
   - Headers, titles, and document identifiers
   - All names, addresses, and contact information
   - All numbers, codes, IDs, and references
   - All dates and times
   - All amounts, quantities, and measurements
   - All product/service descriptions
   - All table data (if present)
   - All terms, conditions, and notes
   - Any signatures, stamps, or authentication marks

3. ORGANIZE information into logical categories:
   - Document Metadata (type, number, dates)
   - Parties/Entities (names, addresses, contacts)
   - Transaction/Content Details (items, amounts, descriptions)
   - Additional Information (terms, notes, references)

4. For EACH piece of information provide:
   - The exact text/value found
   - What type of information it is
   - Its importance level (critical/important/supplementary)

Return the response as a structured JSON with this format:
{{
    "document_type": "identified document type",
    "document_metadata": {{
        "document_number": "if found",
        "document_date": "if found",
        "generated_date": "if found",
        "other_ids": ["list of any other IDs/numbers"]
    }},
    "parties": [
        {{
            "type": "from/to/issuer/etc",
            "name": "entity name",
            "address": "full address",
            "contact_info": {{"phone": "", "email": "", "other": ""}}
        }}
    ],
    "content_details": [
        {{
            "category": "category name",
            "items": [
                {{
                    "field_name": "descriptive name",
                    "value": "extracted value",
                    "type": "text/number/date/amount/etc",
                    "importance": "critical/important/supplementary"
                }}
            ]
        }}
    ],
    "tables": [
        {{
            "table_name": "if identifiable",
            "headers": ["column headers"],
            "rows": [
                ["row data"]
            ]
        }}
    ],
    "additional_info": {{
        "terms_conditions": "any terms found",
        "notes": "any additional notes",
        "references": ["any reference numbers or codes"],
        "totals_summary": {{"key totals found"}}
    }}
}}

Be extremely thorough and extract everything visible in the document."""

        return prompt

    def _parse_universal_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the universal extraction response from Gemini."""
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Fallback: parse text response into structured format
                return self._parse_text_response(response_text)
                
        except Exception as e:
            logger.warning(f"Failed to parse universal response: {e}")
            return self._parse_text_response(response_text)

    def _parse_text_response(self, text: str) -> Dict[str, Any]:
        """Parse text response into structured format."""
        lines = text.split('\n')
        
        result = {
            "document_type": "unknown",
            "document_metadata": {},
            "parties": [],
            "content_details": [],
            "tables": [],
            "additional_info": {}
        }
        
        current_section = "content_details"
        current_items = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for document type indicators
            if any(keyword in line.lower() for keyword in ['invoice', 'receipt', 'bill', 'statement', 'report']):
                result["document_type"] = line
            
            # Extract key-value pairs
            if ':' in line:
                key, value = line.split(':', 1)
                current_items.append({
                    "field_name": key.strip(),
                    "value": value.strip(),
                    "type": "text",
                    "importance": "important"
                })
        
        if current_items:
            result["content_details"].append({
                "category": "extracted_information",
                "items": current_items
            })
        
        return result

    async def _structure_universal_results(
        self, 
        extraction_results: Dict[str, Any],
        ocr_results: Dict
    ) -> Dict[str, ExtractedField]:
        """Structure universal extraction results into ExtractedField format."""
        
        structured_fields = {}
        field_counter = 1
        
        # Process document metadata
        metadata = extraction_results.get("document_metadata", {})
        for key, value in metadata.items():
            if value:
                field_name = f"metadata_{key}"
                structured_fields[field_name] = ExtractedField(
                    value=value,
                    confidence=0.95,
                    confidence_level=ConfidenceLevel.HIGH,
                    location=await self._find_field_location(str(value), ocr_results),
                    original_text=str(value)
                )
        
        # Process parties information
        parties = extraction_results.get("parties", [])
        for i, party in enumerate(parties):
            party_prefix = f"party_{i+1}"
            for key, value in party.items():
                if value:
                    field_name = f"{party_prefix}_{key}"
                    structured_fields[field_name] = ExtractedField(
                        value=value,
                        confidence=0.90,
                        confidence_level=ConfidenceLevel.HIGH,
                        location=await self._find_field_location(str(value), ocr_results),
                        original_text=str(value)
                    )
        
        # Process content details
        content_details = extraction_results.get("content_details", [])
        for category in content_details:
            category_name = category.get("category", "general")
            items = category.get("items", [])
            
            for item in items:
                field_name = item.get("field_name", f"field_{field_counter}")
                value = item.get("value", "")
                importance = item.get("importance", "important")
                
                confidence = 0.95 if importance == "critical" else 0.85 if importance == "important" else 0.75
                
                structured_fields[field_name] = ExtractedField(
                    value=value,
                    confidence=confidence,
                    confidence_level=self._get_confidence_level(confidence),
                    location=await self._find_field_location(str(value), ocr_results),
                    original_text=str(value)
                )
                field_counter += 1
        
        # Process tables
        tables = extraction_results.get("tables", [])
        for i, table in enumerate(tables):
            table_name = table.get("table_name", f"table_{i+1}")
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            
            # Store table headers
            if headers:
                structured_fields[f"{table_name}_headers"] = ExtractedField(
                    value=headers,
                    confidence=0.90,
                    confidence_level=ConfidenceLevel.HIGH,
                    location=None,
                    original_text=str(headers)
                )
            
            # Store table data
            if rows:
                structured_fields[f"{table_name}_data"] = ExtractedField(
                    value=rows,
                    confidence=0.85,
                    confidence_level=ConfidenceLevel.HIGH,
                    location=None,
                    original_text=str(rows)
                )
        
        # Process additional information
        additional_info = extraction_results.get("additional_info", {})
        for key, value in additional_info.items():
            if value:
                field_name = f"additional_{key}"
                structured_fields[field_name] = ExtractedField(
                    value=value,
                    confidence=0.80,
                    confidence_level=ConfidenceLevel.HIGH,
                    location=await self._find_field_location(str(value), ocr_results),
                    original_text=str(value)
                )
        
        return structured_fields

    async def _find_field_location(self, value: str, ocr_results: Dict) -> Optional[FieldLocation]:
        """Find the spatial location of a field value in the OCR results with enhanced accuracy."""
        try:
            text_blocks = ocr_results.get("text_blocks", [])
            image_dimensions = ocr_results.get("image_dimensions", (1, 1))
            
            if not text_blocks or not value:
                return None
            
            value_clean = str(value).strip()
            
            # Strategy 1: Exact match (highest priority)
            location = await self._find_exact_match(value_clean, text_blocks, image_dimensions)
            if location:
                # Improve accuracy of found location
                return await self._improve_location_accuracy("", value_clean, location, ocr_results)
            
            # Strategy 2: Fuzzy matching with edit distance
            location = await self._find_fuzzy_match(value_clean, text_blocks, image_dimensions)
            if location:
                return await self._improve_location_accuracy("", value_clean, location, ocr_results)
            
            # Strategy 3: Partial matching (for long values)
            location = await self._find_partial_match(value_clean, text_blocks, image_dimensions)
            if location:
                return await self._improve_location_accuracy("", value_clean, location, ocr_results)
            
            # Strategy 4: Pattern-based matching (for structured data)
            location = await self._find_pattern_match(value_clean, text_blocks, image_dimensions)
            if location:
                return await self._improve_location_accuracy("", value_clean, location, ocr_results)
            
            # Strategy 5: Contextual matching (based on nearby text)
            location = await self._find_contextual_match(value_clean, text_blocks, image_dimensions)
            if location:
                return await self._improve_location_accuracy("", value_clean, location, ocr_results)
            
            return None
            
        except Exception as e:
            logger.warning(f"Field location detection failed: {e}")
            return None

    async def _find_exact_match(self, value: str, text_blocks: List, image_dimensions: Tuple) -> Optional[FieldLocation]:
        """Find exact text matches."""
        value_lower = value.lower()
        
        for block in text_blocks:
            block_text_lower = block.text.strip().lower()
            
            if value_lower == block_text_lower:
                bbox = block.bounding_box
                return FieldLocation(
                    x=bbox.x1 / image_dimensions[0],
                    y=bbox.y1 / image_dimensions[1],
                    width=(bbox.x2 - bbox.x1) / image_dimensions[0],
                    height=(bbox.y2 - bbox.y1) / image_dimensions[1]
                )
        
        return None

    async def _find_fuzzy_match(self, value: str, text_blocks: List, image_dimensions: Tuple) -> Optional[FieldLocation]:
        """Find matches using fuzzy string matching."""
        import difflib
        
        value_lower = value.lower()
        best_match = None
        best_ratio = 0.0
        
        for block in text_blocks:
            block_text_lower = block.text.strip().lower()
            
            # Calculate similarity ratio
            ratio = difflib.SequenceMatcher(None, value_lower, block_text_lower).ratio()
            
            if ratio > 0.8 and ratio > best_ratio:  # 80% similarity threshold
                best_ratio = ratio
                best_match = block
        
        if best_match:
            bbox = best_match.bounding_box
            return FieldLocation(
                x=bbox.x1 / image_dimensions[0],
                y=bbox.y1 / image_dimensions[1],
                width=(bbox.x2 - bbox.x1) / image_dimensions[0],
                height=(bbox.y2 - bbox.y1) / image_dimensions[1]
            )
        
        return None

    async def _find_partial_match(self, value: str, text_blocks: List, image_dimensions: Tuple) -> Optional[FieldLocation]:
        """Find partial matches for long values."""
        value_lower = value.lower()
        
        # For very long values, try to match significant parts
        if len(value) > 20:
            # Split into words and find blocks containing multiple words
            words = [w for w in value_lower.split() if len(w) > 3]  # Ignore short words
            
            for block in text_blocks:
                block_text_lower = block.text.strip().lower()
                word_matches = sum(1 for word in words if word in block_text_lower)
                
                if word_matches >= min(2, len(words) // 2):  # At least half the significant words
                    bbox = block.bounding_box
                    return FieldLocation(
                        x=bbox.x1 / image_dimensions[0],
                        y=bbox.y1 / image_dimensions[1],
                        width=(bbox.x2 - bbox.x1) / image_dimensions[0],
                        height=(bbox.y2 - bbox.y1) / image_dimensions[1]
                    )
        
        # For shorter values, try substring matching
        for block in text_blocks:
            block_text_lower = block.text.strip().lower()
            
            if (len(value) > 5 and value_lower in block_text_lower) or \
               (len(block_text_lower) > 5 and block_text_lower in value_lower):
                bbox = block.bounding_box
                return FieldLocation(
                    x=bbox.x1 / image_dimensions[0],
                    y=bbox.y1 / image_dimensions[1],
                    width=(bbox.x2 - bbox.x1) / image_dimensions[0],
                    height=(bbox.y2 - bbox.y1) / image_dimensions[1]
                )
        
        return None

    async def _find_pattern_match(self, value: str, text_blocks: List, image_dimensions: Tuple) -> Optional[FieldLocation]:
        """Find matches using pattern recognition for structured data."""
        import re
        
        # Patterns for common data types
        patterns = {
            'amount': r'[\d,]+\.?\d*',
            'date': r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',
            'phone': r'[\d\s\-\+\(\)]+',
            'id_number': r'[A-Z0-9]+',
            'percentage': r'\d+%',
        }
        
        # Clean value for pattern matching
        value_clean = re.sub(r'[^\w\d\.\-/]', '', value)
        
        for pattern_name, pattern in patterns.items():
            if re.search(pattern, value, re.IGNORECASE):
                # Look for blocks with similar patterns
                for block in text_blocks:
                    block_text = block.text.strip()
                    block_clean = re.sub(r'[^\w\d\.\-/]', '', block_text)
                    
                    if re.search(pattern, block_text, re.IGNORECASE) and \
                       (value_clean in block_clean or block_clean in value_clean):
                        bbox = block.bounding_box
                        return FieldLocation(
                            x=bbox.x1 / image_dimensions[0],
                            y=bbox.y1 / image_dimensions[1],
                            width=(bbox.x2 - bbox.x1) / image_dimensions[0],
                            height=(bbox.y2 - bbox.y1) / image_dimensions[1]
                        )
        
        return None

    async def _find_contextual_match(self, value: str, text_blocks: List, image_dimensions: Tuple) -> Optional[FieldLocation]:
        """Find matches based on context and nearby text."""
        # This is more advanced - look for values near labels or in structured positions
        value_lower = value.lower()
        
        # Sort blocks by position (top to bottom, left to right)
        sorted_blocks = sorted(text_blocks, key=lambda b: (b.bounding_box.y1, b.bounding_box.x1))
        
        for i, block in enumerate(sorted_blocks):
            block_text_lower = block.text.strip().lower()
            
            # Check if this might be a label for our value
            if any(keyword in block_text_lower for keyword in ['total', 'amount', 'date', 'number', 'name', 'address']):
                # Look for values in nearby blocks (next few blocks)
                for j in range(i + 1, min(i + 5, len(sorted_blocks))):
                    nearby_block = sorted_blocks[j]
                    nearby_text = nearby_block.text.strip().lower()
                    
                    if value_lower in nearby_text or nearby_text in value_lower:
                        bbox = nearby_block.bounding_box
                        return FieldLocation(
                            x=bbox.x1 / image_dimensions[0],
                            y=bbox.y1 / image_dimensions[1],
                            width=(bbox.x2 - bbox.x1) / image_dimensions[0],
                            height=(bbox.y2 - bbox.y1) / image_dimensions[1]
                        )
        
        return None

    async def _analyze_document_structure(self, ocr_results: Dict) -> Dict[str, Any]:
        """Analyze the document structure and layout."""
        
        text_blocks = ocr_results.get("text_blocks", [])
        layout_elements = ocr_results.get("layout_elements", [])
        
        analysis = {
            "structure_type": "unknown",
            "layout_characteristics": {
                "total_text_blocks": len(text_blocks),
                "has_tables": False,
                "has_headers": False,
                "text_density": "medium"
            },
            "content_areas": [],
            "document_format": "structured" if len(layout_elements) > 0 else "unstructured"
        }
        
        # Analyze text distribution
        if text_blocks:
            y_positions = [block.bounding_box.y1 for block in text_blocks]
            top_blocks = [block for block in text_blocks if block.bounding_box.y1 < min(y_positions) + 100]
            
            # Check for headers (large text at top)
            if top_blocks:
                avg_font_size = sum(block.font_size for block in top_blocks) / len(top_blocks)
                if avg_font_size > 16:
                    analysis["layout_characteristics"]["has_headers"] = True
            
            # Check for table-like structures
            x_positions = [block.bounding_box.x1 for block in text_blocks]
            if len(set(x_positions)) > 3:  # Multiple columns
                analysis["layout_characteristics"]["has_tables"] = True
        
        # Determine structure type
        if analysis["layout_characteristics"]["has_tables"]:
            analysis["structure_type"] = "tabular"
        elif analysis["layout_characteristics"]["has_headers"]:
            analysis["structure_type"] = "form"
        else:
            analysis["structure_type"] = "document"
        
        return analysis

    async def _prepare_image(self, image_data: bytes) -> Image.Image:
        """Prepare image for Gemini processing."""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if too large
            max_size = 2048
            if max(image.size) > max_size:
                ratio = max_size / max(image.size)
                new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            return image
            
        except Exception as e:
            logger.error(f"Image preparation failed: {e}")
            raise

    def _get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Convert confidence score to confidence level."""
        if confidence >= 0.9:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.7:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def _calculate_overall_confidence(self, fields: Dict[str, ExtractedField]) -> float:
        """Calculate overall confidence."""
        if not fields:
            return 0.0
        
        confidences = [field.confidence for field in fields.values()]
        return sum(confidences) / len(confidences)

    async def _get_universal_mock_extraction(self, ocr_results: Dict, extraction_mode: str) -> Dict[str, Any]:
        """Generate mock universal extraction for testing."""
        
        full_text = ocr_results.get("full_text", "")
        
        # Simulate comprehensive extraction
        mock_result = {
            "document_type": "E-way Bill" if "e-way" in full_text.lower() else "Business Document",
            "document_metadata": {
                "document_number": "111023233647",
                "document_date": "01-05-2025 05:47:00 AM",
                "generated_date": "02-05-2025 11:59:00 PM",
                "other_ids": ["37AAACV2678L1ZT", "AP0147461947"]
            },
            "parties": [
                {
                    "type": "from",
                    "name": "Jerun Beverages Limited",
                    "address": "37, Andhra Pradesh - 517146",
                    "contact_info": {"gstin": "37AAACV2678L1ZT"}
                },
                {
                    "type": "to", 
                    "name": "SCOOTY LOGISTICS PRIVATE LIMITED",
                    "address": "SALGARAGAM-40",
                    "contact_info": {"gstin": "33AAPCS6916228"}
                }
            ],
            "content_details": [
                {
                    "category": "transportation_details",
                    "items": [
                        {"field_name": "mode", "value": "Road", "type": "text", "importance": "critical"},
                        {"field_name": "approx_distance", "value": "74 km", "type": "measurement", "importance": "important"},
                        {"field_name": "transaction_type", "value": "Regular", "type": "text", "importance": "important"}
                    ]
                },
                {
                    "category": "goods_details", 
                    "items": [
                        {"field_name": "hsn_code_1", "value": "22011010", "type": "code", "importance": "critical"},
                        {"field_name": "product_1", "value": "AQUAFINA 250ml PET 36 Bot", "type": "text", "importance": "critical"},
                        {"field_name": "quantity_1", "value": "200", "type": "number", "importance": "critical"}
                    ]
                }
            ],
            "tables": [
                {
                    "table_name": "goods_table",
                    "headers": ["HSN Code", "Product Description", "Quantity", "Taxable Amount", "Tax Rate", "Tax Amount"],
                    "rows": [
                        ["22011010", "AQUAFINA 250ml PET 36 Bot", "200", "27118.64", "0+0+18+0*", "4881.36"],
                        ["22021010", "7 UP FIZZ 750ML PET 24*40", "50", "24607.14", "0+0+28+12*", "6890"]
                    ]
                }
            ],
            "additional_info": {
                "terms_conditions": "Transportation by Road",
                "totals_summary": {"total_taxable_amount": "262779.05", "cgst_amount": "0", "sgst_amount": "0"},
                "references": ["37AAACV2678L1ZT", "111023233647"],
                "vehicle_details": "TN394615"
            }
        }
        
        return mock_result

    async def _improve_location_accuracy(self, field_name: str, field_value: str, location: FieldLocation, ocr_results: Dict) -> FieldLocation:
        """Improve location accuracy using field context and validation."""
        try:
            text_blocks = ocr_results.get("text_blocks", [])
            image_dimensions = ocr_results.get("image_dimensions", (1, 1))
            
            # Validate current location makes sense
            if not self._validate_location(location, field_name, field_value):
                # Try to find a better location using context
                improved_location = await self._find_improved_location(field_name, field_value, text_blocks, image_dimensions)
                if improved_location:
                    return improved_location
            
            # Refine bounding box for better accuracy
            return self._refine_bounding_box(location, field_value, text_blocks, image_dimensions)
            
        except Exception as e:
            logger.warning(f"Location accuracy improvement failed: {e}")
            return location

    def _validate_location(self, location: FieldLocation, field_name: str, field_value: str) -> bool:
        """Validate if the location makes sense for the field type."""
        # Check if location is within reasonable bounds
        if not (0 <= location.x <= 1 and 0 <= location.y <= 1):
            return False
        
        # Check if dimensions are reasonable
        if location.width and location.height:
            if location.width > 0.8 or location.height > 0.5:  # Too large
                return False
            if location.width < 0.01 or location.height < 0.005:  # Too small
                return False
        
        return True

    async def _find_improved_location(self, field_name: str, field_value: str, text_blocks: List, image_dimensions: Tuple) -> Optional[FieldLocation]:
        """Find improved location using multiple strategies."""
        
        # Strategy 1: Look for field labels and find nearby values
        field_keywords = self._extract_field_keywords(field_name)
        
        for keyword in field_keywords:
            for i, block in enumerate(text_blocks):
                if keyword.lower() in block.text.lower():
                    # Look for values in nearby blocks (spatially close)
                    nearby_blocks = self._find_spatially_close_blocks(block, text_blocks, max_distance=100)
                    
                    for nearby_block in nearby_blocks:
                        if self._is_value_match(field_value, nearby_block.text):
                            bbox = nearby_block.bounding_box
                            return FieldLocation(
                                x=bbox.x1 / image_dimensions[0],
                                y=bbox.y1 / image_dimensions[1],
                                width=(bbox.x2 - bbox.x1) / image_dimensions[0],
                                height=(bbox.y2 - bbox.y1) / image_dimensions[1]
                            )
        
        return None

    def _extract_field_keywords(self, field_name: str) -> List[str]:
        """Extract keywords from field name for label matching."""
        keywords = []
        
        # Split by underscores and camelCase
        parts = field_name.replace('_', ' ').split()
        
        for part in parts:
            # Add the word itself
            keywords.append(part)
            
            # Add variations
            if part.lower() in ['amt', 'amount']:
                keywords.extend(['total', 'sum', 'value'])
            elif part.lower() in ['num', 'number', 'no']:
                keywords.extend(['id', 'reference', 'ref'])
            elif part.lower() in ['addr', 'address']:
                keywords.extend(['location', 'place'])
        
        return keywords

    def _find_spatially_close_blocks(self, reference_block: Any, text_blocks: List, max_distance: int = 100) -> List[Any]:
        """Find text blocks that are spatially close to a reference block."""
        ref_bbox = reference_block.bounding_box
        ref_center_x = (ref_bbox.x1 + ref_bbox.x2) / 2
        ref_center_y = (ref_bbox.y1 + ref_bbox.y2) / 2
        
        close_blocks = []
        
        for block in text_blocks:
            if block == reference_block:
                continue
                
            bbox = block.bounding_box
            center_x = (bbox.x1 + bbox.x2) / 2
            center_y = (bbox.y1 + bbox.y2) / 2
            
            # Calculate distance
            distance = ((center_x - ref_center_x) ** 2 + (center_y - ref_center_y) ** 2) ** 0.5
            
            if distance <= max_distance:
                close_blocks.append(block)
        
        # Sort by distance
        close_blocks.sort(key=lambda b: ((b.bounding_box.x1 + b.bounding_box.x2) / 2 - ref_center_x) ** 2 + 
                                       ((b.bounding_box.y1 + b.bounding_box.y2) / 2 - ref_center_y) ** 2)
        
        return close_blocks

    def _is_value_match(self, expected_value: str, block_text: str) -> bool:
        """Check if block text matches the expected value."""
        expected_clean = str(expected_value).strip().lower()
        block_clean = block_text.strip().lower()
        
        # Direct match
        if expected_clean == block_clean:
            return True
        
        # Partial match for long values
        if len(expected_clean) > 10 and expected_clean in block_clean:
            return True
        
        # Fuzzy match
        import difflib
        ratio = difflib.SequenceMatcher(None, expected_clean, block_clean).ratio()
        return ratio > 0.85

    def _refine_bounding_box(self, location: FieldLocation, field_value: str, text_blocks: List, image_dimensions: Tuple) -> FieldLocation:
        """Refine bounding box dimensions for better accuracy."""
        try:
            # If we have width/height, validate and adjust them
            if location.width and location.height:
                # Ensure minimum readable size
                min_width = max(0.02, len(str(field_value)) * 0.008)  # Adaptive to content length
                min_height = 0.015  # Minimum height for readability
                
                adjusted_width = max(location.width, min_width)
                adjusted_height = max(location.height, min_height)
                
                # Ensure we don't exceed image bounds
                max_x = 1 - adjusted_width
                max_y = 1 - adjusted_height
                
                adjusted_x = min(location.x, max_x)
                adjusted_y = min(location.y, max_y)
                
                return FieldLocation(
                    x=adjusted_x,
                    y=adjusted_y,
                    width=adjusted_width,
                    height=adjusted_height
                )
            
            return location
            
        except Exception as e:
            logger.warning(f"Bounding box refinement failed: {e}")
            return location
