# Document AI MVP

A comprehensive document extraction system with Google Document AI parity, featuring advanced OCR, spatial understanding, and interactive highlighting.

## 🚀 Features

- **Universal Document Extraction**: Extract all fields from any document type
- **Interactive Highlighting**: Click fields to see their location in the document
- **Multi-Strategy OCR**: Enhanced accuracy with multiple detection methods
- **Real-time Processing**: WebSocket-based progress tracking
- **Export Capabilities**: JSON, CSV, and Excel export options
- **Confidence Scoring**: AI-powered confidence indicators
- **Responsive Design**: Modern, mobile-friendly interface

## 🏗️ Architecture

```
document-ai-mvp/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── models/         # Data models and schemas
│   │   ├── services/       # Business logic
│   │   └── utils/          # Utilities
│   ├── main.py             # Application entry point
│   └── requirements.txt    # Python dependencies
├── frontend/               # Static web frontend
│   ├── index.html         # Main HTML file
│   └── static/
│       ├── css/           # Stylesheets
│       └── js/            # JavaScript modules
└── uploads/               # Document uploads directory
```

## 🛠️ Setup

### Prerequisites
- Python 3.8+
- pip
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd document-ai-mvp
   ```

2. **Backend Setup**
   ```bash
   cd backend
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start the server**
   ```bash
   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Access the application**
   Open http://localhost:8000 in your browser

## 🎯 Usage

1. **Upload Document**: Drag and drop or click to upload
2. **Select Extraction Type**: Choose Universal Extraction for any document
3. **Choose Mode**: Basic, Comprehensive, or Detailed extraction
4. **View Results**: Interactive cards with field highlighting
5. **Export Data**: Download results in your preferred format

## 🔧 Configuration

Edit `backend/.env` to configure:
- `GEMINI_API_KEY`: Google Gemini API key (optional)
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)
- `MAX_FILE_SIZE`: Maximum upload size in bytes

## 🧪 Testing

Run the universal extraction test:
```bash
cd backend
python test_universal_extraction.py
```

## 🎨 Highlighting Features

- **Interactive Cards**: Click any field card to highlight its location
- **Smart Positioning**: Accurate bounding box detection
- **Visual Feedback**: Smooth animations and confidence indicators
- **Debug Mode**: Add `?debug=true` to URL for debugging overlays

## 📊 Supported Document Types

- Invoices and bills
- E-way bills and receipts
- Forms and applications
- Contracts and agreements
- Any structured or semi-structured document

## 🔄 API Endpoints

- `POST /api/upload` - Upload document
- `POST /api/extract-universal` - Universal extraction
- `GET /api/documents/{doc_id}` - Get document info
- `WebSocket /api/ws/progress` - Real-time progress

## 🚀 Production Deployment

For production deployment:
1. Set environment variables appropriately
2. Use a production ASGI server (e.g., Gunicorn with Uvicorn workers)
3. Configure reverse proxy (Nginx)
4. Set up SSL certificates
5. Configure monitoring and logging

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
1. Check the documentation
2. Search existing issues
3. Create a new issue with detailed information

---

**Built with ❤️ using FastAPI, HTML5, CSS3, and JavaScript**
