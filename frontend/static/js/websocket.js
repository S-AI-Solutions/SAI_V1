// WebSocket Manager for Real-time Updates

class WebSocketManager {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.onProgress = null;
        this.onError = null;
        this.onConnected = null;
        this.onDisconnected = null;
        
        this.connect();
    }
    
    connect() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/api/ws/progress`;
            
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = this.handleOpen.bind(this);
            this.ws.onmessage = this.handleMessage.bind(this);
            this.ws.onclose = this.handleClose.bind(this);
            this.ws.onerror = this.handleError.bind(this);
            
        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.scheduleReconnect();
        }
    }
    
    handleOpen(event) {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        
        if (this.onConnected) {
            this.onConnected();
        }
        
        // Send a ping to keep connection alive
        this.ping();
    }
    
    handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'ping') {
                // Respond to ping with pong
                this.send({ type: 'pong' });
                return;
            }
            
            if (this.onProgress) {
                this.onProgress(data);
            }
            
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    }
    
    handleClose(event) {
        console.log('WebSocket disconnected:', event.code, event.reason);
        
        if (this.onDisconnected) {
            this.onDisconnected(event);
        }
        
        // Attempt to reconnect if not a clean close
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
        }
    }
    
    handleError(error) {
        console.error('WebSocket error:', error);
        
        if (this.onError) {
            this.onError(error);
        }
    }
    
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('Max reconnection attempts reached');
            return;
        }
        
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        
        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
        
        setTimeout(() => {
            this.connect();
        }, delay);
    }
    
    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }
    
    ping() {
        this.send({ type: 'ping' });
        
        // Schedule next ping
        setTimeout(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ping();
            }
        }, 30000); // Ping every 30 seconds
    }
    
    close() {
        if (this.ws) {
            this.ws.close(1000, 'Client closing');
        }
    }
    
    getStatus() {
        if (!this.ws) return 'disconnected';
        
        switch (this.ws.readyState) {
            case WebSocket.CONNECTING:
                return 'connecting';
            case WebSocket.OPEN:
                return 'connected';
            case WebSocket.CLOSING:
                return 'closing';
            case WebSocket.CLOSED:
                return 'closed';
            default:
                return 'unknown';
        }
    }
}

// Progress Update Handlers
class ProgressHandler {
    constructor() {
        this.progressCallbacks = new Map();
    }
    
    onDocumentProgress(documentId, callback) {
        this.progressCallbacks.set(documentId, callback);
    }
    
    removeDocumentProgress(documentId) {
        this.progressCallbacks.delete(documentId);
    }
    
    handleProgress(data) {
        if (data.document_id && this.progressCallbacks.has(data.document_id)) {
            const callback = this.progressCallbacks.get(data.document_id);
            callback(data);
        }
        
        // Handle global progress updates
        this.handleGlobalProgress(data);
    }
    
    handleGlobalProgress(data) {
        switch (data.type) {
            case 'document_processed':
                this.showProcessingToast(data);
                break;
                
            case 'batch_processed':
                this.showBatchToast(data);
                break;
                
            case 'processing_status':
                this.updateProcessingStatus(data);
                break;
        }
    }
    
    showProcessingToast(data) {
        const message = `Document ${data.status} (${Math.round(data.confidence * 100)}% confidence)`;
        const type = data.status === 'completed' ? 'success' : 
                    data.status === 'failed' ? 'error' : 'info';
        
        if (window.documentAI) {
            window.documentAI.showToast(message, type);
        }
    }
    
    showBatchToast(data) {
        const message = `Batch completed: ${data.processed_documents}/${data.total_documents} successful`;
        
        if (window.documentAI) {
            window.documentAI.showToast(message, 'info');
        }
    }
    
    updateProcessingStatus(data) {
        // Update any visible processing indicators
        const statusElements = document.querySelectorAll('[data-status-for]');
        statusElements.forEach(element => {
            if (element.dataset.statusFor === data.document_id) {
                element.textContent = data.status;
                element.className = `status status-${data.status}`;
            }
        });
    }
}

// Real-time Status Monitor
class StatusMonitor {
    constructor() {
        this.statusIndicator = null;
        this.createStatusIndicator();
    }
    
    createStatusIndicator() {
        // Create a small status indicator in the top-right
        this.statusIndicator = document.createElement('div');
        this.statusIndicator.className = 'ws-status-indicator';
        this.statusIndicator.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #ccc;
            z-index: 1000;
            transition: background 0.3s ease;
            cursor: pointer;
        `;
        
        this.statusIndicator.title = 'Connection status';
        document.body.appendChild(this.statusIndicator);
        
        // Add click handler for status details
        this.statusIndicator.addEventListener('click', this.showStatusDetails.bind(this));
    }
    
    updateStatus(status) {
        const colors = {
            connected: '#34A853',
            connecting: '#FBBC04',
            disconnected: '#EA4335',
            error: '#EA4335'
        };
        
        this.statusIndicator.style.background = colors[status] || '#ccc';
        this.statusIndicator.title = `Connection: ${status}`;
    }
    
    showStatusDetails() {
        // Could show a modal with connection details
        console.log('WebSocket status:', window.wsManager?.getStatus());
    }
}

// Initialize WebSocket connection when script loads
let wsManager = null;
let progressHandler = null;
let statusMonitor = null;

document.addEventListener('DOMContentLoaded', () => {
    // Initialize WebSocket manager
    wsManager = new WebSocketManager();
    progressHandler = new ProgressHandler();
    statusMonitor = new StatusMonitor();
    
    // Connect handlers
    wsManager.onConnected = () => {
        statusMonitor.updateStatus('connected');
    };
    
    wsManager.onDisconnected = () => {
        statusMonitor.updateStatus('disconnected');
    };
    
    wsManager.onError = () => {
        statusMonitor.updateStatus('error');
    };
    
    wsManager.onProgress = (data) => {
        progressHandler.handleProgress(data);
    };
    
    // Make available globally
    window.wsManager = wsManager;
    window.progressHandler = progressHandler;
    window.statusMonitor = statusMonitor;
    window.WebSocketManager = WebSocketManager;
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (wsManager) {
        wsManager.close();
    }
});
