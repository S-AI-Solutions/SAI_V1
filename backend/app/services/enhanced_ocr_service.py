"""Enhanced OCR Service with spatial understanding and layout detection."""

import io
import asyncio
from typing import Dict, List, Optional, Tuple, Any, Union
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
import cv2
import numpy as np
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    easyocr = None

from app.models.schemas import BoundingBox, TextBlock, LayoutElement
from app.utils.logging import get_logger
from app.utils.helpers import measure_time

logger = get_logger(__name__)


class EnhancedOCRService:
    """Advanced OCR service with layout understanding and spatial coordinates."""
    
    def __init__(self):
        self.tesseract_available = TESSERACT_AVAILABLE
        self.easyocr_available = EASYOCR_AVAILABLE
        self.easyocr_reader = None
        
        # Initialize EasyOCR reader if available
        if self.easyocr_available:
            try:
                self.easyocr_reader = easyocr.Reader(['en'], gpu=False)  # type: ignore
                logger.info("EasyOCR initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize EasyOCR: {e}")
                self.easyocr_available = False
        
        if not self.tesseract_available and not self.easyocr_available:
            logger.warning("No OCR engines available. Install pytesseract or easyocr for enhanced functionality")

    @measure_time
    async def extract_text_with_layout(self, image_data: bytes) -> Dict[str, Any]:
        """Extract text with spatial coordinates and layout information."""
        try:
            # Convert to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Enhance image quality
            enhanced_image = await self._enhance_for_ocr(image)
            
            # Extract text with multiple engines
            results = {
                'text_blocks': [],
                'layout_elements': [],
                'full_text': '',
                'confidence': 0.0,
                'image_dimensions': image.size
            }
            
            # Use best available OCR engine
            if self.easyocr_available:
                results = await self._extract_with_easyocr(enhanced_image, results)
            elif self.tesseract_available:
                results = await self._extract_with_tesseract(enhanced_image, results)
            else:
                # Fallback to basic text extraction
                results['full_text'] = "OCR not available - install pytesseract or easyocr"
                results['confidence'] = 0.1
            
            # Detect layout structure
            results['layout_elements'] = await self._detect_layout_structure(enhanced_image, results['text_blocks'])
            
            return results
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return {
                'text_blocks': [],
                'layout_elements': [],
                'full_text': '',
                'confidence': 0.0,
                'error': str(e)
            }

    async def _enhance_for_ocr(self, image: Image.Image) -> Image.Image:
        """Enhanced image preprocessing for better OCR accuracy."""
        try:
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert to OpenCV format for advanced processing
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Apply adaptive thresholding for better text contrast
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Remove noise
            denoised = cv2.bilateralFilter(gray, 9, 75, 75)
            
            # Enhance contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(denoised)
            
            # Convert back to PIL
            enhanced_pil = Image.fromarray(enhanced)
            
            # Additional PIL enhancements
            enhancer = ImageEnhance.Sharpness(enhanced_pil)
            enhanced_pil = enhancer.enhance(1.2)
            
            enhancer = ImageEnhance.Contrast(enhanced_pil)
            enhanced_pil = enhancer.enhance(1.1)
            
            return enhanced_pil.convert('RGB')
            
        except Exception as e:
            logger.warning(f"Image enhancement failed: {e}")
            return image

    async def _extract_with_easyocr(self, image: Image.Image, results: Dict) -> Dict:
        """Extract text using EasyOCR with confidence scores."""
        try:
            # Convert PIL to numpy array
            img_array = np.array(image)
            
            # Extract text with bounding boxes
            ocr_results = self.easyocr_reader.readtext(img_array, detail=1)  # type: ignore
            
            text_blocks = []
            full_text_parts = []
            total_confidence = 0
            
            for (bbox, text, confidence) in ocr_results:
                # Ensure confidence is a float
                confidence_float = float(confidence) if isinstance(confidence, (int, float, str)) else 0.0
                if confidence_float > 0.3:  # Filter low-confidence results
                    # Convert bbox to our format
                    x1, y1 = int(min(point[0] for point in bbox)), int(min(point[1] for point in bbox))
                    x2, y2 = int(max(point[0] for point in bbox)), int(max(point[1] for point in bbox))
                    
                    text_block = TextBlock(
                        text=text.strip(),
                        confidence=confidence_float,
                        bounding_box=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
                        font_size=self._estimate_font_size(y2 - y1),
                        line_number=len(text_blocks) + 1
                    )
                    
                    text_blocks.append(text_block)
                    full_text_parts.append(text.strip())
                    total_confidence += confidence_float
            
            results['text_blocks'] = text_blocks
            results['full_text'] = '\n'.join(full_text_parts)
            results['confidence'] = total_confidence / len(ocr_results) if ocr_results else 0
            
            return results
            
        except Exception as e:
            logger.error(f"EasyOCR extraction failed: {e}")
            return results

    async def _extract_with_tesseract(self, image: Image.Image, results: Dict) -> Dict:
        """Extract text using Tesseract with detailed information."""
        if not pytesseract:
            return {
                'text_blocks': [],
                'layout_elements': [],
                'full_text': '',
                'confidence': 0.0,
                'image_dimensions': image.size,
                'detected_orientation': 0
            }
            
        try:
            # Get detailed data from Tesseract
            custom_config = r'--oem 3 --psm 6'
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, config=custom_config)  # type: ignore
            
            text_blocks = []
            full_text_parts = []
            
            n_boxes = len(data['level'])
            for i in range(n_boxes):
                text = data['text'][i].strip()
                conf = int(data['conf'][i])
                
                if text and conf > 30:  # Filter low-confidence results
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    
                    text_block = TextBlock(
                        text=text,
                        confidence=conf / 100.0,  # Convert to 0-1 scale
                        bounding_box=BoundingBox(x1=x, y1=y, x2=x+w, y2=y+h),
                        font_size=self._estimate_font_size(h),
                        line_number=len(text_blocks) + 1
                    )
                    
                    text_blocks.append(text_block)
                    full_text_parts.append(text)
            
            results['text_blocks'] = text_blocks
            results['full_text'] = '\n'.join(full_text_parts)
            results['confidence'] = sum(tb.confidence for tb in text_blocks) / len(text_blocks) if text_blocks else 0
            
            return results
            
        except Exception as e:
            logger.error(f"Tesseract extraction failed: {e}")
            return results

    def _estimate_font_size(self, height: int) -> int:
        """Estimate font size from text height."""
        # Rough estimation: height in pixels to approximate font size
        return max(8, min(72, int(height * 0.75)))

    async def _detect_layout_structure(self, image: Image.Image, text_blocks: List[TextBlock]) -> List[LayoutElement]:
        """Detect document layout structure (headers, tables, paragraphs)."""
        layout_elements = []
        
        if not text_blocks:
            return layout_elements
        
        try:
            # Sort text blocks by y-coordinate (top to bottom)
            sorted_blocks = sorted(text_blocks, key=lambda b: b.bounding_box.y1)
            
            # Group text blocks into layout elements
            current_group = []
            current_y = sorted_blocks[0].bounding_box.y1 if sorted_blocks else 0
            line_height_threshold = 30  # pixels
            
            for block in sorted_blocks:
                # Check if this block is on a new line
                if block.bounding_box.y1 - current_y > line_height_threshold:
                    if current_group:
                        # Process current group
                        layout_elements.append(self._create_layout_element(current_group))
                        current_group = []
                
                current_group.append(block)
                current_y = block.bounding_box.y1
            
            # Process last group
            if current_group:
                layout_elements.append(self._create_layout_element(current_group))
            
            # Classify layout elements
            for element in layout_elements:
                element.element_type = self._classify_layout_element(element)
            
            return layout_elements
            
        except Exception as e:
            logger.error(f"Layout detection failed: {e}")
            return []

    def _create_layout_element(self, text_blocks: List[TextBlock]) -> LayoutElement:
        """Create a layout element from a group of text blocks."""
        if not text_blocks:
            return LayoutElement(
                element_type='unknown',
                bounding_box=BoundingBox(x1=0, y1=0, x2=0, y2=0),
                text='',
                confidence=0.0
            )
        
        # Calculate bounding box for the entire group
        min_x = min(block.bounding_box.x1 for block in text_blocks)
        min_y = min(block.bounding_box.y1 for block in text_blocks)
        max_x = max(block.bounding_box.x2 for block in text_blocks)
        max_y = max(block.bounding_box.y2 for block in text_blocks)
        
        # Combine text
        text = ' '.join(block.text for block in text_blocks)
        
        # Average confidence
        avg_confidence = sum(block.confidence for block in text_blocks) / len(text_blocks)
        
        return LayoutElement(
            element_type='paragraph',  # Will be classified later
            bounding_box=BoundingBox(x1=min_x, y1=min_y, x2=max_x, y2=max_y),
            text=text,
            confidence=avg_confidence,
            text_blocks=text_blocks
        )

    def _classify_layout_element(self, element: LayoutElement) -> str:
        """Classify layout element type based on characteristics."""
        text = element.text.strip()
        
        # Check for headers (typically larger font, shorter text, at top)
        avg_font_size = sum(block.font_size for block in element.text_blocks) / len(element.text_blocks)
        
        if avg_font_size > 16 and len(text) < 50:
            return 'header'
        
        # Check for table-like structure (numbers, columns)
        if self._looks_like_table_row(text):
            return 'table_row'
        
        # Check for list items
        if text.startswith(('•', '-', '*', '1.', '2.', '3.')) or text.startswith(tuple(f'{i}.' for i in range(1, 20))):
            return 'list_item'
        
        # Check for amounts/currency
        if any(symbol in text for symbol in ['$', '€', '£', '¥']) and any(char.isdigit() for char in text):
            return 'amount'
        
        # Check for dates
        if self._looks_like_date(text):
            return 'date'
        
        # Default to paragraph
        return 'paragraph'

    def _looks_like_table_row(self, text: str) -> bool:
        """Check if text looks like a table row."""
        # Simple heuristic: multiple numbers or specific spacing patterns
        words = text.split()
        if len(words) < 2:
            return False
        
        # Count numeric words
        numeric_words = sum(1 for word in words if any(char.isdigit() for char in word))
        return numeric_words >= 2 or len(words) >= 4

    def _looks_like_date(self, text: str) -> bool:
        """Check if text looks like a date."""
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',
            r'[A-Za-z]+ \d{1,2}, \d{4}',
            r'\d{1,2} [A-Za-z]+ \d{4}'
        ]
        
        import re
        for pattern in date_patterns:
            if re.search(pattern, text):
                return True
        return False

    async def find_field_locations(self, ocr_results: Dict, field_values: Dict[str, str]) -> Dict[str, BoundingBox]:
        """Find spatial locations of extracted field values in the document."""
        field_locations = {}
        
        try:
            text_blocks = ocr_results.get('text_blocks', [])
            
            for field_name, field_value in field_values.items():
                if not field_value:
                    continue
                
                # Try to find exact match first
                location = self._find_exact_match(text_blocks, field_value)
                
                if not location:
                    # Try fuzzy matching
                    location = self._find_fuzzy_match(text_blocks, field_value)
                
                if location:
                    field_locations[field_name] = location
            
            return field_locations
            
        except Exception as e:
            logger.error(f"Field location detection failed: {e}")
            return {}

    def _find_exact_match(self, text_blocks: List[TextBlock], value: str) -> Optional[BoundingBox]:
        """Find exact match of value in text blocks."""
        value_clean = value.strip().lower()
        
        for block in text_blocks:
            if value_clean in block.text.strip().lower():
                return block.bounding_box
        
        return None

    def _find_fuzzy_match(self, text_blocks: List[TextBlock], value: str) -> Optional[BoundingBox]:
        """Find fuzzy match of value in text blocks."""
        import difflib
        
        value_clean = value.strip().lower()
        best_match = None
        best_ratio = 0.0
        
        for block in text_blocks:
            ratio = difflib.SequenceMatcher(None, value_clean, block.text.strip().lower()).ratio()
            if ratio > best_ratio and ratio > 0.7:  # 70% similarity threshold
                best_ratio = ratio
                best_match = block.bounding_box
        
        return best_match
