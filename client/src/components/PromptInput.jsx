import React, { useState, useRef, useEffect } from 'react';
import './PromptInput.css';

function PromptInput({ onBuild, isBuilding, hasExistingDesign }) {
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

  const placeholder = hasExistingDesign
    ? "Describe what to change... (Press Enter to send)"
    : "Describe what you want to build... (Press Enter to send)";

  return (
    <div className="prompt-input">
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
