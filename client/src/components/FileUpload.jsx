import React, { useState, useRef, useCallback } from 'react';
import './FileUpload.css';

const ACCEPTED_EXTENSIONS = [
  '.step', '.stp', '.iges', '.igs', '.brep', '.dxf',
  '.stl', '.obj', '.3mf', '.ply', '.off', '.glb', '.gltf',
];

const FORMAT_LABELS = {
  '.step': 'STEP', '.stp': 'STEP',
  '.iges': 'IGES', '.igs': 'IGES',
  '.brep': 'BRep', '.dxf': 'DXF',
  '.stl': 'STL', '.obj': 'OBJ',
  '.3mf': '3MF', '.ply': 'PLY',
  '.off': 'OFF', '.glb': 'GLB', '.gltf': 'glTF',
};

function FileUpload({ onUploadComplete, onUploadStart, disabled }) {
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  const getFileExtension = (filename) => {
    const idx = filename.lastIndexOf('.');
    return idx >= 0 ? filename.slice(idx).toLowerCase() : '';
  };

  const validateFile = (file) => {
    const ext = getFileExtension(file.name);
    if (!ACCEPTED_EXTENSIONS.includes(ext)) {
      return `Unsupported format "${ext}". Supported: ${ACCEPTED_EXTENSIONS.join(', ')}`;
    }
    const maxSize = 100 * 1024 * 1024; // 100MB
    if (file.size > maxSize) {
      return `File too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Maximum is 100 MB.`;
    }
    return null;
  };

  const handleUpload = useCallback(async (file) => {
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);
    setUploading(true);
    setUploadProgress(0);

    if (onUploadStart) {
      onUploadStart(file.name);
    }

    try {
      // Dynamic import to avoid circular deps
      const { uploadCADFile } = await import('../api');
      const result = await uploadCADFile(file, (progress) => {
        setUploadProgress(progress);
      });

      setUploading(false);
      setUploadProgress(100);

      if (onUploadComplete) {
        onUploadComplete(result);
      }
    } catch (err) {
      setUploading(false);
      setUploadProgress(0);
      setError(err.message || 'Upload failed');
    }
  }, [onUploadComplete, onUploadStart]);

  // ── Drag & Drop handlers
  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (disabled || uploading) return;

    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      handleUpload(files[0]);
    }
  }, [disabled, uploading, handleUpload]);

  const handleFileSelect = useCallback((e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleUpload(files[0]);
    }
    // Reset input so same file can be re-selected
    e.target.value = '';
  }, [handleUpload]);

  const handleClick = () => {
    if (!disabled && !uploading) {
      inputRef.current?.click();
    }
  };

  return (
    <div className="file-upload-wrapper">
      <div
        className={`file-upload-dropzone ${dragActive ? 'drag-active' : ''} ${uploading ? 'uploading' : ''} ${disabled ? 'disabled' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={handleClick}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleClick(); }}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_EXTENSIONS.join(',')}
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />

        {uploading ? (
          <div className="upload-progress-container">
            <div className="upload-spinner">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 12a9 9 0 1 1-6.219-8.56" />
              </svg>
            </div>
            <span className="upload-progress-text">
              Uploading... {uploadProgress}%
            </span>
            <div className="upload-progress-bar">
              <div
                className="upload-progress-fill"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </div>
        ) : (
          <div className="upload-idle-content">
            <div className="upload-icon">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <span className="upload-label">
              {dragActive ? 'Drop file here' : 'Upload CAD file'}
            </span>
            <span className="upload-hint">
              STEP · STL · IGES · OBJ · 3MF · DXF
            </span>
          </div>
        )}
      </div>

      {error && (
        <div className="upload-error">
          <span className="upload-error-icon">⚠️</span>
          <span className="upload-error-text">{error}</span>
          <button className="upload-error-dismiss" onClick={() => setError(null)}>✕</button>
        </div>
      )}
    </div>
  );
}

export default FileUpload;
