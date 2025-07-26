/**
 * Vehicle Photo Analysis Upload Function
 * 
 * This function handles uploading vehicle photos to the backend API
 * in the correct format for analysis.
 */

/**
 * Analyzes vehicle photos by sending them to the backend API
 * @param {Array} photos - Array of photo objects with dataUrl and category properties
 * @param {Object} vehicleInfo - Optional vehicle metadata (make, model, year, askingPrice)
 * @param {string} apiBase - Base URL for the API
 * @param {Object} ui - UI elements for updating progress and status
 * @returns {Promise} - Resolves with analysis results or rejects with error
 */
async function analyzeVehiclePhotos(photos, vehicleInfo, apiBase, ui) {
    if (photos.length === 0) {
        throw new Error('Please take at least one photo before analyzing.');
    }

    // Show uploading UI
    if (ui.actionContainer) ui.actionContainer.style.display = 'none';
    if (ui.uploadingContainer) ui.uploadingContainer.style.display = 'flex';
    
    // Build the payload in the format expected by the backend
    const payload = {
        photos: photos.map(photo => ({
            // Strip the `data:image/jpeg;base64,` prefix so the backend
            // only receives base-64 data
            image_data: photo.dataUrl.split(',')[1],
            category: photo.category
        })),
        // Include vehicle info if available
        vehicle_info: vehicleInfo || null
    };

    try {
        // Update progress indicator (start)
        if (ui.uploadProgress) ui.uploadProgress.textContent = '0';
        if (ui.progressFill) ui.progressFill.style.width = '0%';

        // Use fetch API to send the data
        const response = await fetch(
            `${apiBase}/api/vehicles/analyze`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            }
        );

        // Update progress to 100% when request completes
        if (ui.uploadProgress) ui.uploadProgress.textContent = '100';
        if (ui.progressFill) ui.progressFill.style.width = '100%';

        // Check if the request was successful
        if (!response.ok) {
            throw new Error(`Upload failed: ${response.status} ${response.statusText}`);
        }

        // Parse the JSON response
        const analysisResults = await response.json();
        
        // Reset UI
        if (ui.uploadingContainer) ui.uploadingContainer.style.display = 'none';
        if (ui.actionContainer) ui.actionContainer.style.display = 'flex';
        
        return analysisResults;
    } catch (error) {
        console.error('Photo upload failed:', error);
        
        // Reset UI on error
        if (ui.uploadingContainer) ui.uploadingContainer.style.display = 'none';
        if (ui.actionContainer) ui.actionContainer.style.display = 'flex';
        
        throw error;
    }
}

// For integration with the existing app
function integrateWithApp(app) {
    // Replace the app's analyzePhotos method with our improved version
    app.analyzePhotos = async function() {
        if (this.isUploading) return; // guard against double-click
        this.isUploading = true;
        
        try {
            const ui = {
                actionContainer: this.actionContainer,
                uploadingContainer: this.uploadingContainer,
                uploadProgress: this.uploadProgress,
                progressFill: this.progressFill
            };
            
            const results = await analyzeVehiclePhotos(
                this.photos,
                this.vehicleInfo,
                this.apiBase,
                ui
            );
            
            // You can use the real results or fall back to the mock results
            // For now, we'll use the app's existing showAnalysisResults method
            this.showAnalysisResults(results);
        } catch (error) {
            alert(error.message || 'Upload failed. Showing simulated analysis instead.');
            // Fall back to simulated results
            this.showAnalysisResults();
        } finally {
            this.isUploading = false;
        }
    };
    
    return app;
}

// Export the functions
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        analyzeVehiclePhotos,
        integrateWithApp
    };
}
