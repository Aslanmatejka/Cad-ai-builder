import React, { useState } from 'react';
import './ExportPanel.css';

/**
 * Phase 4: Export Options Panel
 * Provides download buttons for STEP, STL, and Python script
 * Includes S3 sharing functionality
 */
function ExportPanel({ buildId, stlUrl, stepUrl, parametricScript, onShare }) {
  const [sharing, setSharing] = useState(false);
  const [shareUrl, setShareUrl] = useState(null);
  const [copySuccess, setCopySuccess] = useState(false);

  const handleDownload = (url, filename) => {
    const link = document.createElement('a');
    link.href = `http://localhost:3001${url}`;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleShare = async () => {
    if (!buildId) return;
    
    setSharing(true);
    try {
      if (onShare) {
        const result = await onShare(buildId);
        setShareUrl(result.shareUrl);
      }
    } catch (error) {
      console.error('Share failed:', error);
      alert('Failed to generate share link: ' + error.message);
    } finally {
      setSharing(false);
    }
  };

  const handleCopyLink = () => {
    if (shareUrl) {
      navigator.clipboard.writeText(shareUrl);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    }
  };

  if (!buildId) {
    return null;
  }

  return (
    <div className="export-panel">
      <div className="export-header">
        <h3>📦 Export Options</h3>
        <span className="build-id">Build: {buildId.slice(0, 8)}</span>
      </div>

      <div className="export-buttons">
        {stlUrl && (
          <button 
            className="export-button stl"
            onClick={() => handleDownload(stlUrl, `${buildId}.stl`)}
          >
            <span className="icon">🖨️</span>
            <div className="button-text">
              <span className="title">Download STL</span>
              <span className="subtitle">For 3D Printing</span>
            </div>
          </button>
        )}

        {stepUrl && (
          <button 
            className="export-button step"
            onClick={() => handleDownload(stepUrl, `${buildId}.step`)}
          >
            <span className="icon">⚙️</span>
            <div className="button-text">
              <span className="title">Download STEP</span>
              <span className="subtitle">Editable CAD Format</span>
            </div>
          </button>
        )}

        {parametricScript && (
          <button 
            className="export-button script"
            onClick={() => handleDownload(parametricScript, `${buildId}_parametric.py`)}
          >
            <span className="icon">📝</span>
            <div className="button-text">
              <span className="title">Download Python Script</span>
              <span className="subtitle">Edit & Re-run Locally</span>
            </div>
          </button>
        )}
      </div>

      <div className="share-section">
        <button 
          className="share-button"
          onClick={handleShare}
          disabled={sharing || !buildId}
        >
          {sharing ? (
            <>
              <span className="spinner"></span>
              Generating Share Link...
            </>
          ) : shareUrl ? (
            '✓ Share Link Generated'
          ) : (
            '🔗 Generate Share Link'
          )}
        </button>

        {shareUrl && (
          <div className="share-link-container">
            <input 
              type="text" 
              className="share-link-input" 
              value={shareUrl} 
              readOnly 
            />
            <button 
              className="copy-button"
              onClick={handleCopyLink}
            >
              {copySuccess ? '✓ Copied!' : '📋 Copy'}
            </button>
          </div>
        )}
      </div>

      <div className="export-info">
        <p>💡 <strong>STEP files</strong> can be opened in professional CAD software (SolidWorks, Fusion 360, FreeCAD)</p>
        <p>💡 <strong>STL files</strong> are ready for slicing and 3D printing</p>
        <p>💡 <strong>Python scripts</strong> let you modify parameters and regenerate locally</p>
      </div>
    </div>
  );
}

export default ExportPanel;
