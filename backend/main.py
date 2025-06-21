from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import os
from pathlib import Path

from app.config import settings
from app.api.endpoints import router
from app.utils.logging import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Document AI MVP application")
    
    # Create upload directory if it doesn't exist
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(exist_ok=True)
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Document AI MVP application")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Document AI MVP with Gemini-2.0-flash integration",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")

# Health check endpoint for Railway
@app.get("/health")
async def health_check():
    """Health check endpoint for deployment platforms."""
    return {"status": "healthy", "app": settings.app_name, "version": settings.version}

# Mount static files
frontend_path = Path(__file__).parent.parent / "frontend" / "static"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

# Serve frontend
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the main frontend application."""
    frontend_file = Path(__file__).parent.parent / "frontend" / "index.html"
    
    if frontend_file.exists():
        return HTMLResponse(content=frontend_file.read_text(), status_code=200)
    else:
        return HTMLResponse(
            content="""
            <html>
                <head>
                    <title>Document AI MVP</title>
                    <style>
                        body { 
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                            max-width: 800px; 
                            margin: 50px auto; 
                            padding: 20px;
                            line-height: 1.6;
                        }
                        .header { text-align: center; margin-bottom: 40px; }
                        .status { 
                            background: #e7f5e7; 
                            border: 1px solid #4caf50; 
                            border-radius: 5px; 
                            padding: 15px; 
                            margin: 20px 0;
                        }
                        .endpoints {
                            background: #f5f5f5;
                            border-radius: 5px;
                            padding: 20px;
                            margin: 20px 0;
                        }
                        .endpoint {
                            margin: 10px 0;
                            padding: 8px;
                            background: white;
                            border-radius: 3px;
                        }
                        .method {
                            display: inline-block;
                            padding: 2px 8px;
                            border-radius: 3px;
                            font-weight: bold;
                            margin-right: 10px;
                        }
                        .post { background: #28a745; color: white; }
                        .get { background: #007bff; color: white; }
                        .ws { background: #6f42c1; color: white; }
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>🤖 Document AI MVP</h1>
                        <p>Intelligent Document Processing with Gemini-2.0-flash</p>
                    </div>
                    
                    <div class="status">
                        <h3>✅ API Server Running</h3>
                        <p>The Document AI API is ready to process your documents!</p>
                        <p><strong>Version:</strong> {version}</p>
                        <p><strong>Environment:</strong> {"Development" if settings.debug else "Production"}</p>
                    </div>
                    
                    <div class="endpoints">
                        <h3>📡 Available Endpoints</h3>
                        
                        <div class="endpoint">
                            <span class="method post">POST</span>
                            <strong>/api/process</strong> - Process single document
                        </div>
                        
                        <div class="endpoint">
                            <span class="method post">POST</span>
                            <strong>/api/batch</strong> - Process multiple documents
                        </div>
                        
                        <div class="endpoint">
                            <span class="method get">GET</span>
                            <strong>/api/documents/{'{id}'}</strong> - Get processing result
                        </div>
                        
                        <div class="endpoint">
                            <span class="method post">POST</span>
                            <strong>/api/validate</strong> - Validate/correct extracted field
                        </div>
                        
                        <div class="endpoint">
                            <span class="method get">GET</span>
                            <strong>/api/document-types</strong> - List supported document types
                        </div>
                        
                        <div class="endpoint">
                            <span class="method get">GET</span>
                            <strong>/api/stats</strong> - Get processing statistics
                        </div>
                        
                        <div class="endpoint">
                            <span class="method get">GET</span>
                            <strong>/api/health</strong> - Health check
                        </div>
                        
                        <div class="endpoint">
                            <span class="method ws">WS</span>
                            <strong>/api/ws/progress</strong> - Real-time processing updates
                        </div>
                    </div>
                    
                    <div style="text-align: center; margin-top: 40px;">
                        <p>
                            <a href="/api/docs" style="margin: 0 10px;">📚 API Documentation</a>
                            <a href="/api/redoc" style="margin: 0 10px;">📖 API Reference</a>
                        </p>
                        <p style="color: #666; font-size: 0.9em;">
                            Frontend interface will be available here once built.
                        </p>
                    </div>
                </body>
            </html>
            """.format(version=settings.version),
            status_code=200
        )


# Custom exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    return HTMLResponse(
        content="""
        <html>
            <body style="font-family: Arial, sans-serif; text-align: center; margin-top: 100px;">
                <h1>404 - Page Not Found</h1>
                <p>The requested resource was not found.</p>
                <p><a href="/">← Back to Home</a></p>
            </body>
        </html>
        """,
        status_code=404
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {exc}")
    return HTMLResponse(
        content="""
        <html>
            <body style="font-family: Arial, sans-serif; text-align: center; margin-top: 100px;">
                <h1>500 - Internal Server Error</h1>
                <p>Something went wrong on our end.</p>
                <p><a href="/">← Back to Home</a></p>
            </body>
        </html>
        """,
        status_code=500
    )


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
