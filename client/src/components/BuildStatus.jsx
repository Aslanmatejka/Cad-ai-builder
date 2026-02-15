import React from 'react';
import './BuildStatus.css';
import './AssemblyStyles.css';

function BuildStatus({ status, error, result, buildSteps }) {
  if (status === 'idle') return null;

  const designSource = result?.design || result?.designData || {};
  const units = designSource.units || 'mm';
  const features = Array.isArray(designSource.features) ? designSource.features : [];
  const cutouts = Array.isArray(designSource.cutouts) ? designSource.cutouts : [];
  const defaultModelName = process.env.REACT_APP_AI_MODEL_NAME || 'Claude Sonnet 4.5';
  const aiModelName = result?.aiModel || defaultModelName;
  const productType = designSource.product_type || 'Custom product';
  const dimensionLength = designSource.length ?? '—';
  const dimensionWidth = designSource.width ?? '—';
  const dimensionHeight = designSource.height ?? '—';
  const wallThickness = designSource.wall_thickness ?? '—';
  const material = designSource.material || 'Not specified';
  const steps = buildSteps || [];

  return (
    <div className="build-status">
      {status === 'building' && (
        <div className="status-building">
          <h3>🏭 Building Your Product</h3>
          <div className="build-steps-live">
            {steps.length === 0 && (
              <div className="step-item active">
                <span className="step-spinner"></span>
                <span className="step-text">Starting build pipeline...</span>
              </div>
            )}
            {steps
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
          </div>
        </div>
      )}

      {status === 'success' && result && (
        <div className="status-success">
          <h3>✅ Build Complete!</h3>
          <div className="build-details">
            <div className="design-summary">
              <h4>📋 Design Summary:</h4>
              <table>
                <tbody>
                  <tr>
                    <td><strong>Product Type:</strong></td>
                    <td>{productType}</td>
                  </tr>
                  <tr>
                    <td><strong>AI Model:</strong></td>
                    <td>
                      <span className="ai-model-highlight">{aiModelName}</span>
                    </td>
                  </tr>
                  <tr>
                    <td><strong>Dimensions:</strong></td>
                    <td>{dimensionLength} × {dimensionWidth} × {dimensionHeight} {units}</td>
                  </tr>
                  <tr>
                    <td><strong>Wall Thickness:</strong></td>
                    <td>{wallThickness} {units}</td>
                  </tr>
                  <tr>
                    <td><strong>Material:</strong></td>
                    <td>{material}</td>
                  </tr>
                  {features.length > 0 && (
                    <tr>
                      <td><strong>Features:</strong></td>
                      <td>{features.join(', ')}</td>
                    </tr>
                  )}
                  {cutouts.length > 0 && (
                    <tr>
                      <td><strong>Cutouts:</strong></td>
                      <td>{cutouts.length} cutout(s) ({cutouts.map(c => c.type).join(', ')})</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            
            {result.feedback && (result.feedback.compatibility?.length > 0 || result.feedback.engine?.length > 0) && (
              <div className="feedback-section">
                <h4>💡 Build Insights:</h4>
                {result.feedback.compatibility && result.feedback.compatibility.length > 0 && (
                  <div className="compatibility-feedback">
                    <strong>⚙️ Compatibility Notes:</strong>
                    <ul>
                      {result.feedback.compatibility.map((note, i) => (
                        <li key={i}>{note}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {result.feedback.engine && result.feedback.engine.length > 0 && (
                  <div className="engine-feedback">
                    <strong>🔧 Engine Feedback:</strong>
                    <ul>
                      {result.feedback.engine.map((note, i) => (
                        <li key={i}>{note}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
            
            {result.printSettings && Object.keys(result.printSettings).length > 0 && (
              <div className="print-settings-section">
                <h4>🖨️ Print-Ready Information:</h4>
                <div className="print-status">
                  {result.printSettings.isManifold && (
                    <div className="status-badge success">
                      ✓ Watertight Geometry - Ready to Slice
                    </div>
                  )}
                  {result.printSettings.needsSupports === false && (
                    <div className="status-badge success">
                      ✓ No Supports Needed
                    </div>
                  )}
                  {result.printSettings.needsSupports === true && (
                    <div className="status-badge warning">
                      ⚠ Supports Required
                    </div>
                  )}
                </div>
                
                {(result.printSettings.Material || result.printSettings['Layer Height']) && (
                  <div className="print-settings-table">
                    <strong>Recommended Slicer Settings:</strong>
                    <table>
                      <tbody>
                        {result.printSettings.Material && (
                          <tr>
                            <td>Material:</td>
                            <td>{result.printSettings.Material}</td>
                          </tr>
                        )}
                        {result.printSettings['Layer Height'] && (
                          <tr>
                            <td>Layer Height:</td>
                            <td>{result.printSettings['Layer Height']}</td>
                          </tr>
                        )}
                        {result.printSettings.Infill && (
                          <tr>
                            <td>Infill:</td>
                            <td>{result.printSettings.Infill}</td>
                          </tr>
                        )}
                        {result.printSettings.Walls && (
                          <tr>
                            <td>Wall Lines:</td>
                            <td>{result.printSettings.Walls}</td>
                          </tr>
                        )}
                        {result.printSettings['Print Speed'] && (
                          <tr>
                            <td>Print Speed:</td>
                            <td>{result.printSettings['Print Speed']}</td>
                          </tr>
                        )}
                        {result.printSettings['Bed Adhesion'] && (
                          <tr>
                            <td>Bed Adhesion:</td>
                            <td>{result.printSettings['Bed Adhesion']}</td>
                          </tr>
                        )}
                        {result.printSettings['Estimated Print Time'] && (
                          <tr>
                            <td>Est. Time:</td>
                            <td>{result.printSettings['Estimated Print Time']}</td>
                          </tr>
                        )}
                        {result.printSettings['Estimated Material'] && (
                          <tr>
                            <td>Est. Material:</td>
                            <td>{result.printSettings['Estimated Material']}</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
            
            {result.isAssembly && result.assemblyInfo && (
              <div className="assembly-section">
                <h4>🔧 Assembly Information:</h4>
                <div className="assembly-overview">
                  <div className="assembly-stat">
                    <strong>{result.assemblyInfo.totalParts}</strong>
                    <span>Parts to Print</span>
                  </div>
                  {result.assemblyInfo.totalPrintTime > 0 && (
                    <div className="assembly-stat">
                      <strong>~{result.assemblyInfo.totalPrintTime}h</strong>
                      <span>Total Print Time</span>
                    </div>
                  )}
                  {result.assemblyInfo.assemblyTime > 0 && (
                    <div className="assembly-stat">
                      <strong>{result.assemblyInfo.assemblyTime}min</strong>
                      <span>Assembly Time</span>
                    </div>
                  )}
                </div>
                
                {result.assemblyInfo.hardware && result.assemblyInfo.hardware.length > 0 && (
                  <div className="hardware-list">
                    <strong>🔩 Required Hardware:</strong>
                    <ul>
                      {result.assemblyInfo.hardware.map((hw, i) => (
                        <li key={i}>
                          {hw.quantity}x {hw.type} ({hw.size}) - {hw.purpose}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {result.assemblyInfo.toolsRequired && result.assemblyInfo.toolsRequired.length > 0 && (
                  <div className="tools-list">
                    <strong>🛠️ Tools Needed:</strong>
                    <div className="tools-badges">
                      {result.assemblyInfo.toolsRequired.map((tool, i) => (
                        <span key={i} className="tool-badge">{tool.replace(/_/g, ' ')}</span>
                      ))}
                    </div>
                  </div>
                )}
                
                {result.assemblyInfo.assemblySteps && result.assemblyInfo.assemblySteps.length > 0 && (
                  <div className="assembly-instructions">
                    <strong>📋 Assembly Steps:</strong>
                    <ol>
                      {result.assemblyInfo.assemblySteps.map((step, i) => (
                        <li key={i}>{step}</li>
                      ))}
                    </ol>
                  </div>
                )}
              </div>
            )}
            
            <h4>💾 Download Files:</h4>
            <ul className="file-list">
              {result.isAssembly && Array.isArray(result.files) ? (
                result.files.map((part, idx) => (
                  <li key={idx} className="assembly-part">
                    <div className="part-header">
                      <strong>Part {part.partNumber}: {part.partName}</strong>
                      {part.quantity > 1 && <span className="quantity-badge">Print {part.quantity}x</span>}
                      <span className="material-badge">{part.material}</span>
                    </div>
                    <div className="part-files">
                      {part.files.map((file, fileIdx) => {
                        const fileName = file.split('/').pop();
                        const isSTL = fileName.endsWith('.stl');
                        return (
                          <a key={fileIdx} href={`http://localhost:3001/exports/cad/${fileName}`} download>
                            {isSTL ? '🔺' : '📦'} {fileName}
                            <span className="file-type"> - {isSTL ? '3D Print' : 'CAD Edit'}</span>
                          </a>
                        );
                      })}
                    </div>
                  </li>
                ))
              ) : (
                <>
                  {result.files && result.files.stl && (
                    <li>
                      <a href={`http://localhost:3001${result.files.stl}`} download>
                        🔺 {result.files.stl.split('/').pop()}
                      </a>
                      <span className="file-type"> - 3D Print Ready</span>
                    </li>
                  )}
                  {result.files && result.files.step && (
                    <li>
                      <a href={`http://localhost:3001${result.files.step}`} download>
                        📦 {result.files.step.split('/').pop()}
                      </a>
                      <span className="file-type"> - CAD Editable</span>
                    </li>
                  )}
                </>
              )}
            </ul>
          </div>
        </div>
      )}

      {status === 'error' && (
        <div className="status-error">
          <h3>❌ Build Failed</h3>
          <p className="error-message">{error}</p>
          <p className="error-help">💡 Tip: Try being more specific about dimensions and features, or check the console for details.</p>
        </div>
      )}
    </div>
  );
}

export default BuildStatus;
