#!/usr/bin/env python3
"""Test universal extraction with real document images."""

import requests
import base64
import json
from PIL import Image, ImageDraw, ImageFont
import io

def create_eway_bill_test():
    """Create a test E-way bill similar to the uploaded image."""
    img = Image.new('RGB', (800, 1100), 'white')
    draw = ImageDraw.Draw(img)
    
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 20)
        font_medium = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
        font_small = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 12)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Header
    draw.text((300, 30), "E-WAY BILL Details", fill='black', font=font_large)
    
    # E-way Bill Info
    draw.text((50, 80), "E-Way Bill No: 111023233647", fill='black', font=font_medium)
    draw.text((450, 80), "Generated Date: 01-05-2025 05:47:00 AM", fill='black', font=font_small)
    draw.text((450, 100), "Valid Upto: 02-05-2025 11:59:00 PM", fill='black', font=font_small)
    
    # Transport Details
    draw.text((50, 140), "Mode: Road", fill='black', font=font_small)
    draw.text((200, 140), "Approx Distance: 74 km", fill='black', font=font_small)
    draw.text((400, 140), "Transaction Type: Regular", fill='black', font=font_small)
    
    # From Details
    draw.text((50, 180), "From:", fill='black', font=font_medium)
    draw.text((50, 200), "GSTIN: 37AAACV2678L1ZT", fill='black', font=font_small)
    draw.text((50, 220), "Jerun Beverages Limited", fill='black', font=font_small)
    draw.text((50, 240), "37, Andhra Pradesh - 517146", fill='black', font=font_small)
    
    # To Details  
    draw.text((450, 180), "To:", fill='black', font=font_medium)
    draw.text((450, 200), "GSTIN: 33AAPCS6916228", fill='black', font=font_small)
    draw.text((450, 220), "SCOOTY LOGISTICS PRIVATE LIMITED", fill='black', font=font_small)
    draw.text((450, 240), "Tamil Nadu", fill='black', font=font_small)
    
    # Goods Details Header
    draw.text((50, 300), "Goods Details:", fill='black', font=font_medium)
    
    # Table Header
    y_pos = 330
    draw.text((50, y_pos), "HSN Code", fill='black', font=font_small)
    draw.text((150, y_pos), "Product Description", fill='black', font=font_small)
    draw.text((400, y_pos), "Quantity", fill='black', font=font_small)
    draw.text((500, y_pos), "Taxable Amount", fill='black', font=font_small)
    draw.text((650, y_pos), "Tax Amount", fill='black', font=font_small)
    
    # Table line
    draw.line([(50, y_pos + 20), (750, y_pos + 20)], fill='black', width=1)
    
    # Table Data
    y_pos += 30
    draw.text((50, y_pos), "22011010", fill='black', font=font_small)
    draw.text((150, y_pos), "AQUAFINA 250ml PET 36 Bot", fill='black', font=font_small)
    draw.text((400, y_pos), "200", fill='black', font=font_small)
    draw.text((500, y_pos), "27118.64", fill='black', font=font_small)
    draw.text((650, y_pos), "4881.36", fill='black', font=font_small)
    
    y_pos += 25
    draw.text((50, y_pos), "22021010", fill='black', font=font_small)
    draw.text((150, y_pos), "7 UP FIZZ 750ML PET 24*40", fill='black', font=font_small)
    draw.text((400, y_pos), "50", fill='black', font=font_small)
    draw.text((500, y_pos), "24607.14", fill='black', font=font_small)
    draw.text((650, y_pos), "6890", fill='black', font=font_small)
    
    # Totals
    y_pos += 50
    draw.text((400, y_pos), "Total Taxable Amount:", fill='black', font=font_medium)
    draw.text((600, y_pos), "262779.05", fill='black', font=font_medium)
    
    y_pos += 25
    draw.text((400, y_pos), "CGST Amount:", fill='black', font=font_small)
    draw.text((600, y_pos), "0", fill='black', font=font_small)
    
    y_pos += 25
    draw.text((400, y_pos), "SGST Amount:", fill='black', font=font_small)
    draw.text((600, y_pos), "0", fill='black', font=font_small)
    
    # Vehicle Details
    y_pos += 60
    draw.text((50, y_pos), "Vehicle Details:", fill='black', font=font_medium)
    y_pos += 25
    draw.text((50, y_pos), "Vehicle No: TN394615", fill='black', font=font_small)
    
    # Transporter Details
    y_pos += 40
    draw.text((50, y_pos), "Transporter Details:", fill='black', font=font_medium)
    y_pos += 25
    draw.text((50, y_pos), "Transporter ID & Name: 37AAACG109901ZJ", fill='black', font=font_small)
    
    return img

def test_universal_extraction():
    """Test the universal extraction endpoint."""
    print("🧪 Testing Universal Document Extraction")
    print("=" * 60)
    
    # Create test E-way bill
    print("📄 Creating test E-way bill image...")
    img = create_eway_bill_test()
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes = img_bytes.getvalue()
    
    # Save for reference
    img.save('test_eway_bill.png')
    print(f"✅ Test E-way bill saved as 'test_eway_bill.png' ({len(img_bytes)} bytes)")
    
    base_url = "http://localhost:8000/api"
    
    # Test different extraction modes
    for mode in ['basic', 'comprehensive', 'detailed']:
        print(f"\n🔍 Testing Universal Extraction - {mode.upper()} Mode...")
        
        try:
            files = {'file': ('test_eway_bill.png', img_bytes, 'image/png')}
            data = {
                'extraction_mode': mode,
                'include_ocr': True,
                'include_analysis': True
            }
            
            response = requests.post(f"{base_url}/extract-universal", files=files, data=data)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    data = result['data']
                    print(f"✅ {mode.capitalize()} extraction successful!")
                    
                    # Print summary
                    summary = data.get('summary', {})
                    print(f"   Total Fields Extracted: {summary.get('total_fields_extracted', 0)}")
                    print(f"   Document Type: {summary.get('document_type', 'unknown')}")
                    print(f"   Overall Confidence: {summary.get('confidence', 0):.1%}")
                    print(f"   Field Categories: {', '.join(summary.get('field_categories', []))}")
                    
                    # Print some extracted fields
                    extraction_results = data.get('extraction_results', {})
                    print(f"\n📋 Sample Extracted Fields:")
                    count = 0
                    for field_name, field_data in extraction_results.items():
                        if count >= 5:  # Show first 5 fields
                            break
                        value = field_data.get('value', 'N/A')
                        confidence = field_data.get('confidence', 0) * 100
                        location = field_data.get('location')
                        loc_str = ""
                        if location:
                            loc_str = f" [x={location.get('x', 0):.2f}, y={location.get('y', 0):.2f}]"
                        print(f"     {field_name}: {value} ({confidence:.1f}%){loc_str}")
                        count += 1
                    
                    if len(extraction_results) > 5:
                        print(f"     ... and {len(extraction_results) - 5} more fields")
                    
                    # Print document analysis if available
                    if data.get('document_analysis'):
                        analysis = data['document_analysis']
                        print(f"\n📊 Document Analysis:")
                        print(f"   Structure Type: {analysis.get('structure_type', 'unknown')}")
                        print(f"   Document Format: {analysis.get('document_format', 'unknown')}")
                        
                        layout = analysis.get('layout_characteristics', {})
                        print(f"   Text Blocks: {layout.get('total_text_blocks', 0)}")
                        print(f"   Has Tables: {layout.get('has_tables', False)}")
                        print(f"   Has Headers: {layout.get('has_headers', False)}")
                    
                else:
                    print(f"❌ {mode} extraction failed: {result.get('message')}")
                    if result.get('errors'):
                        print(f"   Errors: {result['errors']}")
            else:
                print(f"❌ {mode} extraction failed with status {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"❌ {mode} extraction error: {e}")
    
    print(f"\n🎉 Universal extraction testing completed!")
    print(f"Check 'test_eway_bill.png' for the test image used.")

if __name__ == "__main__":
    test_universal_extraction()
