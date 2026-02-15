import React, { useState, useRef, useEffect } from 'react';
import PromptInput from './components/PromptInput';
import MultiProductCanvas from './components/MultiProductCanvas';
import ProjectBrowser from './components/ProjectBrowser';
import { buildProduct, buildProductStream, uploadToS3, getProject, saveMessage } from './api';
import './App.css';

function App() {
  const [status, setStatus] = useState('idle');
  const [result, setResult] = useState(null);
  const [messages, setMessages] = useState([]);
  const [currentDesign, setCurrentDesign] = useState(null);
  const [chatWidth, setChatWidth] = useState(50); // percentage
  const [isDragging, setIsDragging] = useState(false);
  const [currentScene, setCurrentScene] = useState(null);
  const [sceneProducts, setSceneProducts] = useState([]);
  const [showProjectBrowser, setShowProjectBrowser] = useState(false);
  // Parameters stored in currentDesign — AI handles all modifications via chat
  const [currentBuildId, setCurrentBuildId] = useState(null);
  const [currentProjectId, setCurrentProjectId] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleMouseDown = (e) => {
    setIsDragging(true);
    e.preventDefault();
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    
    const windowWidth = window.innerWidth;
    const newWidth = (e.clientX / windowWidth) * 100;
    
    // Constrain between 20% and 80%
    if (newWidth >= 20 && newWidth <= 80) {
      setChatWidth(newWidth);
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging]);

  // Initialize scene on mount
  useEffect(() => {
    if (!currentScene) {
      initializeScene();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const initializeScene = async () => {
    try {
      const response = await fetch('http://localhost:3001/api/scene/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'Workspace ' + new Date().toLocaleDateString() })
      });
      const data = await response.json();
      if (data.success) {
        setCurrentScene(data.scene);
        console.log('✅ Scene created:', data.scene);
      }
    } catch (error) {
      console.error('❌ Scene initialization failed:', error);
    }
  };

  const addProductToScene = async (buildResult, isModification = false) => {
    // If no scene exists yet, create one first
    if (!currentScene) {
      console.log('⚠️ No scene exists, creating one first...');
      try {
        const response = await fetch('http://localhost:3001/api/scene/create', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: 'Workspace ' + new Date().toLocaleDateString() })
        });
        const data = await response.json();
        if (data.success) {
          setCurrentScene(data.scene);
          console.log('✅ Scene created:', data.scene);
          // Now add the product using the newly created scene
          return await addProductToSceneInternal(buildResult, data.scene, isModification);
        }
      } catch (error) {
        console.error('❌ Scene creation failed:', error);
        return;
      }
    }

    return await addProductToSceneInternal(buildResult, currentScene, isModification);
  };

  const addProductToSceneInternal = async (buildResult, scene, isModification = false) => {
    try {
      console.log('📦 Build result received:', buildResult);
      console.log(`${isModification ? '🔧 Modification mode — will REPLACE existing product' : '🆕 New product — will ADD to scene'}`);
      
      // Handle assembly parts - add all parts to scene
      if (buildResult.isAssembly && Array.isArray(buildResult.files) && buildResult.files.length > 1) {
        console.log(`🔧 Assembly detected with ${buildResult.files.length} parts`);
        
        const addedProducts = [];
        for (let i = 0; i < buildResult.files.length; i++) {
          const part = buildResult.files[i];
          let stlFile = null;
          
          // Extract STL from part.files (object or array format)
          if (part.files) {
            if (typeof part.files === 'object' && !Array.isArray(part.files) && part.files.stl) {
              stlFile = part.files.stl;
            } else if (Array.isArray(part.files)) {
              stlFile = part.files.find(f => f.endsWith('.stl'));
            }
          }
          
          if (!stlFile) {
            console.warn(`⚠️ No STL found for part ${i + 1}: ${part.partName}`);
            continue;
          }
          
          const stlPath = stlFile.startsWith('/') ? stlFile : `/exports/cad/${stlFile}`;
          console.log(`📂 Part ${i + 1}/${buildResult.files.length} - ${part.partName}: ${stlPath}`);
          
          // Add each part as separate product to scene
          const response = await fetch(`http://localhost:3001/api/scene/${scene.sceneId}/add-product`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              buildId: buildResult.buildId + `_part${i + 1}`,
              instanceName: part.partName || `Part ${i + 1}`,
              position: { x: i * 50, y: 0, z: 0 }, // Space parts 50mm apart
              rotation: { x: 0, y: 0, z: 0 },
              scale: { x: 1, y: 1, z: 1 }
            })
          });
          
          const data = await response.json();
          if (data.success) {
            const newProduct = {
              instanceId: data.product.instanceId,
              buildId: buildResult.buildId + `_part${i + 1}`,
              instanceName: part.partName || `Part ${i + 1}`,
              position: data.product.position,
              rotation: data.product.rotation,
              scale: data.product.scale,
              stlUrl: `http://localhost:3001${stlPath}`,
              productType: part.partName,
              designData: buildResult.design
            };
            addedProducts.push(newProduct);
            console.log(`✅ Added part ${i + 1}: ${part.partName}`);
          }
        }
        
        // Update scene products with all assembly parts
        if (addedProducts.length > 0) {
          if (isModification) {
            // Replace all existing products with the new assembly parts
            console.log('🔧 Replacing existing products with modified assembly parts');
            setSceneProducts(addedProducts);
          } else {
            setSceneProducts(prev => [...prev, ...addedProducts]);
          }
          console.log(`✅ ${isModification ? 'Replaced with' : 'Added'} ${addedProducts.length} parts to scene`);
        }
        return;
      }
      
      // Single-part design - original logic
      let stlFile = null;
      
      // Check buildResult.files.cad structure (orchestrator returns this)
      if (buildResult.files?.cad?.files) {
        const cadFiles = buildResult.files.cad.files;
        if (typeof cadFiles === 'string') {
          stlFile = cadFiles.endsWith('.stl') ? cadFiles : null;
        } else if (typeof cadFiles === 'object' && cadFiles.stl) {
          stlFile = cadFiles.stl;
        } else if (Array.isArray(cadFiles)) {
          stlFile = cadFiles.find(f => f.endsWith('.stl'));
        }
      }
      
      // Fallback to legacy structure
      if (!stlFile && buildResult.files?.stl) {
        stlFile = buildResult.files.stl;
      } else if (!stlFile && buildResult.files && Array.isArray(buildResult.files)) {
        const firstPart = buildResult.files[0];
        if (firstPart?.files) {
          if (typeof firstPart.files === 'object' && !Array.isArray(firstPart.files) && firstPart.files.stl) {
            stlFile = firstPart.files.stl;
          } else if (Array.isArray(firstPart.files)) {
            stlFile = firstPart.files.find(f => f.endsWith('.stl'));
          }
        }
      }
      
      // Fallback to top-level stlUrl from /api/build response
      if (!stlFile && buildResult.stlUrl) {
        stlFile = buildResult.stlUrl;
      }
      
      if (!stlFile) {
        console.warn('⚠️ No STL file found in build result');
        console.log('Build result structure:', JSON.stringify(buildResult, null, 2));
        return;
      }
      
      const stlPath = stlFile.startsWith('/') ? stlFile : `/exports/cad/${stlFile}`;
      console.log('📂 STL path:', stlPath);

      // When modifying, keep the same position as the product being replaced
      let productPosition = { x: 0, y: 0, z: 0 };
      if (isModification && sceneProducts.length > 0) {
        const lastProduct = sceneProducts[sceneProducts.length - 1];
        productPosition = lastProduct.position || { x: 0, y: 0, z: 0 };
      } else if (!isModification) {
        productPosition = { x: sceneProducts.length * 100, y: 0, z: 0 };
      }

      const response = await fetch(`http://localhost:3001/api/scene/${scene.sceneId}/add-product`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          buildId: buildResult.buildId,
          instanceName: buildResult.design?.product_type || 'Product',
          position: productPosition,
          rotation: { x: 0, y: 0, z: 0 },
          scale: { x: 1, y: 1, z: 1 }
        })
      });

      const data = await response.json();
      console.log('📡 Add product response:', data);
      
      if (data.success) {
        const newProduct = {
          instanceId: data.product.instanceId,
          buildId: buildResult.buildId,
          instanceName: data.product.instanceName,
          position: data.product.position,
          rotation: data.product.rotation,
          scale: data.product.scale,
          stlUrl: `http://localhost:3001${stlPath}`,
          productType: buildResult.design?.product_type,
          designData: buildResult.design
        };
        
        if (isModification) {
          // REPLACE the last product in the scene (the one being modified)
          console.log('🔧 Replacing existing product in scene with modified version');
          setSceneProducts(prev => {
            if (prev.length === 0) return [newProduct];
            // Replace the last product (most recently built = the one being modified)
            const updated = [...prev.slice(0, -1), newProduct];
            console.log('📊 Updated scene products (replaced):', updated);
            return updated;
          });
        } else {
          // ADD new product to scene
          console.log('✅ Adding new product to scene:', newProduct);
          setSceneProducts(prev => {
            const updated = [...prev, newProduct];
            console.log('📊 Updated scene products (added):', updated);
            return updated;
          });
        }
      } else {
        console.error('❌ Failed to add product to scene:', data.error);
      }
    } catch (error) {
      console.error('❌ Add to scene failed:', error);
    }
  };

  const handleProjectSelect = async (project) => {
    // Load project from MySQL
    try {
      const data = await getProject(project.id);
      if (!data.success || !data.project) {
        console.error('❌ Failed to load project');
        return;
      }

      const proj = data.project;
      setCurrentProjectId(proj.id);

      // Restore chat messages
      if (proj.messages && proj.messages.length > 0) {
        const restoredMessages = proj.messages.map((msg, idx) => ({
          id: Date.now() + idx,
          type: msg.role,
          content: msg.content,
          status: msg.status || (msg.role === 'assistant' ? 'success' : undefined),
          result: msg.build_result || undefined,
          timestamp: new Date(msg.created_at)
        }));
        setMessages(restoredMessages);
      } else {
        setMessages([]);
      }

      // Restore the latest build's design for modification flow
      if (proj.builds && proj.builds.length > 0) {
        const lastBuild = proj.builds[proj.builds.length - 1];
        setCurrentDesign({
          code: lastBuild.code,
          parameters: lastBuild.parameters,
          explanation: lastBuild.explanation,
        });
        setCurrentBuildId(lastBuild.build_id);

        // Load the STL into the 3D viewer
        if (lastBuild.stl_path) {
          // Add to scene
          const buildResult = {
            buildId: lastBuild.build_id,
            stlUrl: lastBuild.stl_path,
            design: {
              code: lastBuild.code,
              parameters: lastBuild.parameters,
              explanation: lastBuild.explanation,
            }
          };
          await addProductToScene(buildResult);
        }
      } else {
        setCurrentDesign(null);
        setCurrentBuildId(null);
      }

      console.log('✅ Project loaded:', proj.name);
    } catch (error) {
      console.error('❌ Failed to load project:', error);
    }
  };

  const handleNewProject = () => {
    setShowProjectBrowser(false);
    setMessages([]);
    setCurrentDesign(null);
    setCurrentProjectId(null);
    setCurrentBuildId(null);
    setResult(null);
    setStatus('idle');
    setSceneProducts([]);
    // Reinitialize scene so next build has a valid sceneId
    setCurrentScene(null);
    initializeScene();
  };

  const handleBuild = async (prompt) => {
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: prompt,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMessage]);

    setStatus('building');

    const isModification = currentDesign && currentDesign.code;
    const buildingMessage = {
      id: Date.now() + 1,
      type: 'assistant',
      status: 'building',
      content: isModification 
        ? '🔧 Got it! Modifying your existing design...' 
        : 'Got it! Let me design that for you...',
      steps: [],
      timestamp: new Date()
    };
    setMessages(prev => [...prev, buildingMessage]);

    try {
      const buildResult = await buildProductStream(prompt, currentDesign, (stepData) => {
        // Update the building message in chat with live step progress
        setMessages(prev => prev.map((msg, idx) => {
          if (idx !== prev.length - 1 || msg.status !== 'building') return msg;

          // Accumulate healing history (errors + fix attempts on step 4)
          let healingLog = msg.healingLog || [];
          if (stepData.step === 4 && stepData.status === 'error') {
            healingLog = [...healingLog, { message: stepData.message, detail: stepData.detail, attempt: stepData.healing?.attempt || 0 }];
          }

          return {
            ...msg,
            steps: [...(msg.steps || []).filter(s => s.step !== stepData.step), stepData],
            healingLog,
          };
        }));
      }, currentProjectId);

      setResult(buildResult);
      setCurrentDesign(buildResult.design);
      setStatus('success');
      
      // Store buildId and projectId for future builds
      if (buildResult.buildId) {
        setCurrentBuildId(buildResult.buildId);
      }
      if (buildResult.projectId) {
        setCurrentProjectId(buildResult.projectId);
      }

      // Save chat messages to DB (fire-and-forget)
      if (buildResult.projectId) {
        try {
          await saveMessage(buildResult.projectId, 'user', prompt);
          await saveMessage(
            buildResult.projectId, 'assistant',
            buildResult.explanation?.design_intent || 'Design created',
            buildResult, 'success'
          );
        } catch (msgErr) {
          console.warn('⚠️ Failed to save chat messages:', msgErr);
        }
      }

      setMessages(prev => prev.map((msg, idx) => 
        idx === prev.length - 1 
          ? { 
              ...msg, 
              status: 'success', 
              content: buildResult.reasoning || "Here's your design!", 
              result: buildResult 
            }
          : msg
      ));

      await addProductToScene(buildResult, isModification);
    } catch (err) {
      setStatus('error');

      setMessages(prev => prev.map((msg, idx) => 
        idx === prev.length - 1 
          ? { ...msg, status: 'error', content: err.message }
          : msg
      ));
    }
  };

  const handleShareToS3 = async () => {
    if (!currentBuildId) {
      return;
    }
    
    try {
      const shareResult = await uploadToS3(currentBuildId);
      const shareUrl = shareResult.shareUrl;
      navigator.clipboard.writeText(shareUrl);
      
      setMessages(prev => [...prev, {
        id: Date.now(),
        type: 'assistant',
        status: 'success',
        content: `✅ Share link copied to clipboard!\n${shareUrl}`,
        timestamp: new Date()
      }]);
    } catch (error) {
      console.error('S3 upload failed:', error);
      setMessages(prev => [...prev, {
        id: Date.now(),
        type: 'assistant',
        status: 'error',
        content: `Couldn't generate share link: ${error.message}`,
        timestamp: new Date()
      }]);
    }
  };

  return (
    <div className="App">
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
        <div className="header-right">
          <button 
            className="projects-btn"
            onClick={() => setShowProjectBrowser(true)}
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
                  href={`http://localhost:3001${result.stlUrl || result.files.stl}`} 
                  download
                  className="export-btn"
                  title="Download for 3D printing"
                >
                  🖨️ Download STL
                </a>
              )}
              {(result.stepUrl || result.files?.step) && (
                <a 
                  href={`http://localhost:3001${result.stepUrl || result.files.step}`} 
                  download
                  className="export-btn"
                  title="Open in FreeCAD or Fusion 360 to edit further"
                >
                  ✏️ Download STEP
                </a>
              )}
            </div>
          )}
        </div>
      </header>

      <main style={{ gridTemplateColumns: `${chatWidth}% 8px ${100 - chatWidth}%` }}>
        <div className="chat-container">
          <div className="chat-messages">
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
                      {[
                        { emoji: '📱', text: 'iPhone 15 Pro case with camera cutout and charging port', category: 'Everyday' },
                        { emoji: '🎮', text: 'Game controller grip with ergonomic curves', category: 'Gaming' },
                        { emoji: '⚙️', text: 'Raspberry Pi 4 case with ventilation slots and mounting holes', category: 'Tech' },
                        { emoji: '🏠', text: 'Desk organizer with pen holder and phone stand', category: 'Home' },
                        { emoji: '🔧', text: 'Adjustable wrench 150mm with textured handle', category: 'Tools' },
                        { emoji: '☕', text: 'Travel mug with threaded lid and grip texture', category: 'Kitchen' },
                      ].map((example, i) => (
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
                              {/* Healing history log — shows collapsed past errors during self-healing */}
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
                        {message.status === 'success' && message.result && (
                          <div className="design-summary">
                            {/* Design Intent */}
                            {message.result.explanation?.design_intent && (
                              <div className="summary-section">
                                <div className="summary-label">🎯 What I Built</div>
                                <div className="summary-text">{message.result.explanation.design_intent}</div>
                              </div>
                            )}

                            {/* Features Created */}
                            {message.result.explanation?.features_created && (
                              <div className="summary-section">
                                <div className="summary-label">🔩 Features & Details</div>
                                <div className="summary-text features-list">{message.result.explanation.features_created}</div>
                              </div>
                            )}

                            {/* Dimensions */}
                            {message.result.explanation?.dimensions_summary && (
                              <div className="summary-section">
                                <div className="summary-label">📐 Dimensions</div>
                                <div className="summary-text">{message.result.explanation.dimensions_summary}</div>
                              </div>
                            )}

                            {/* Construction Method */}
                            {message.result.explanation?.construction_method && (
                              <div className="summary-section">
                                <div className="summary-label">🏗️ How It Was Built</div>
                                <div className="summary-text">{message.result.explanation.construction_method}</div>
                              </div>
                            )}

                            {/* What You Can Modify — replaced by suggestions */}

                            {/* Fallback if no explanation fields */}
                            {!message.result.explanation?.design_intent && (
                              <div className="summary-section">
                                <div className="summary-text">{message.result.reasoning || "Your design is ready! Check the 3D viewer on the right."}</div>
                              </div>
                            )}

                            {/* Download links */}
                            <div className="inline-downloads">
                              {(message.result.stlUrl || message.result.files?.stl) && (
                                <a 
                                  href={`http://localhost:3001${message.result.stlUrl || message.result.files.stl}`}
                                  download
                                  className="inline-download-link"
                                >
                                  📥 STL (3D Print)
                                </a>
                              )}
                              {(message.result.stepUrl || message.result.files?.step) && (
                                <a 
                                  href={`http://localhost:3001${message.result.stepUrl || message.result.files.step}`}
                                  download
                                  className="inline-download-link"
                                >
                                  📥 STEP (CAD)
                                </a>
                              )}
                              {message.result.parametricScript && (
                                <a 
                                  href={`http://localhost:3001${message.result.parametricScript}`}
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
            <div ref={messagesEndRef} />
          </div>
          
          <PromptInput 
            onBuild={handleBuild} 
            isBuilding={status === 'building'}
            hasExistingDesign={currentDesign !== null}
          />
        </div>

        <div 
          className={`resize-handle ${isDragging ? 'dragging' : ''}`}
          onMouseDown={handleMouseDown}
        >
          <div className="resize-handle-bar"></div>
        </div>

        <div className="preview-panel">
          <div className="preview-header">
            <span>👁️ 3D Preview</span>
            <span className="preview-status">
              {sceneProducts.length === 0 
                ? 'Waiting for your first design...' 
                : `● ${sceneProducts.length} ${sceneProducts.length === 1 ? 'product' : 'products'} in scene`
              }
            </span>
          </div>
          
          <MultiProductCanvas
            sceneId={currentScene?.sceneId}
            initialProducts={sceneProducts}
          />
        </div>
      </main>

      {showProjectBrowser && (
        <ProjectBrowser
          onSelectProject={handleProjectSelect}
          onClose={() => setShowProjectBrowser(false)}
          onNewProject={handleNewProject}
        />
      )}
    </div>
  );
}

export default App;
