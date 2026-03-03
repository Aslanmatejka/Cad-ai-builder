import React, { useRef, useEffect, useCallback, useState } from 'react';
import PromptInput from './components/PromptInput';
import MultiProductCanvas from './components/MultiProductCanvas';
import ProjectBrowser from './components/ProjectBrowser';
import ParameterPanel from './components/ParameterPanel';
import ExportPanel from './components/ExportPanel';
import FileUpload from './components/FileUpload';
import { useAppContext } from './context/AppContext';
import { useBuild } from './hooks/useBuild';
import { uploadToS3 } from './api';
import './App.css';

const API_HOST = process.env.REACT_APP_API_HOST || 'http://localhost:3001';

function App() {
  const { state, dispatch, canUndo, canRedo, undo, redo } = useAppContext();
  const {
    status, result, messages, currentDesign, currentBuildId,
    chatWidth, isDragging, chatCollapsed, previewCollapsed,
    activeTab, showProjectBrowser, buildProgress, sceneProducts,
    currentScene, showParameterPanel, buildStartTime, uploadedFile,
  } = state;

  const { handleBuild, handleRebuild, handleProjectSelect, handleNewProject, initializeScene, handleUploadComplete } = useBuild();

  const messagesEndRef = useRef(null);
  const chatMessagesRef = useRef(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 968);
  const [elapsedTime, setElapsedTime] = useState(0);

  // Track mobile breakpoint
  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth <= 968);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  // Smart auto-scroll: only scroll if user is already at bottom
  useEffect(() => {
    if (isAtBottom) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isAtBottom]);

  const handleChatScroll = useCallback(() => {
    const el = chatMessagesRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
    setIsAtBottom(atBottom);
  }, []);

  // Elapsed time during build
  useEffect(() => {
    if (status !== 'building' || !buildStartTime) {
      setElapsedTime(0);
      return;
    }
    const interval = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - buildStartTime) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [status, buildStartTime]);

  // Resize handle
  const handleMouseDown = (e) => {
    dispatch({ type: 'SET_DRAGGING', payload: true });
    e.preventDefault();
  };

  const handleMouseMove = useCallback((e) => {
    if (!isDragging) return;
    const newWidth = (e.clientX / window.innerWidth) * 100;
    if (newWidth >= 20 && newWidth <= 80) {
      dispatch({ type: 'SET_CHAT_WIDTH', payload: newWidth });
    }
  }, [isDragging, dispatch]);

  const handleMouseUp = useCallback(() => {
    dispatch({ type: 'SET_DRAGGING', payload: false });
  }, [dispatch]);

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);

  // Initialize scene on mount
  useEffect(() => {
    if (!currentScene) initializeScene();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyboard = (e) => {
      if (e.ctrlKey && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        if (canUndo) undo();
      }
      if (e.ctrlKey && e.key === 'z' && e.shiftKey) {
        e.preventDefault();
        if (canRedo) redo();
      }
      if (e.ctrlKey && e.key === 'y') {
        e.preventDefault();
        if (canRedo) redo();
      }
    };
    window.addEventListener('keydown', handleKeyboard);
    return () => window.removeEventListener('keydown', handleKeyboard);
  }, [canUndo, canRedo, undo, redo]);

  // Compute grid columns
  const getGridColumns = () => {
    if (isMobile) return '1fr';
    if (chatCollapsed) return '48px 0px 1fr';
    if (previewCollapsed) return '1fr 0px 48px';
    return `${chatWidth}% 8px ${100 - chatWidth}%`;
  };

  const formatTime = (seconds) => {
    if (seconds < 60) return `${seconds}s`;
    return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  };

  // Quick-start examples
  const examples = [
    { emoji: '📱', text: 'iPhone 15 Pro case with camera cutout and charging port', category: 'Everyday' },
    { emoji: '🎮', text: 'Game controller grip with ergonomic curves', category: 'Gaming' },
    { emoji: '⚙️', text: 'Raspberry Pi 4 case with ventilation slots and mounting holes', category: 'Tech' },
    { emoji: '🏠', text: 'Desk organizer with pen holder and phone stand', category: 'Home' },
    { emoji: '🔧', text: 'Adjustable wrench 150mm with textured handle', category: 'Tools' },
    { emoji: '☕', text: 'Travel mug with threaded lid and grip texture', category: 'Kitchen' },
  ];

  const parameters = currentDesign?.parameters;
  const hasDesign = !!result;

  return (
    <div className="App">
      {/* ════ Header ════ */}
      <header>
        <div className="header-left">
          <h1>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
            Product Builder
          </h1>
        </div>
        <div className="header-center">
          {/* Undo / Redo */}
          <button
            className="header-icon-btn"
            onClick={undo}
            disabled={!canUndo}
            title="Undo (Ctrl+Z)"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="1 4 1 10 7 10"/>
              <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
            </svg>
          </button>
          <button
            className="header-icon-btn"
            onClick={redo}
            disabled={!canRedo}
            title="Redo (Ctrl+Shift+Z)"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="23 4 23 10 17 10"/>
              <path d="M20.49 15a9 9 0 1 1-2.13-9.36L23 10"/>
            </svg>
          </button>
        </div>
        <div className="header-right">
          <button
            className="projects-btn"
            onClick={() => dispatch({ type: 'SET_SHOW_PROJECT_BROWSER', payload: true })}
            title="View your saved projects"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M1.5 0A1.5 1.5 0 0 0 0 1.5v13A1.5 1.5 0 0 0 1.5 16h13a1.5 1.5 0 0 0 1.5-1.5v-13A1.5 1.5 0 0 0 14.5 0h-13zM1 1.5a.5.5 0 0 1 .5-.5h13a.5.5 0 0 1 .5.5v13a.5.5 0 0 1-.5.5h-13a.5.5 0 0 1-.5-.5v-13z"/>
              <path d="M4 4a.5.5 0 0 1 .5-.5h7a.5.5 0 0 1 0 1h-7A.5.5 0 0 1 4 4zm0 3a.5.5 0 0 1 .5-.5h7a.5.5 0 0 1 0 1h-7A.5.5 0 0 1 4 7zm0 3a.5.5 0 0 1 .5-.5h7a.5.5 0 0 1 0 1h-7a.5.5 0 0 1 0-1z"/>
            </svg>
            My Projects
          </button>
          {result && (result.stlUrl || result.files?.stl || result.stepUrl || result.files?.step) && (
            <div className="export-links">
              {(result.stlUrl || result.files?.stl) && (
                <a
                  href={`${API_HOST}${result.stlUrl || result.files.stl}`}
                  download
                  className="export-btn"
                  title="Download for 3D printing"
                >
                  🖨️ STL
                </a>
              )}
              {(result.stepUrl || result.files?.step) && (
                <a
                  href={`${API_HOST}${result.stepUrl || result.files.step}`}
                  download
                  className="export-btn"
                  title="Open in FreeCAD or Fusion 360"
                >
                  ✏️ STEP
                </a>
              )}
            </div>
          )}
        </div>
      </header>

      {/* ════ Build Progress Bar ════ */}
      {status === 'building' && (
        <div className="build-progress-bar">
          <div
            className="build-progress-fill"
            style={{ width: `${buildProgress}%` }}
          />
          <span className="build-progress-label">
            {buildProgress < 100 ? `Building... ${formatTime(elapsedTime)}` : 'Finishing...'}
          </span>
        </div>
      )}

      {/* ════ Mobile Tab Bar ════ */}
      {isMobile && (
        <div className="mobile-tab-bar">
          <button
            className={`mobile-tab ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => dispatch({ type: 'SET_ACTIVE_TAB', payload: 'chat' })}
          >
            💬 Chat
          </button>
          <button
            className={`mobile-tab ${activeTab === 'preview' ? 'active' : ''}`}
            onClick={() => dispatch({ type: 'SET_ACTIVE_TAB', payload: 'preview' })}
          >
            👁️ 3D Preview
            {sceneProducts.length > 0 && (
              <span className="mobile-tab-badge">{sceneProducts.length}</span>
            )}
          </button>
        </div>
      )}

      {/* ════ Main Layout ════ */}
      <main style={{ gridTemplateColumns: getGridColumns() }}>
        {/* ──── Chat Panel ──── */}
        <div className={`chat-container ${chatCollapsed ? 'collapsed' : ''} ${isMobile && activeTab !== 'chat' ? 'mobile-hidden' : ''}`}>
          {chatCollapsed ? (
            <button
              className="panel-expand-btn"
              onClick={() => dispatch({ type: 'TOGGLE_CHAT_COLLAPSED' })}
              title="Expand chat"
            >
              <span className="panel-expand-label">💬</span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="9 18 15 12 9 6"/>
              </svg>
            </button>
          ) : (
            <>
              {/* Chat panel header with collapse button */}
              {!isMobile && (
                <div className="panel-header chat-panel-header">
                  <span className="panel-title">💬 Chat</span>
                  <button
                    className="panel-collapse-btn"
                    onClick={() => dispatch({ type: 'TOGGLE_CHAT_COLLAPSED' })}
                    title="Collapse chat panel"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="15 18 9 12 15 6"/>
                    </svg>
                  </button>
                </div>
              )}

              <div
                className="chat-messages"
                ref={chatMessagesRef}
                onScroll={handleChatScroll}
              >
                {messages.length === 0 ? (
                  <div className="welcome-screen">
                    <div className="welcome-content">
                      <div className="welcome-hero">
                        <div className="welcome-icon">
                          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                            <path d="M2 17l10 5 10-5"/>
                            <path d="M2 12l10 5 10-5"/>
                          </svg>
                        </div>
                        <h2>What do you want to build?</h2>
                        <p>Describe any product, part, or object — AI will generate a 3D model you can download and 3D print.</p>
                      </div>

                      <div className="quick-start-section">
                        <span className="quick-start-label">Try one of these:</span>
                        <div className="quick-start-grid">
                          {examples.map((example, i) => (
                            <button
                              key={i}
                              className="quick-start-card"
                              onClick={() => handleBuild(example.text)}
                            >
                              <span className="qsc-emoji">{example.emoji}</span>
                              <span className="qsc-text">{example.text}</span>
                            </button>
                          ))}
                        </div>
                      </div>

                      <div className="welcome-how-it-works">
                        <div className="how-step"><span className="how-num">1</span> Type what you want</div>
                        <div className="how-arrow">→</div>
                        <div className="how-step"><span className="how-num">2</span> AI builds it</div>
                        <div className="how-arrow">→</div>
                        <div className="how-step"><span className="how-num">3</span> Download STL / STEP</div>
                      </div>
                    </div>
                  </div>
                ) : (
                  messages.map((message) => (
                    <div key={message.id} className={`message ${message.type}`}>
                      {message.type === 'user' ? (
                        <div className="message-content user-message">
                          <div className="message-text">{message.content}</div>
                        </div>
                      ) : (
                        <div className="message-content assistant-message">
                          <div className="assistant-avatar">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                              <path d="M2 17l10 5 10-5"/>
                              <path d="M2 12l10 5 10-5"/>
                            </svg>
                          </div>
                          <div className="assistant-content">
                            {/* ── Building Status ── */}
                            {message.status === 'building' && (
                              <div className="building-status">
                                <div className="build-steps-live">
                                  {(!message.steps || message.steps.length === 0) && (
                                    <div className="step-item active">
                                      <span className="step-spinner"></span>
                                      <span className="step-text">Starting build pipeline...</span>
                                    </div>
                                  )}
                                  {message.steps && message.steps
                                    .sort((a, b) => a.step - b.step)
                                    .map((s, i) => (
                                      <div key={i} className={`step-item ${s.status}`}>
                                        {s.status === 'done' && <span className="step-check">✓</span>}
                                        {s.status === 'active' && <span className="step-spinner"></span>}
                                        {s.status === 'error' && <span className="step-error">✕</span>}
                                        {s.status === 'info' && <span className="step-info-icon">ℹ</span>}
                                        <div className="step-content">
                                          <span className="step-text">{s.message}</span>
                                          {s.detail && (s.status === 'active' || s.status === 'error' || s.status === 'info') && (
                                            <span className="step-detail">{s.detail}</span>
                                          )}
                                          {s.healing?.resolved && (
                                            <span className="step-healing-badge">🛡️ Self-healed</span>
                                          )}
                                        </div>
                                      </div>
                                    ))}
                                  {/* Healing history */}
                                  {message.healingLog && message.healingLog.length > 0 && (
                                    <div className="healing-history">
                                      <details>
                                        <summary className="healing-summary">
                                          🔧 {message.healingLog.length} error{message.healingLog.length > 1 ? 's' : ''} auto-fixed
                                        </summary>
                                        <div className="healing-entries">
                                          {message.healingLog.map((entry, hi) => (
                                            <div key={hi} className="healing-entry">
                                              <span className="healing-attempt">#{entry.attempt}</span>
                                              <span className="healing-msg">{entry.message}</span>
                                            </div>
                                          ))}
                                        </div>
                                      </details>
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}

                            {/* ── Success ── */}
                            {message.status === 'success' && message.result && (
                              <div className="design-summary">
                                {message.result.explanation?.design_intent && (
                                  <div className="summary-section">
                                    <div className="summary-label">🎯 What I Built</div>
                                    <div className="summary-text">{message.result.explanation.design_intent}</div>
                                  </div>
                                )}
                                {message.result.explanation?.features_created && (
                                  <div className="summary-section">
                                    <div className="summary-label">🔩 Features & Details</div>
                                    <div className="summary-text features-list">{message.result.explanation.features_created}</div>
                                  </div>
                                )}
                                {message.result.explanation?.dimensions_summary && (
                                  <div className="summary-section">
                                    <div className="summary-label">📐 Dimensions</div>
                                    <div className="summary-text">{message.result.explanation.dimensions_summary}</div>
                                  </div>
                                )}
                                {message.result.explanation?.construction_method && (
                                  <div className="summary-section">
                                    <div className="summary-label">🏗️ How It Was Built</div>
                                    <div className="summary-text">{message.result.explanation.construction_method}</div>
                                  </div>
                                )}
                                {!message.result.explanation?.design_intent && (
                                  <div className="summary-section">
                                    <div className="summary-text">{message.result.reasoning || "Your design is ready! Check the 3D viewer."}</div>
                                  </div>
                                )}

                                {/* Inline downloads */}
                                <div className="inline-downloads">
                                  {(message.result.stlUrl || message.result.files?.stl) && (
                                    <a
                                      href={`${API_HOST}${message.result.stlUrl || message.result.files.stl}`}
                                      download
                                      className="inline-download-link"
                                    >
                                      📥 STL (3D Print)
                                    </a>
                                  )}
                                  {(message.result.stepUrl || message.result.files?.step) && (
                                    <a
                                      href={`${API_HOST}${message.result.stepUrl || message.result.files.step}`}
                                      download
                                      className="inline-download-link"
                                    >
                                      📥 STEP (CAD)
                                    </a>
                                  )}
                                  {message.result.parametricScript && (
                                    <a
                                      href={`${API_HOST}${message.result.parametricScript}`}
                                      download
                                      className="inline-download-link"
                                    >
                                      📥 Python Script
                                    </a>
                                  )}
                                </div>

                                {/* AI Suggested Improvements */}
                                {message.result.explanation?.suggested_next_steps &&
                                  message.result.explanation.suggested_next_steps.length > 0 &&
                                  status !== 'building' && (
                                    <div className="suggestions-section">
                                      <div className="suggestions-label">💡 Want me to improve it?</div>
                                      <div className="suggestions-list">
                                        {message.result.explanation.suggested_next_steps.map((suggestion, si) => (
                                          <button
                                            key={si}
                                            className="suggestion-chip"
                                            onClick={() => handleBuild(suggestion)}
                                            disabled={status === 'building'}
                                          >
                                            <span className="suggestion-text">{suggestion}</span>
                                            <span className="suggestion-add">+ Add</span>
                                          </button>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                              </div>
                            )}

                            {/* ── Error ── */}
                            {message.status === 'error' && (
                              <div className="error-message">
                                <div className="error-icon">⚠️</div>
                                <div className="error-body">
                                  <div className="error-title">Something went wrong</div>
                                  <div className="error-detail">{message.content}</div>
                                  <button
                                    className="retry-button"
                                    onClick={() => {
                                      const lastUserMsg = messages.filter(m => m.type === 'user').pop();
                                      if (lastUserMsg) handleBuild(lastUserMsg.content);
                                    }}
                                  >
                                    🔄 Try Again
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  ))
                )}

                {/* Scroll-to-bottom indicator */}
                {!isAtBottom && messages.length > 0 && (
                  <button
                    className="scroll-to-bottom"
                    onClick={() => {
                      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
                      setIsAtBottom(true);
                    }}
                  >
                    ↓ New messages
                  </button>
                )}
                <div ref={messagesEndRef} />
              </div>

              <PromptInput
                onBuild={handleBuild}
                isBuilding={status === 'building'}
                hasExistingDesign={currentDesign !== null}
                uploadedFile={uploadedFile}
              />

              {/* ── File Upload ── */}
              <FileUpload
                onUploadComplete={handleUploadComplete}
                onUploadStart={(filename) => {
                  dispatch({
                    type: 'ADD_MESSAGE',
                    payload: {
                      id: Date.now(),
                      type: 'assistant',
                      status: 'success',
                      content: `Uploading ${filename}...`,
                      timestamp: new Date(),
                    },
                  });
                }}
                disabled={status === 'building'}
              />
            </>
          )}
        </div>

        {/* ──── Resize Handle ──── */}
        {!isMobile && !chatCollapsed && !previewCollapsed && (
          <div
            className={`resize-handle ${isDragging ? 'dragging' : ''}`}
            onMouseDown={handleMouseDown}
          >
            <div className="resize-handle-bar"></div>
          </div>
        )}

        {/* ──── Preview Panel ──── */}
        <div className={`preview-panel ${previewCollapsed ? 'collapsed' : ''} ${isMobile && activeTab !== 'preview' ? 'mobile-hidden' : ''}`}>
          {previewCollapsed ? (
            <button
              className="panel-expand-btn"
              onClick={() => dispatch({ type: 'TOGGLE_PREVIEW_COLLAPSED' })}
              title="Expand preview"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="15 18 9 12 15 6"/>
              </svg>
              <span className="panel-expand-label">👁️</span>
            </button>
          ) : (
            <>
              <div className="preview-header">
                <div className="preview-header-left">
                  {!isMobile && (
                    <button
                      className="panel-collapse-btn"
                      onClick={() => dispatch({ type: 'TOGGLE_PREVIEW_COLLAPSED' })}
                      title="Collapse preview panel"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="9 18 15 12 9 6"/>
                      </svg>
                    </button>
                  )}
                  <span>👁️ 3D Preview</span>
                </div>
                <div className="preview-header-right">
                  {parameters && parameters.length > 0 && (
                    <button
                      className={`view-mode-toggle ${showParameterPanel ? 'active' : ''}`}
                      onClick={() => dispatch({ type: 'TOGGLE_PARAMETER_PANEL' })}
                      title="Toggle parameter sliders"
                    >
                      🎛️ Parameters
                    </button>
                  )}
                  <span className="preview-status">
                    {sceneProducts.length === 0
                      ? 'Waiting for first design...'
                      : `● ${sceneProducts.length} ${sceneProducts.length === 1 ? 'product' : 'products'}`}
                  </span>
                </div>
              </div>

              <div className="preview-body">
                <div className="canvas-area">
                  {sceneProducts.length === 0 && status !== 'building' ? (
                    <div className="empty-canvas">
                      <div className="empty-canvas-icon">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round">
                          <path d="M12 2L2 7l10 5 10-5-10-5z" opacity="0.3"/>
                          <path d="M2 17l10 5 10-5" opacity="0.2"/>
                          <path d="M2 12l10 5 10-5" opacity="0.25"/>
                        </svg>
                      </div>
                      <p className="empty-canvas-text">Your 3D model will appear here</p>
                      <p className="empty-canvas-hint">Type a description in the chat to get started</p>
                    </div>
                  ) : (
                    <MultiProductCanvas
                      sceneId={currentScene?.sceneId}
                      initialProducts={sceneProducts}
                    />
                  )}
                  {status === 'building' && sceneProducts.length === 0 && (
                    <div className="canvas-loading">
                      <div className="canvas-loading-cube">
                        <div className="cube-face front"></div>
                        <div className="cube-face back"></div>
                        <div className="cube-face right"></div>
                        <div className="cube-face left"></div>
                        <div className="cube-face top"></div>
                        <div className="cube-face bottom"></div>
                      </div>
                      <p>Generating 3D model...</p>
                    </div>
                  )}
                </div>

                {/* ── Parameter Sliders ── */}
                {showParameterPanel && parameters && parameters.length > 0 && (
                  <div className="parameter-panel-wrapper">
                    <ParameterPanel
                      parameters={parameters}
                      buildId={currentBuildId}
                      onUpdate={handleRebuild}
                    />
                  </div>
                )}

                {/* ── Export Panel (compact) ── */}
                {hasDesign && result && (
                  <div className="export-panel-wrapper">
                    <ExportPanel
                      buildId={result.buildId}
                      stlUrl={result.stlUrl || result.files?.stl}
                      stepUrl={result.stepUrl || result.files?.step}
                      parametricScript={result.parametricScript}
                      onShare={(buildId) => uploadToS3(buildId)}
                    />
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </main>

      {showProjectBrowser && (
        <ProjectBrowser
          onSelectProject={handleProjectSelect}
          onClose={() => dispatch({ type: 'SET_SHOW_PROJECT_BROWSER', payload: false })}
          onNewProject={handleNewProject}
        />
      )}
    </div>
  );
}

export default App;
