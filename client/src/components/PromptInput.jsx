import React, { useState, useRef, useEffect } from 'react';
import './PromptInput.css';

function PromptInput({ onBuild, isBuilding, hasExistingDesign, uploadedFile }) {
  const [prompt, setPrompt] = useState('');
  const textareaRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  }, [prompt]);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (prompt.trim() && !isBuilding) {
      onBuild(prompt);
      setPrompt('');
    }
  };

  const handleKeyDown = (e) => {
    // Enter sends, Shift+Enter adds newline
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const placeholder = uploadedFile
    ? `Edit ${uploadedFile.filename} — describe changes... (Press Enter)`
    : hasExistingDesign
      ? "Describe what to change... (Press Enter to send)"
      : "Describe what you want to build... (Press Enter to send)";

  return (
    <div className="prompt-input">
      {uploadedFile && (
        <div className="prompt-upload-badge">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          <span>{uploadedFile.filename}</span>
          {uploadedFile.editable && <span className="badge-editable">NLP editable</span>}
        </div>
      )}
      <form onSubmit={handleSubmit}>
        <div className="input-wrapper">
          <textarea
            ref={textareaRef}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            rows={1}
            disabled={isBuilding}
          />
          <button 
            type="submit" 
            disabled={!prompt.trim() || isBuilding}
            className="send-button"
            title={isBuilding ? 'Building...' : 'Send (Enter)'}
          >
            {isBuilding ? (
              <span className="send-spinner"></span>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            )}
          </button>
        </div>
        <div className="input-hint">
          <span><kbd>Enter</kbd> to send · <kbd>Shift + Enter</kbd> for new line</span>
        </div>
      </form>
    </div>
  );
}

export default PromptInput;
