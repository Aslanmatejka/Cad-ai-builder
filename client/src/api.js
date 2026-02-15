/**
 * API Client - Handles communication with Product Builder backend
 */

// Always use direct connection to backend on port 3001
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3001/api';

export async function chatWithEngineer(message, conversationHistory = [], currentDesign = null) {
  try {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        message,
        conversationHistory,
        currentDesign
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ 
        error: 'Server error', 
        message: `Server returned ${response.status}. Please check the server logs for details.` 
      }));
      throw new Error(error.message || error.error || `Server returned ${response.status}`);
    }

    return response.json();
  } catch (error) {
    // Check for network/connection errors
    if (error.message.includes('fetch') || 
        error.message.includes('Failed to fetch') ||
        error.message.includes('NetworkError') ||
        (error.name === 'TypeError' && error.message.includes('fetch'))) {
      throw new Error('Cannot connect to server. Make sure the backend is running on port 3001.');
    }
    throw error;
  }
}

export async function buildProduct(prompt, previousDesign = null) {
  try {
    if (previousDesign) {
      console.log('🔄 Including previous design for modification');
    }
    
    const response = await fetch(`${API_BASE_URL}/build`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        prompt,
        previousDesign 
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ 
        error: 'Server error', 
        message: `Server returned ${response.status}. Please check the server logs for details.` 
      }));
      throw new Error(error.detail || error.message || error.error || `Server returned ${response.status}`);
    }

    return response.json();
  } catch (error) {
    // Check for network/connection errors
    if (error.message.includes('fetch') || 
        error.message.includes('Failed to fetch') ||
        error.message.includes('NetworkError') ||
        (error.name === 'TypeError' && error.message.includes('fetch'))) {
      throw new Error('Cannot connect to server. Make sure the backend is running on port 3001.');
    }
    throw error;
  }
}

/**
 * Stream build with SSE progress events.
 * onStep(stepData) is called for each progress event.
 * Returns the final build result when complete.
 */
export async function buildProductStream(prompt, previousDesign = null, onStep = () => {}, projectId = null) {
  const response = await fetch(`${API_BASE_URL}/build/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, previousDesign, projectId }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({
      error: 'Server error',
      message: `Server returned ${response.status}.`
    }));
    throw new Error(error.detail || error.message || error.error || `Server returned ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let finalResult = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Process complete SSE lines
    const lines = buffer.split('\n');
    buffer = lines.pop(); // keep incomplete line in buffer

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          onStep(data);

          if (data.status === 'complete' && data.result) {
            finalResult = data.result;
          }
          if (data.status === 'fatal') {
            throw new Error(data.message || 'Build failed');
          }
        } catch (e) {
          if (!(e instanceof SyntaxError)) throw e;
          // Ignore JSON parse errors on partial SSE data
        }
      }
    }
  }

  // Process any remaining buffer
  if (buffer.trim().startsWith('data: ')) {
    try {
      const data = JSON.parse(buffer.trim().slice(6));
      onStep(data);
      if (data.status === 'complete' && data.result) finalResult = data.result;
      if (data.status === 'fatal') throw new Error(data.message || 'Build failed');
    } catch (e) {
      if (!(e instanceof SyntaxError)) throw e;
    }
  }

  if (!finalResult) {
    throw new Error('Build stream ended without a result. Check server logs.');
  }

  return finalResult;
}

export async function getBuildStatus(buildId) {
  try {
    const response = await fetch(`${API_BASE_URL}/build/${buildId}`);
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Server error' }));
      throw new Error(error.message || `Server returned ${response.status}`);
    }

    return response.json();
  } catch (error) {
    // Check for network/connection errors
    if (error.message.includes('fetch') || 
        error.message.includes('Failed to fetch') ||
        error.message.includes('NetworkError') ||
        (error.name === 'TypeError' && error.message.includes('fetch'))) {
      throw new Error('Cannot connect to server. Make sure the backend is running on port 3001.');
    }
    throw error;
  }
}

export function getFileUrl(filePath) {
  return `http://localhost:3001/exports/${filePath}`;
}

/**
 * Phase 4: Rebuild model with updated parameters (no AI call)
 */
export async function rebuildWithParameters(buildId, parameters) {
  try {
    const response = await fetch(`${API_BASE_URL}/rebuild`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        buildId,
        parameters
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ 
        error: 'Rebuild failed', 
        message: `Server returned ${response.status}` 
      }));
      throw new Error(error.message || error.error || `Server returned ${response.status}`);
    }

    return response.json();
  } catch (error) {
    if (error.message.includes('fetch') || 
        error.message.includes('Failed to fetch') ||
        error.message.includes('NetworkError') ||
        (error.name === 'TypeError' && error.message.includes('fetch'))) {
      throw new Error('Cannot connect to server. Make sure the backend is running on port 3001.');
    }
    throw error;
  }
}

/**
 * Phase 4: Upload model to S3 for caching and sharing
 */
export async function uploadToS3(buildId) {
  try {
    const response = await fetch(`${API_BASE_URL}/s3/upload`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ buildId }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ 
        error: 'S3 upload failed' 
      }));
      throw new Error(error.message || error.error || `Upload failed: ${response.status}`);
    }

    return response.json(); // { shareUrl, s3Key }
  } catch (error) {
    if (error.message.includes('fetch')) {
      throw new Error('Cannot connect to server.');
    }
    throw error;
  }
}

/**
 * Phase 4: Download shared model from S3
 */
export async function downloadFromS3(s3Key) {
  try {
    const response = await fetch(`${API_BASE_URL}/s3/download/${s3Key}`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ 
        error: 'Download failed' 
      }));
      throw new Error(error.message || error.error || `Download failed: ${response.status}`);
    }

    return response.json(); // { buildId, stlUrl, stepUrl, parameters }
  } catch (error) {
    if (error.message.includes('fetch')) {
      throw new Error('Cannot connect to server.');
    }
    throw error;
  }
}

// ── Project & History API (MySQL) ────────────────────────────────────

/**
 * List all saved projects
 */
export async function getProjects() {
  const response = await fetch(`${API_BASE_URL}/projects`);
  if (!response.ok) throw new Error(`Failed to load projects: ${response.status}`);
  return response.json();
}

/**
 * Get a single project with builds and messages
 */
export async function getProject(projectId) {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}`);
  if (!response.ok) throw new Error(`Failed to load project: ${response.status}`);
  return response.json();
}

/**
 * Create a new project
 */
export async function createProject(name = 'Untitled Project', description = null) {
  const response = await fetch(`${API_BASE_URL}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description }),
  });
  if (!response.ok) throw new Error(`Failed to create project: ${response.status}`);
  return response.json();
}

/**
 * Update a project (rename)
 */
export async function updateProject(projectId, name = null, description = null) {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description }),
  });
  if (!response.ok) throw new Error(`Failed to update project: ${response.status}`);
  return response.json();
}

/**
 * Delete a project and all its data
 */
export async function deleteProject(projectId) {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error(`Failed to delete project: ${response.status}`);
  return response.json();
}

/**
 * Save a chat message to a project
 */
export async function saveMessage(projectId, role, content, buildResult = null, status = null) {
  const response = await fetch(`${API_BASE_URL}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ projectId, role, content, buildResult, status }),
  });
  if (!response.ok) throw new Error(`Failed to save message: ${response.status}`);
  return response.json();
}

/**
 * Get recent build history across all projects
 */
export async function getHistory() {
  const response = await fetch(`${API_BASE_URL}/history`);
  if (!response.ok) throw new Error(`Failed to load history: ${response.status}`);
  return response.json();
}
