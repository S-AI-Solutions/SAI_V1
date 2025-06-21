// Document AI MVP - Main Application JavaScript (Fixed Universal Support)

class DocumentAI {
    constructor() {
        this.currentStep = 1;
        this.uploadedFiles = [];
        this.currentDocumentId = null;
        this.currentBatchId = null;
        this.ws = null;
        this.extractedData = {};
        this.zoomLevel = 1;
        this.rotation = 0;
        this.exportManager = new ExportManager();
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.initWebSocket();
        this.updateStats();
        this.showStep(1);
    }
    
    setupEventListeners() {
        // File upload
        const uploadZone = document.getElementById('upload-zone');
        const fileInput = document.getElementById('file-input');
        
        uploadZone.addEventListener('click', () => fileInput.click());
        uploadZone.addEventListener('dragover', this.handleDragOver.bind(this));
        uploadZone.addEventListener('dragleave', this.handleDragLeave.bind(this));
        uploadZone.addEventListener('drop', this.handleDrop.bind(this));
        
        fileInput.addEventListener('change', this.handleFileSelect.bind(this));
        
        // Document type selection
        document.getElementById('document-type')?.addEventListener('change', this.handleDocumentTypeChange.bind(this));
        
        // Document type cards
        document.addEventListener('click', (e) => {
            if (e.target.closest('.detection-card')) {
                this.selectDocumentType(e.target.closest('.detection-card'));
            }
        });
        
        // Processing steps
        document.querySelectorAll('.step').forEach(step => {
            step.addEventListener('click', (e) => {
                const stepNumber = parseInt(e.currentTarget.dataset.step);
                if (stepNumber <= this.currentStep) {
                    this.showStep(stepNumber);
                }
            });
        });
        
        // View toggle
        document.querySelectorAll('.toggle-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchView(e.target.dataset.view);
            });
        });
        
        // Export functionality
        document.getElementById('export-data')?.addEventListener('click', this.showExportModal.bind(this));
        document.getElementById('close-export-modal')?.addEventListener('click', this.hideExportModal.bind(this));
        document.getElementById('cancel-export')?.addEventListener('click', this.hideExportModal.bind(this));
        document.getElementById('confirm-export')?.addEventListener('click', this.exportData.bind(this));
        
        // Process another
        document.getElementById('process-another')?.addEventListener('click', this.resetProcess.bind(this));
        
        // Preview controls
        document.getElementById('zoom-in')?.addEventListener('click', () => this.adjustZoom(1.2));
        document.getElementById('zoom-out')?.addEventListener('click', () => this.adjustZoom(0.8));
        document.getElementById('rotate')?.addEventListener('click', () => this.rotateImage(90));
        
        // Navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', this.handleNavigation.bind(this));
        });
        
        // Modal close on backdrop click
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.hideExportModal();
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', this.handleKeyboard.bind(this));
    }
    
    handleDocumentTypeChange(e) {
        const selectedType = e.target.value;
        const universalOptions = document.getElementById('universal-options');
        
        if (selectedType === 'universal') {
            universalOptions.style.display = 'block';
        } else {
            universalOptions.style.display = 'none';
        }
    }
    
    handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        e.currentTarget.classList.add('dragover');
    }
    
    handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        e.currentTarget.classList.remove('dragover');
    }
    
    handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        e.currentTarget.classList.remove('dragover');
        
        const files = Array.from(e.dataTransfer.files);
        this.handleFiles(files);
    }
    
    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.handleFiles(files);
    }
    
    async handleFiles(files) {
        if (files.length === 0) return;
        
        this.uploadedFiles = files.filter(file => this.validateFile(file));
        
        if (this.uploadedFiles.length === 0) {
            this.showToast('No valid files selected', 'error');
            return;
        }
        
        if (this.uploadedFiles.length === 1) {
            await this.processSingleFile(this.uploadedFiles[0]);
        } else {
            await this.processBatchFiles(this.uploadedFiles);
        }
    }
    
    validateFile(file) {
        const maxSize = 10 * 1024 * 1024; // 10MB
        const allowedTypes = ['image/jpeg', 'image/png', 'image/tiff', 'image/webp', 'application/pdf'];
        
        if (file.size > maxSize) {
            this.showToast(`File ${file.name} is too large (max 10MB)`, 'error');
            return false;
        }
        
        if (!allowedTypes.includes(file.type)) {
            this.showToast(`File ${file.name} has unsupported format`, 'error');
            return false;
        }
        
        return true;
    }
    
    async processSingleFile(file) {
        try {
            this.showFilePreview(file);
            this.showStep(2);
            await this.detectDocumentType(file);
        } catch (error) {
            console.error('Error processing file:', error);
            this.showToast('Error processing file', 'error');
        }
    }
    
    async processBatchFiles(files) {
        // Implement batch processing logic
        console.log('Batch processing not implemented yet');
        this.showToast('Batch processing coming soon!', 'info');
    }
    
    showFilePreview(file) {
        const previewContainer = document.getElementById('preview-image');
        
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                previewContainer.innerHTML = `<img src="${e.target.result}" alt="Document preview">`;
            };
            reader.readAsDataURL(file);
        } else {
            previewContainer.innerHTML = `<div class="pdf-preview">PDF: ${file.name}</div>`;
        }
    }
    
    async detectDocumentType(file) {
        try {
            // Check if universal extraction is selected
            const documentType = document.getElementById('document-type').value;
            if (documentType === 'universal') {
                // Skip type detection for universal extraction
                this.showStep(3);
                setTimeout(() => this.startProcessing(), 500);
                return;
            }
            
            // Mock document type detection for standard processing
            const mockTypes = [
                { type: 'invoice', confidence: 0.95, description: 'Business invoice with line items and totals' },
                { type: 'receipt', confidence: 0.85, description: 'Purchase receipt from retail transaction' },
                { type: 'business_card', confidence: 0.75, description: 'Professional contact information card' },
                { type: 'form', confidence: 0.65, description: 'Structured form with fillable fields' }
            ];
            
            mockTypes.sort((a, b) => b.confidence - a.confidence);
            
            this.renderDocumentTypeCards(mockTypes);
            this.updateFieldPreview(mockTypes[0].type);
            
        } catch (error) {
            console.error('Error detecting document type:', error);
            this.showToast('Error detecting document type', 'error');
        }
    }
    
    renderDocumentTypeCards(types) {
        const container = document.getElementById('detection-cards');
        container.innerHTML = '';
        
        types.forEach((type, index) => {
            const confidenceClass = type.confidence >= 0.9 ? 'high' : 
                                   type.confidence >= 0.7 ? 'medium' : 'low';
            
            const card = document.createElement('div');
            card.className = `detection-card ${index === 0 ? 'selected' : ''}`;
            card.dataset.type = type.type;
            
            card.innerHTML = `
                <div class="card-header">
                    <div class="card-title">${type.type.replace('_', ' ')}</div>
                    <div class="confidence-badge confidence-${confidenceClass}">
                        ${Math.round(type.confidence * 100)}%
                    </div>
                </div>
                <div class="card-description">${type.description}</div>
            `;
            
            container.appendChild(card);
        });
    }
    
    selectDocumentType(card) {
        document.querySelectorAll('.detection-card').forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        
        const type = card.dataset.type;
        this.updateFieldPreview(type);
        
        setTimeout(() => {
            this.startProcessing();
        }, 1000);
    }
    
    updateFieldPreview(type) {
        const fieldMap = {
            invoice: ['Vendor Name', 'Invoice Number', 'Invoice Date', 'Total Amount', 'Currency', 'Items'],
            receipt: ['Merchant Name', 'Transaction Date', 'Total Amount', 'Payment Method', 'Items'],
            business_card: ['Full Name', 'Company', 'Title', 'Email', 'Phone', 'Address'],
            form: ['Dynamic fields based on form structure'],
            custom: ['Custom fields as specified']
        };
        
        const fields = fieldMap[type] || [];
        const container = document.getElementById('field-list');
        
        container.innerHTML = fields.map(field => 
            `<span class="field-tag">${field}</span>`
        ).join('');
    }
    
    async startProcessing() {
        this.showStep(3);
        
        try {
            await this.simulateProcessing();
            
            const file = this.uploadedFiles[0];
            const result = await this.processDocument(file);
            
            if (result.success) {
                this.currentDocumentId = result.data.id || 'universal_' + Date.now();
                
                // Handle both universal and standard extraction data
                const extractedData = result.data.extraction_results || result.data.extracted_data;
                this.extractedData = extractedData;
                
                this.showResults(result.data);
                this.showStep(4);
            } else {
                throw new Error(result.message || 'Processing failed');
            }
            
        } catch (error) {
            console.error('Processing error:', error);
            this.showToast('Processing failed: ' + error.message, 'error');
            this.showStep(1);
        }
    }
    
    async simulateProcessing() {
        const steps = [
            { title: 'Analyzing document structure...', progress: 20, time: 1000 },
            { title: 'Identifying key fields...', progress: 40, time: 1500 },
            { title: 'Extracting data with AI...', progress: 70, time: 2000 },
            { title: 'Validating results...', progress: 90, time: 1000 },
            { title: 'Processing complete!', progress: 100, time: 500 }
        ];
        
        for (const step of steps) {
            document.getElementById('processing-title').textContent = step.title;
            document.getElementById('progress-fill').style.width = step.progress + '%';
            document.getElementById('processing-message').textContent = 
                step.progress < 100 ? 'AI is analyzing your document...' : 'Ready to show results';
            
            await new Promise(resolve => setTimeout(resolve, step.time));
        }
    }
    
    async processDocument(file) {
        const documentType = document.getElementById('document-type').value;
        
        if (documentType === 'universal' || documentType === '') {
            return await this.processUniversalExtraction(file);
        } else {
            return await this.processStandardExtraction(file);
        }
    }
    
    async processUniversalExtraction(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        const extractionMode = document.getElementById('extraction-mode')?.value || 'comprehensive';
        formData.append('extraction_mode', extractionMode);
        formData.append('include_ocr', 'true');
        formData.append('include_analysis', 'true');
        
        const response = await fetch('/api/extract-universal', {
            method: 'POST',
            body: formData
        });
        
        return await response.json();
    }
    
    async processStandardExtraction(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        const documentType = document.querySelector('.detection-card.selected')?.dataset.type || 
                           document.getElementById('document-type').value;
        if (documentType && documentType !== 'universal') {
            formData.append('document_type', documentType);
        }
        
        const enhanceImage = document.getElementById('enhance-image').checked;
        formData.append('enhance_image', enhanceImage);
        
        const customFields = document.getElementById('custom-fields').value.trim();
        if (customFields) {
            formData.append('custom_fields', customFields);
        }
        
        const response = await fetch('/api/process', {
            method: 'POST',
            body: formData
        });
        
        return await response.json();
    }
    
    showResults(data) {
        // Handle both standard and universal extraction results
        const extractedData = data.extraction_results || data.extracted_data;
        
        this.showResultDocument(data);
        this.renderExtractedData(extractedData);
        this.updateConfidenceIndicators(data);
        
        if (data.summary) {
            this.showUniversalSummary(data.summary);
        }
    }
    
    showUniversalSummary(summary) {
        let summaryElement = document.querySelector('.universal-summary');
        if (!summaryElement) {
            summaryElement = document.createElement('div');
            summaryElement.className = 'universal-summary';
            summaryElement.style.cssText = `
                background: #f8f9fa;
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 20px;
                border: 1px solid #e9ecef;
            `;
            
            const resultsHeader = document.querySelector('.results-header');
            if (resultsHeader) {
                resultsHeader.appendChild(summaryElement);
            }
        }
        
        summaryElement.innerHTML = `
            <div class="summary-stats" style="display: flex; gap: 20px; align-items: center;">
                <div class="summary-stat" style="text-align: center;">
                    <span class="stat-value" style="font-size: 24px; font-weight: bold; color: #28a745;">${summary.total_fields_extracted}</span>
                    <br><span class="stat-label" style="font-size: 12px; color: #6c757d;">Fields Extracted</span>
                </div>
                <div class="summary-stat" style="text-align: center;">
                    <span class="stat-value" style="font-size: 24px; font-weight: bold; color: #007bff;">${Math.round((summary.confidence || 0) * 100)}%</span>
                    <br><span class="stat-label" style="font-size: 12px; color: #6c757d;">Confidence</span>
                </div>
                <div class="summary-stat" style="text-align: center;">
                    <span class="stat-value" style="font-size: 16px; font-weight: bold; color: #6f42c1;">${summary.document_type || 'unknown'}</span>
                    <br><span class="stat-label" style="font-size: 12px; color: #6c757d;">Document Type</span>
                </div>
            </div>
        `;
    }
    
    // FIXED: This method now renders ALL extracted fields without filtering
    renderExtractedData(extractedData) {
        console.log('Rendering extracted data:', extractedData);
        
        if (!extractedData || typeof extractedData !== 'object') {
            console.error('Invalid extracted data:', extractedData);
            return;
        }
        
        this.renderDataCards(extractedData);
        this.renderDataTable(extractedData);
        this.renderDataJSON(extractedData);
    }
    
    // FIXED: Render ALL fields as cards without any filtering
    renderDataCards(extractedData) {
        const container = document.getElementById('data-cards');
        if (!container) return;
        
        container.innerHTML = '';
        
        // Get all fields from the extracted data
        const allFields = Object.entries(extractedData || {});
        
        if (allFields.length === 0) {
            container.innerHTML = '<div class="no-data">No data extracted</div>';
            return;
        }
        
        allFields.forEach(([fieldName, fieldData]) => {
            const card = this.createFieldCard(fieldName, fieldData);
            container.appendChild(card);
        });
        
        console.log(`Rendered ${allFields.length} field cards`);
    }
    
    createFieldCard(fieldName, fieldData) {
        const card = document.createElement('div');
        card.className = 'data-card';
        card.dataset.field = fieldName;
        
        // Handle both ExtractedField objects and simple values
        const value = fieldData?.value !== undefined ? fieldData.value : fieldData;
        const confidence = fieldData?.confidence !== undefined ? fieldData.confidence : 1.0;
        const location = fieldData?.location;
        const originalText = fieldData?.original_text || value;
        
        const confidencePercent = Math.round(confidence * 100);
        const confidenceClass = confidence >= 0.9 ? 'confidence-high' : 
                               confidence >= 0.7 ? 'confidence-medium' : 'confidence-low';
        
        // Format field name for display
        const displayName = fieldName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        
        // Get field category icon
        const categoryIcon = this.getFieldCategoryIcon(fieldName);
        
        // Format location for display
        const locationDisplay = location ? 
            `📍 (${Math.round((location.x || 0) * 100)}%, ${Math.round((location.y || 0) * 100)}%)` : 
            '📍 Location not available';
        
        card.innerHTML = `
            <div class="data-card-header">
                <div class="field-meta">
                    <div class="field-name">
                        <span class="field-icon">${categoryIcon}</span>
                        ${displayName}
                    </div>
                    <div class="field-category">${this.getFieldCategory(fieldName)}</div>
                </div>
                <div class="field-actions">
                    <div class="field-confidence ${confidenceClass}">
                        ${confidencePercent}%
                    </div>
                </div>
            </div>
            <div class="field-value">${this.formatFieldValue(value)}</div>
            ${originalText && originalText !== value ? 
                `<div class="field-original-text">Original: "${originalText}"</div>` : ''}
            <div class="field-footer">
                <div class="field-location">${locationDisplay}</div>
                <div class="field-actions">
                    <button class="field-action-btn highlight-btn" title="Highlight in document">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                        </svg>
                    </button>
                    <button class="field-action-btn copy-btn" title="Copy value">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/>
                        </svg>
                    </button>
                </div>
            </div>
        `;
        
        // Add click handler for highlighting
        card.addEventListener('click', (e) => {
            if (!e.target.closest('.field-action-btn')) {
                this.highlightFieldInDocument(fieldName, location, card);
            }
        });
        
        // Add copy functionality
        const copyBtn = card.querySelector('.copy-btn');
        copyBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.copyFieldValue(value);
        });
        
        // Add highlight functionality
        const highlightBtn = card.querySelector('.highlight-btn');
        highlightBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.highlightFieldInDocument(fieldName, location, card);
        });
        
        return card;
    }
    
    formatFieldValue(value) {
        if (value === null || value === undefined) return 'N/A';
        if (Array.isArray(value)) return value.join(', ');
        if (typeof value === 'object') return JSON.stringify(value, null, 2);
        return String(value);
    }
    
    // FIXED: Render ALL fields in table format
    renderDataTable(extractedData) {
        const container = document.getElementById('data-table');
        if (!container) return;
        
        const allFields = Object.entries(extractedData || {});
        
        if (allFields.length === 0) {
            container.innerHTML = '<tr><td colspan="4">No data extracted</td></tr>';
            return;
        }
        
        const headerRow = `
            <tr>
                <th>Field Name</th>
                <th>Value</th>
                <th>Confidence</th>
                <th>Type</th>
            </tr>
        `;
        
        const dataRows = allFields.map(([fieldName, fieldData]) => {
            const value = fieldData?.value !== undefined ? fieldData.value : fieldData;
            const confidence = fieldData?.confidence !== undefined ? fieldData.confidence : 1.0;
            const type = Array.isArray(value) ? 'array' : typeof value;
            
            const displayName = fieldName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            
            return `
                <tr>
                    <td><strong>${displayName}</strong></td>
                    <td>${this.formatFieldValue(value)}</td>
                    <td>${Math.round(confidence * 100)}%</td>
                    <td>${type}</td>
                </tr>
            `;
        }).join('');
        
        container.innerHTML = headerRow + dataRows;
        
        console.log(`Rendered ${allFields.length} table rows`);
    }
    
    // FIXED: Render ALL fields as JSON
    renderDataJSON(extractedData) {
        const container = document.getElementById('json-output');
        if (!container) return;
        
        try {
            const jsonString = JSON.stringify(extractedData, null, 2);
            container.textContent = jsonString;
            console.log(`Rendered JSON with ${Object.keys(extractedData || {}).length} fields`);
        } catch (error) {
            container.textContent = 'Error rendering JSON: ' + error.message;
        }
    }
    
    switchView(view) {
        // Update toggle buttons
        document.querySelectorAll('.toggle-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === view);
        });
        
        // Update views
        document.querySelectorAll('.data-view').forEach(viewElement => {
            viewElement.classList.toggle('active', viewElement.id === `${view}-view`);
        });
    }
    
    showResultDocument(data) {
        const container = document.getElementById('result-document');
        if (!container) return;
        
        // Set up container for highlighting
        container.style.position = 'relative';
        container.style.overflow = 'hidden';
        
        if (this.uploadedFiles[0]?.type?.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                container.innerHTML = `
                    <div class="document-image-container" style="position: relative; display: inline-block;">
                        <img src="${e.target.result}" alt="Processed document" 
                             style="max-width: 100%; height: auto; display: block;" 
                             onload="this.parentElement.style.minHeight = this.offsetHeight + 'px'">
                    </div>
                `;
                
                // Initialize highlight overlay
                const imageContainer = container.querySelector('.document-image-container');
                const overlay = document.createElement('div');
                overlay.className = 'highlight-overlay';
                overlay.style.cssText = `
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    pointer-events: none;
                    z-index: 5;
                `;
                imageContainer.appendChild(overlay);
            };
            reader.readAsDataURL(this.uploadedFiles[0]);
        } else {
            container.innerHTML = `
                <div class="pdf-result" style="position: relative; padding: 40px; text-align: center; background: #f8f9fa; border-radius: 8px;">
                    <div style="font-size: 48px; margin-bottom: 16px;">📄</div>
                    <div style="font-weight: 600; margin-bottom: 8px;">PDF Document Processed</div>
                    <div style="color: #666; font-size: 14px;">Field highlighting available for image documents</div>
                </div>
            `;
        }
    }
    
    updateConfidenceIndicators(data) {
        // Update overall confidence if available
        const overallConfidence = data.metadata?.confidence || data.overall_confidence || 0;
        const confidenceElement = document.querySelector('.confidence-indicator');
        if (confidenceElement) {
            confidenceElement.textContent = `${Math.round(overallConfidence * 100)}%`;
        }
    }
    
    getFieldCategoryIcon(fieldName) {
        const field = fieldName.toLowerCase();
        
        // Numbers and amounts
        if (field.includes('amount') || field.includes('total') || field.includes('price') || 
            field.includes('cost') || field.includes('value') || field.includes('tax') ||
            field.includes('discount') || field.includes('quantity') || field.includes('rate')) {
            return '💰';
        }
        
        // Dates and times
        if (field.includes('date') || field.includes('time') || field.includes('validity') ||
            field.includes('expiry') || field.includes('issued') || field.includes('due')) {
            return '📅';
        }
        
        // Contact information
        if (field.includes('phone') || field.includes('mobile') || field.includes('email') ||
            field.includes('contact') || field.includes('fax')) {
            return '📞';
        }
        
        // Addresses and locations
        if (field.includes('address') || field.includes('location') || field.includes('city') ||
            field.includes('state') || field.includes('country') || field.includes('pin') ||
            field.includes('zip') || field.includes('from') || field.includes('to') ||
            field.includes('destination') || field.includes('origin')) {
            return '📍';
        }
        
        // Document information
        if (field.includes('number') || field.includes('id') || field.includes('reference') ||
            field.includes('invoice') || field.includes('bill') || field.includes('receipt') ||
            field.includes('document') || field.includes('serial') || field.includes('code')) {
            return '📄';
        }
        
        // Business and company info
        if (field.includes('company') || field.includes('business') || field.includes('firm') ||
            field.includes('organization') || field.includes('vendor') || field.includes('supplier') ||
            field.includes('customer') || field.includes('client') || field.includes('gstin')) {
            return '🏢';
        }
        
        // Names and personal info
        if (field.includes('name') || field.includes('person') || field.includes('signatory') ||
            field.includes('authorized') || field.includes('representative')) {
            return '👤';
        }
        
        // Transportation
        if (field.includes('vehicle') || field.includes('transport') || field.includes('distance') ||
            field.includes('route') || field.includes('journey') || field.includes('trip')) {
            return '🚛';
        }
        
        // Products and items
        if (field.includes('product') || field.includes('item') || field.includes('goods') ||
            field.includes('description') || field.includes('hsn') || field.includes('commodity')) {
            return '📦';
        }
        
        // Default icon
        return '📋';
    }
    
    getFieldCategory(fieldName) {
        const field = fieldName.toLowerCase();
        
        if (field.includes('amount') || field.includes('total') || field.includes('price') || 
            field.includes('cost') || field.includes('value') || field.includes('tax') ||
            field.includes('discount') || field.includes('quantity') || field.includes('rate')) {
            return 'Financial';
        }
        
        if (field.includes('date') || field.includes('time') || field.includes('validity') ||
            field.includes('expiry') || field.includes('issued') || field.includes('due')) {
            return 'Temporal';
        }
        
        if (field.includes('phone') || field.includes('mobile') || field.includes('email') ||
            field.includes('contact') || field.includes('fax')) {
            return 'Contact';
        }
        
        if (field.includes('address') || field.includes('location') || field.includes('city') ||
            field.includes('state') || field.includes('country') || field.includes('pin') ||
            field.includes('zip') || field.includes('from') || field.includes('to')) {
            return 'Location';
        }
        
        if (field.includes('number') || field.includes('id') || field.includes('reference') ||
            field.includes('invoice') || field.includes('bill') || field.includes('receipt') ||
            field.includes('document') || field.includes('serial') || field.includes('code')) {
            return 'Identifier';
        }
        
        if (field.includes('company') || field.includes('business') || field.includes('firm') ||
            field.includes('organization') || field.includes('vendor') || field.includes('supplier') ||
            field.includes('customer') || field.includes('client') || field.includes('gstin')) {
            return 'Business';
        }
        
        if (field.includes('name') || field.includes('person') || field.includes('signatory') ||
            field.includes('authorized') || field.includes('representative')) {
            return 'Personal';
        }
        
        if (field.includes('vehicle') || field.includes('transport') || field.includes('distance') ||
            field.includes('route') || field.includes('journey') || field.includes('trip')) {
            return 'Transportation';
        }
        
        if (field.includes('product') || field.includes('item') || field.includes('goods') ||
            field.includes('description') || field.includes('hsn') || field.includes('commodity')) {
            return 'Product';
        }
        
        return 'General';
    }
    
    async copyFieldValue(value) {
        try {
            await navigator.clipboard.writeText(String(value));
            this.showToast(`Copied "${String(value).substring(0, 50)}${String(value).length > 50 ? '...' : ''}"`, 'success');
            
            // Visual feedback - temporarily change the copy button
            const activeBtn = document.querySelector('.field-action-btn.copy-btn:hover');
            if (activeBtn) {
                activeBtn.classList.add('copy-success');
                setTimeout(() => {
                    activeBtn.classList.remove('copy-success');
                }, 600);
            }
        } catch (error) {
            console.warn('Could not copy to clipboard:', error);
            this.showToast('Could not copy to clipboard', 'error');
        }
    }
    
    highlightFieldInDocument(fieldName, location, cardElement) {
        console.log(`Highlighting field ${fieldName} at location:`, location);
        
        // Add debug information
        const fieldValue = cardElement?.querySelector('.field-value')?.textContent || '';
        this.showLocationDebugInfo(fieldName, location, fieldValue);
        
        // Remove previous highlights
        this.clearDocumentHighlights();
        
        // Highlight the clicked card
        document.querySelectorAll('.data-card').forEach(card => {
            card.classList.remove('selected');
            card.querySelectorAll('.field-action-btn').forEach(btn => btn.classList.remove('active'));
        });
        
        if (cardElement) {
            cardElement.classList.add('selected');
            const highlightBtn = cardElement.querySelector('.highlight-btn');
            if (highlightBtn) {
                highlightBtn.classList.add('active');
            }
        }
        
        // Get the document image container
        const documentImage = document.querySelector('#result-document img');
        const documentContainer = document.querySelector('#result-document');
        
        if (!documentImage || !location) {
            this.showToast('Cannot highlight: location not available', 'warning');
            return;
        }
        
        // Ensure container has proper positioning
        if (!documentContainer.style.position || documentContainer.style.position === 'static') {
            documentContainer.style.position = 'relative';
        }
        
        // Create or update highlight overlay
        let overlay = document.querySelector('.highlight-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'highlight-overlay';
            documentContainer.appendChild(overlay);
        }
        
        // Clear previous highlights
        overlay.innerHTML = '';
        
        // Calculate highlight position with improved accuracy
        const imageRect = documentImage.getBoundingClientRect();
        const containerRect = documentContainer.getBoundingClientRect();
        
        // Get image display vs natural dimensions
        const displayWidth = imageRect.width;
        const displayHeight = imageRect.height;
        const naturalWidth = documentImage.naturalWidth || displayWidth;
        const naturalHeight = documentImage.naturalHeight || displayHeight;
        
        // Calculate scaling factors for accurate positioning
        const scaleX = displayWidth / naturalWidth;
        const scaleY = displayHeight / naturalHeight;
        
        // Calculate precise coordinates
        let x, y, width, height;
        
        if (location.width && location.height && location.width > 0 && location.height > 0) {
            // Use precise bounding box data
            x = location.x * displayWidth;
            y = location.y * displayHeight;
            width = location.width * displayWidth;
            height = location.height * displayHeight;
            
            console.log(`📍 Using bounding box: ${width.toFixed(1)}x${height.toFixed(1)} at (${x.toFixed(1)}, ${y.toFixed(1)})`);
        } else {
            // Fallback to point-based highlighting with smarter sizing
            x = (location.x || 0.5) * displayWidth;
            y = (location.y || 0.5) * displayHeight;
            
            // Estimate size based on field content and position
            const fieldValue = cardElement?.dataset.field || '';
            const estimatedCharWidth = Math.max(8, displayWidth * 0.008); // Adaptive char width
            const estimatedLineHeight = Math.max(20, displayHeight * 0.025); // Adaptive line height
            
            width = Math.min(
                Math.max(100, fieldValue.length * estimatedCharWidth),
                displayWidth * 0.4
            );
            height = estimatedLineHeight;
            
            // Center the highlight around the point
            x = x - width / 2;
            y = y - height / 2;
            
            console.log(`📍 Using estimated size: ${width.toFixed(1)}x${height.toFixed(1)} at (${x.toFixed(1)}, ${y.toFixed(1)})`);
        }
        
        // Ensure highlight stays within image bounds with padding
        const padding = 5;
        x = Math.max(padding, Math.min(x, displayWidth - width - padding));
        y = Math.max(padding, Math.min(y, displayHeight - height - padding));
        
        // Ensure minimum dimensions for visibility
        width = Math.max(width, 30);
        height = Math.max(height, 20);
        
        // Create highlight element with enhanced visual effects
        const highlight = document.createElement('div');
        highlight.className = 'field-highlight';
        highlight.style.cssText = `
            left: ${x}px;
            top: ${y}px;
            width: ${width}px;
            height: ${height}px;
            animation: highlightFadeIn 0.5s ease-out, highlightPulse 2s ease-in-out infinite 0.5s;
        `;
        
        // Add field name tooltip with improved positioning
        const tooltip = document.createElement('div');
        tooltip.className = 'field-tooltip';
        tooltip.textContent = fieldName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        
        // Smart tooltip positioning based on available space
        const tooltipHeight = 40;
        const spaceAbove = y;
        const spaceBelow = displayHeight - (y + height);
        
        let tooltipTop, tooltipTransform;
        if (spaceAbove > tooltipHeight + 10) {
            // Position above
            tooltipTop = -tooltipHeight - 5;
            tooltipTransform = 'translateX(-50%)';
        } else if (spaceBelow > tooltipHeight + 10) {
            // Position below
            tooltipTop = height + 5;
            tooltipTransform = 'translateX(-50%)';
        } else {
            // Position to the side
            tooltipTop = -10;
            if (x + width + 150 < displayWidth) {
                // Position to the right
                tooltip.style.left = `${width + 10}px`;
                tooltipTransform = 'none';
            } else {
                // Position to the left
                tooltip.style.right = `${width + 10}px`;
                tooltipTransform = 'none';
            }
        }
        
        if (tooltipTransform !== 'none') {
            tooltip.style.cssText += `
                top: ${tooltipTop}px;
                left: 50%;
                transform: ${tooltipTransform};
            `;
        } else {
            tooltip.style.top = `${tooltipTop}px`;
        }
        
        // Add confidence indicator to tooltip if available
        const cardConfidence = cardElement?.querySelector('.field-confidence')?.textContent;
        if (cardConfidence) {
            tooltip.textContent += ` (${cardConfidence})`;
        }
        
        // Add tooltip to highlight
        highlight.appendChild(tooltip);
        
        // Add highlight to overlay
        overlay.appendChild(highlight);
        
        // Enhanced scroll into view with smooth animation
        this.scrollHighlightIntoView(highlight, documentContainer);
        
        // Show success message with field info
        const fieldDisplayName = fieldName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        this.showToast(`📍 Highlighted "${fieldDisplayName}" in document`, 'success');
        
        // Auto-remove highlight after 8 seconds (increased from 5)
        setTimeout(() => {
            if (highlight.parentElement) {
                this.clearDocumentHighlights();
            }
        }, 8000);
    }
    
    clearDocumentHighlights() {
        const overlay = document.querySelector('.highlight-overlay');
        if (overlay) {
            overlay.innerHTML = '';
        }
    }
    
    showExportModal() {
        const modal = document.getElementById('export-modal');
        if (modal) {
            modal.classList.add('active');
            this.populateExportFields();
        }
    }
    
    hideExportModal() {
        const modal = document.getElementById('export-modal');
        if (modal) {
            modal.classList.remove('active');
        }
    }
    
    populateExportFields() {
        const container = document.getElementById('export-field-checkboxes');
        if (!container || !this.extractedData) return;
        
        const fields = Object.keys(this.extractedData);
        container.innerHTML = fields.map(field => `
            <label class="checkbox-label">
                <input type="checkbox" value="${field}" checked>
                <span class="checkmark"></span>
                ${field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </label>
        `).join('');
    }
    
    exportData() {
        const format = document.querySelector('input[name="export-format"]:checked')?.value || 'json';
        const selectedFields = Array.from(document.querySelectorAll('#export-field-checkboxes input:checked'))
            .map(input => input.value);
        
        const exportData = this.exportManager.prepareExportData(this.extractedData, format, selectedFields);
        const filename = this.exportManager.generateFilename(exportData.extension);
        
        this.exportManager.downloadFile(exportData.content, filename, exportData.mimeType);
        this.hideExportModal();
        this.showToast(`Data exported as ${format.toUpperCase()}`, 'success');
    }
    
    resetProcess() {
        this.currentStep = 1;
        this.uploadedFiles = [];
        this.extractedData = {};
        
        document.getElementById('file-input').value = '';
        document.getElementById('document-type').value = '';
        document.getElementById('universal-options').style.display = 'none';
        
        this.showStep(1);
    }
    
    showStep(stepNumber) {
        this.currentStep = stepNumber;
        
        // Update step indicators
        document.querySelectorAll('.step').forEach((step, index) => {
            step.classList.toggle('active', index + 1 === stepNumber);
        });
        
        // Update step content panels
        document.querySelectorAll('.step-content-panel').forEach((panel, index) => {
            panel.classList.toggle('active', index + 1 === stepNumber);
        });
    }
    
    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span>${message}</span>
            <button onclick="this.parentElement.remove()">&times;</button>
        `;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 5000);
    }
    
    adjustZoom(factor) {
        this.zoomLevel *= factor;
        const images = document.querySelectorAll('#preview-image img, #result-document img');
        images.forEach(img => {
            img.style.transform = `scale(${this.zoomLevel}) rotate(${this.rotation}deg)`;
        });
    }
    
    rotateImage(degrees) {
        this.rotation += degrees;
        const images = document.querySelectorAll('#preview-image img, #result-document img');
        images.forEach(img => {
            img.style.transform = `scale(${this.zoomLevel}) rotate(${this.rotation}deg)`;
        });
    }
    
    handleNavigation(e) {
        e.preventDefault();
        const href = e.target.getAttribute('href');
        // Handle navigation
    }
    
    handleKeyboard(e) {
        // Handle keyboard shortcuts
        if (e.ctrlKey || e.metaKey) {
            switch (e.key) {
                case 'o':
                    e.preventDefault();
                    document.getElementById('file-input').click();
                    break;
                case 'e':
                    e.preventDefault();
                    this.showExportModal();
                    break;
            }
        }
    }
    
    initWebSocket() {
        try {
            this.ws = new WebSocket(`ws://${window.location.host}/api/ws/progress`);
            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };
        } catch (error) {
            console.warn('WebSocket connection failed:', error);
        }
    }
    
    handleWebSocketMessage(data) {
        console.log('WebSocket message:', data);
        // Handle real-time updates
    }
    
    updateStats() {
        // Update statistics on the page
        const statElement = document.getElementById('total-processed');
        if (statElement) {
            const current = parseInt(statElement.textContent.replace(/,/g, ''));
            statElement.textContent = (current + Math.floor(Math.random() * 10)).toLocaleString();
        }
    }
    
    scrollHighlightIntoView(highlight, container) {
        try {
            const highlightRect = highlight.getBoundingClientRect();
            const containerRect = container.getBoundingClientRect();
            
            // Check if highlight is visible in the container
            const isVisible = (
                highlightRect.top >= containerRect.top &&
                highlightRect.bottom <= containerRect.bottom &&
                highlightRect.left >= containerRect.left &&
                highlightRect.right <= containerRect.right
            );
            
            if (!isVisible) {
                highlight.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center',
                    inline: 'center'
                });
            }
        } catch (error) {
            console.warn('Could not scroll highlight into view:', error);
        }
    }
    
    showLocationDebugInfo(fieldName, location, value) {
        if (!location) {
            console.log(`📍 DEBUG: No location found for field "${fieldName}" with value "${value}"`);
            return;
        }
        
        console.log(`📍 DEBUG: Location for "${fieldName}":`, {
            field: fieldName,
            value: value,
            location: {
                x: `${(location.x * 100).toFixed(1)}%`,
                y: `${(location.y * 100).toFixed(1)}%`,
                width: location.width ? `${(location.width * 100).toFixed(1)}%` : 'auto',
                height: location.height ? `${(location.height * 100).toFixed(1)}%` : 'auto'
            },
            raw: location
        });
        
        // Add visual debug overlay if in debug mode
        if (window.location.search.includes('debug=true')) {
            this.addDebugOverlay(fieldName, location);
        }
    }
    
    addDebugOverlay(fieldName, location) {
        const documentImage = document.querySelector('#result-document img');
        const documentContainer = document.querySelector('#result-document');
        
        if (!documentImage || !documentContainer) return;
        
        // Create debug overlay
        let debugOverlay = document.querySelector('.debug-overlay');
        if (!debugOverlay) {
            debugOverlay = document.createElement('div');
            debugOverlay.className = 'debug-overlay';
            debugOverlay.style.cssText = `
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                pointer-events: none;
                z-index: 5;
            `;
            documentContainer.appendChild(debugOverlay);
        }
        
        // Calculate position
        const imageRect = documentImage.getBoundingClientRect();
        const x = location.x * imageRect.width;
        const y = location.y * imageRect.height;
        const width = (location.width || 0.1) * imageRect.width;
        const height = (location.height || 0.03) * imageRect.height;
        
        // Create debug marker
        const debugMarker = document.createElement('div');
        debugMarker.className = 'debug-marker';
        debugMarker.style.cssText = `
            position: absolute;
            left: ${x}px;
            top: ${y}px;
            width: ${width}px;
            height: ${height}px;
            border: 2px dashed #ff6b6b;
            background: rgba(255, 107, 107, 0.1);
            font-size: 10px;
            color: #ff6b6b;
            padding: 2px;
            overflow: hidden;
        `;
        debugMarker.textContent = fieldName;
        
        debugOverlay.appendChild(debugMarker);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (debugMarker.parentElement) {
                debugMarker.remove();
            }
        }, 10000);
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    window.documentAI = new DocumentAI();
});
