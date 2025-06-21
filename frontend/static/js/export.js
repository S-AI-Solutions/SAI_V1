// Export functionality for Document AI MVP

class ExportManager {
    constructor() {
        this.exportFormats = ['json', 'csv', 'excel'];
        this.init();
    }
    
    init() {
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Export format change
        document.querySelectorAll('input[name="export-format"]').forEach(radio => {
            radio.addEventListener('change', this.handleFormatChange.bind(this));
        });
    }
    
    handleFormatChange(e) {
        const format = e.target.value;
        const fieldsContainer = document.getElementById('export-field-checkboxes');
        
        // Update field options based on format
        if (format === 'excel') {
            this.showExcelOptions();
        } else {
            this.hideExcelOptions();
        }
    }
    
    showExcelOptions() {
        // Add Excel-specific options if needed
        console.log('Excel format selected');
    }
    
    hideExcelOptions() {
        // Remove Excel-specific options if needed
        console.log('Non-Excel format selected');
    }
    
    prepareExportData(data, format, selectedFields) {
        const filteredData = {};
        
        // Filter data based on selected fields
        selectedFields.forEach(field => {
            if (data[field]) {
                filteredData[field] = data[field];
            }
        });
        
        switch (format) {
            case 'json':
                return this.toJSON(filteredData);
            case 'csv':
                return this.toCSV(filteredData);
            case 'excel':
                return this.toExcel(filteredData);
            default:
                return this.toJSON(filteredData);
        }
    }
    
    toJSON(data) {
        return {
            content: JSON.stringify(data, null, 2),
            mimeType: 'application/json',
            extension: 'json'
        };
    }
    
    toCSV(data) {
        const rows = [];
        const headers = ['Field', 'Value', 'Confidence', 'Type'];
        rows.push(headers.join(','));
        
        Object.entries(data).forEach(([field, fieldData]) => {
            const value = typeof fieldData === 'object' && fieldData.value !== undefined 
                ? fieldData.value 
                : fieldData;
            const confidence = typeof fieldData === 'object' && fieldData.confidence !== undefined 
                ? fieldData.confidence 
                : 'N/A';
            const type = typeof fieldData === 'object' && fieldData.type !== undefined 
                ? fieldData.type 
                : typeof value;
            
            rows.push([
                `"${field}"`,
                `"${value}"`,
                confidence,
                `"${type}"`
            ].join(','));
        });
        
        return {
            content: rows.join('\n'),
            mimeType: 'text/csv',
            extension: 'csv'
        };
    }
    
    toExcel(data) {
        // For now, export as CSV (in a real implementation, you'd use a library like xlsx)
        return this.toCSV(data);
    }
    
    downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.style.display = 'none';
        
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        URL.revokeObjectURL(url);
    }
    
    generateFilename(format, documentType = 'document') {
        const timestamp = new Date().toISOString().split('T')[0];
        return `${documentType}_extraction_${timestamp}.${format}`;
    }
}

// Export for use in main app
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ExportManager;
} else {
    window.ExportManager = ExportManager;
}
