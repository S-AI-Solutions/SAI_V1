#!/usr/bin/env python3
"""Test real image upload to production endpoints."""

import requests
import base64
import json
from PIL import Image, ImageDraw, ImageFont
import io

# Create a simple test invoice image
def create_test_invoice():
    """Create a simple test invoice image."""
    # Create a white background
    img = Image.new('RGB', (800, 1000), 'white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a font, fallback to default if not available
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
        font_medium = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 18)
        font_small = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 14)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Header
    draw.text((50, 50), "TECH SOLUTIONS INC.", fill='black', font=font_large)
    draw.text((50, 80), "123 Business Street", fill='black', font=font_small)
    draw.text((50, 100), "Tech City, TC 12345", fill='black', font=font_small)
    
    # Invoice info
    draw.text((500, 50), "INVOICE", fill='black', font=font_large)
    draw.text((500, 100), "Invoice #: INV-2025-0042", fill='black', font=font_medium)
    draw.text((500, 130), "Date: June 18, 2025", fill='black', font=font_medium)
    draw.text((500, 160), "Due Date: July 18, 2025", fill='black', font=font_medium)
    
    # Bill to
    draw.text((50, 200), "Bill To:", fill='black', font=font_medium)
    draw.text((50, 230), "ABC Corporation", fill='black', font=font_small)
    draw.text((50, 250), "456 Client Avenue", fill='black', font=font_small)
    draw.text((50, 270), "Client City, CC 67890", fill='black', font=font_small)
    
    # Items table
    y_pos = 350
    draw.text((50, y_pos), "Description", fill='black', font=font_medium)
    draw.text((300, y_pos), "Qty", fill='black', font=font_medium)
    draw.text((400, y_pos), "Rate", fill='black', font=font_medium)
    draw.text((500, y_pos), "Amount", fill='black', font=font_medium)
    
    # Line
    draw.line([(50, y_pos + 25), (550, y_pos + 25)], fill='black', width=1)
    
    # Items
    y_pos += 40
    draw.text((50, y_pos), "Software Development Services", fill='black', font=font_small)
    draw.text((300, y_pos), "40", fill='black', font=font_small)
    draw.text((400, y_pos), "$500.00", fill='black', font=font_small)
    draw.text((500, y_pos), "$20,000.00", fill='black', font=font_small)
    
    y_pos += 30
    draw.text((50, y_pos), "Consulting Services", fill='black', font=font_small)
    draw.text((300, y_pos), "15", fill='black', font=font_small)
    draw.text((400, y_pos), "$500.00", fill='black', font=font_small)
    draw.text((500, y_pos), "$7,500.00", fill='black', font=font_small)
    
    # Totals
    y_pos = 700
    draw.text((400, y_pos), "Subtotal:", fill='black', font=font_medium)
    draw.text((500, y_pos), "$27,500.00", fill='black', font=font_medium)
    
    y_pos += 30
    draw.text((400, y_pos), "Tax (8.5%):", fill='black', font=font_medium)
    draw.text((500, y_pos), "$2,337.50", fill='black', font=font_medium)
    
    y_pos += 30
    draw.text((400, y_pos), "Total:", fill='black', font=font_large)
    draw.text((500, y_pos), "$29,837.50", fill='black', font=font_large)
    
    # Payment terms
    y_pos += 80
    draw.text((50, y_pos), "Payment Terms: Net 30 Days", fill='black', font=font_small)
    
    return img

def test_production_endpoints():
    """Test all production endpoints with a real image."""
    print("🧪 Testing Production Endpoints with Real Image Upload")
    print("=" * 60)
    
    # Create test image
    print("📄 Creating test invoice image...")
    img = create_test_invoice()
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes = img_bytes.getvalue()
    
    # Save image for reference
    img.save('test_invoice.png')
    print(f"✅ Test invoice saved as 'test_invoice.png' ({len(img_bytes)} bytes)")
    
    base_url = "http://localhost:8000/api"
    
    # Test 1: Health Check
    print("\n🔍 Testing Health Check...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data.get('status', 'OK')}")
            print(f"   Gemini Status: {data.get('gemini_status', 'Unknown')}")
        else:
            print(f"❌ Health check failed with status {response.status_code}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
    
    # Test 2: Standard Processing
    print("\n🔍 Testing Standard Processing...")
    try:
        files = {'file': ('test_invoice.png', img_bytes, 'image/png')}
        data = {'document_type': 'invoice', 'enhance_image': True}
        
        response = requests.post(f"{base_url}/process", files=files, data=data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                doc_data = result['data']
                print(f"✅ Standard processing successful!")
                print(f"   Document ID: {doc_data.get('id')}")
                print(f"   Document Type: {doc_data.get('document_type')}")
                print(f"   Overall Confidence: {doc_data.get('overall_confidence', 0):.1f}%")
                print(f"   Processing Time: {doc_data.get('metadata', {}).get('processing_time', 0):.2f}s")
                
                # Show some extracted fields
                extracted = doc_data.get('extracted_data', {})
                print(f"   Extracted Fields: {len(extracted)}")
                for field_name, field_data in list(extracted.items())[:3]:
                    value = field_data.get('value', 'N/A')
                    confidence = field_data.get('confidence', 0) * 100
                    print(f"     {field_name}: {value} ({confidence:.1f}% confidence)")
            else:
                print(f"❌ Standard processing failed: {result.get('message')}")
        else:
            print(f"❌ Standard processing failed with status {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Standard processing error: {e}")
    
    # Test 3: Production Processing (Different Modes)
    for mode in ['fast', 'balanced', 'high']:  # Use lowercase
        print(f"\n🚀 Testing Production Processing - {mode.upper()} Mode...")
        try:
            files = {'file': ('test_invoice.png', img_bytes, 'image/png')}
            data = {
                'document_type': 'invoice',
                'accuracy_mode': mode,  # Use lowercase
                'enable_validation': True,
                'enable_spatial_analysis': True
            }
            
            response = requests.post(f"{base_url}/process-production", files=files, data=data)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    doc_data = result['data']
                    print(f"✅ {mode} mode processing successful!")
                    print(f"   Document ID: {doc_data.get('id')}")
                    print(f"   Document Type: {doc_data.get('document_type')}")
                    print(f"   Type Confidence: {doc_data.get('document_type_confidence', 0):.1f}%")
                    print(f"   Overall Confidence: {doc_data.get('overall_confidence', 0):.1f}%")
                    print(f"   Processing Time: {doc_data.get('metadata', {}).get('processing_time', 0):.2f}s")
                    
                    # Show extracted fields with locations
                    extracted = doc_data.get('extracted_data', {})
                    print(f"   Extracted Fields: {len(extracted)}")
                    for field_name, field_data in list(extracted.items())[:3]:
                        value = field_data.get('value', 'N/A')
                        confidence = field_data.get('confidence', 0) * 100
                        location = field_data.get('location')
                        loc_str = ""
                        if location:
                            loc_str = f" [x={location.get('x', 0):.2f}, y={location.get('y', 0):.2f}]"
                        print(f"     {field_name}: {value} ({confidence:.1f}%){loc_str}")
                else:
                    print(f"❌ {mode} processing failed: {result.get('message')}")
            else:
                print(f"❌ {mode} processing failed with status {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"❌ {mode} processing error: {e}")
    
    # Test 4: Production Statistics
    print(f"\n📊 Testing Production Statistics...")
    try:
        response = requests.get(f"{base_url}/production-stats")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                stats = result['data']
                print(f"✅ Production statistics retrieved!")
                print(f"   Total Processed: {stats.get('total_documents', 0)}")
                print(f"   Success Rate: {stats.get('success_rate', 0):.1f}%")
                print(f"   Average Confidence: {stats.get('average_confidence', 0):.1f}%")
                print(f"   Average Processing Time: {stats.get('average_processing_time', 0):.2f}s")
            else:
                print(f"❌ Stats retrieval failed: {result.get('message')}")
        else:
            print(f"❌ Stats retrieval failed with status {response.status_code}")
    except Exception as e:
        print(f"❌ Stats error: {e}")
    
    # Test 5: Service Comparison
    print(f"\n🔍 Testing Service Comparison...")
    try:
        response = requests.get(f"{base_url}/compare-services")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                comparison = result['data']
                print(f"✅ Service comparison retrieved!")
                
                standard = comparison.get('standard_service', {})
                production = comparison.get('production_service', {})
                
                print(f"   Standard Service:")
                print(f"     Processed: {standard.get('total_processed', 0)}")
                print(f"     Avg Confidence: {standard.get('avg_confidence', 0):.1f}%")
                
                print(f"   Production Service:")
                print(f"     Processed: {production.get('total_processed', 0)}")
                print(f"     Avg Confidence: {production.get('avg_confidence', 0):.1f}%")
                print(f"     Enhanced Features: {len(production.get('enhanced_features', []))}")
            else:
                print(f"❌ Comparison failed: {result.get('message')}")
        else:
            print(f"❌ Comparison failed with status {response.status_code}")
    except Exception as e:
        print(f"❌ Comparison error: {e}")
    
    print(f"\n🎉 Testing completed!")
    print(f"Check 'test_invoice.png' for the test image used.")

if __name__ == "__main__":
    test_production_endpoints()
