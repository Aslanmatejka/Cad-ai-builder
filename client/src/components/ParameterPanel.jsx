import React, { useState, useEffect } from 'react';
import './ParameterPanel.css';

/**
 * Phase 4: Dynamic Parameter Panel with Range Sliders
 * Parses parameters from AI response and generates interactive controls
 * Re-runs CadQuery script locally without AI when values change
 */

// Convert snake_case param names to readable labels
function humanize(name) {
  return name
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\b\w/g, c => c.toUpperCase());
}

function ParameterPanel({ parameters, buildId, onParameterChange, onUpdate }) {
  const [paramValues, setParamValues] = useState({});
  const [isUpdating, setIsUpdating] = useState(false);
  const [defaults, setDefaults] = useState({});

  // Initialize parameter values from defaults
  useEffect(() => {
    if (parameters && parameters.length > 0) {
      const initialValues = {};
      parameters.forEach(param => {
        initialValues[param.name] = param.default;
      });
      setParamValues(initialValues);
      setDefaults(initialValues);
    }
  }, [parameters]);

  const handleSliderChange = (paramName, newValue) => {
    const updatedValues = {
      ...paramValues,
      [paramName]: parseFloat(newValue)
    };
    setParamValues(updatedValues);
    if (onParameterChange) {
      onParameterChange(updatedValues);
    }
  };

  const handleReset = () => {
    setParamValues({ ...defaults });
    if (onParameterChange) {
      onParameterChange({ ...defaults });
    }
  };

  const handleUpdate = async () => {
    setIsUpdating(true);
    try {
      if (onUpdate) {
        await onUpdate(paramValues);
      }
    } catch (error) {
      console.error('Update failed:', error);
    } finally {
      setIsUpdating(false);
    }
  };

  if (!parameters || parameters.length === 0) {
    return null;
  }

  return (
    <div className="parameter-panel">
      <div className="parameter-panel-header">
        <h3>🎛️ Adjust Dimensions</h3>
        <button className="reset-params-btn" onClick={handleReset} title="Reset all to defaults">↩ Reset</button>
      </div>
      
      <div className="parameter-list">
        {parameters.map((param, index) => {
          const isChanged = paramValues[param.name] !== defaults[param.name];
          return (
            <div key={index} className={`parameter-item ${isChanged ? 'changed' : ''}`}>
              <div className="parameter-label">
                <span className="parameter-name" title={param.name}>{humanize(param.name)}</span>
                <span className="parameter-value">
                  {paramValues[param.name]?.toFixed(1)}
                  <span className="param-unit">{param.unit || 'mm'}</span>
                </span>
              </div>
              
              <input
                type="range"
                className="parameter-slider"
                min={param.min || 0}
                max={param.max || 100}
                step={param.step || 0.5}
                value={paramValues[param.name] || param.default}
                onChange={(e) => handleSliderChange(param.name, e.target.value)}
              />
              
              <div className="parameter-range">
                <span className="range-min">{param.min || 0}</span>
                <span className="range-max">{param.max || 100}</span>
              </div>
            </div>
          );
        })}
      </div>

      <button 
        className="update-button"
        onClick={handleUpdate}
        disabled={isUpdating}
      >
        {isUpdating ? (
          <>
            <span className="spinner"></span>
            Updating...
          </>
        ) : (
          '⚡ Update 3D Model'
        )}
      </button>

      <div className="parameter-info">
        Drag sliders, then click Update to regenerate.
      </div>
    </div>
  );
}

export default ParameterPanel;
