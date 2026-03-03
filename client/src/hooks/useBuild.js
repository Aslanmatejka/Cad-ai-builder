import { useCallback } from 'react';
import { useAppContext } from '../context/AppContext';
import { buildProductStream, rebuildWithParameters, saveMessage, getProject, nlpEditUploadedFile } from '../api';

const API_HOST = process.env.REACT_APP_API_HOST || 'http://localhost:3001';

// Map SSE steps to progress percentage
const STEP_PROGRESS = { 1: 10, 2: 40, 3: 55, 4: 75, 5: 90, 6: 100 };

export function useBuild() {
  const { state, dispatch } = useAppContext();

  const initializeScene = useCallback(async () => {
    try {
      const response = await fetch(`${API_HOST}/api/scene/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'Workspace ' + new Date().toLocaleDateString() }),
      });
      const data = await response.json();
      if (data.success) {
        dispatch({ type: 'SET_SCENE', payload: data.scene });
        return data.scene;
      }
    } catch (error) {
      console.error('Scene initialization failed:', error);
    }
    return null;
  }, [dispatch]);

  const resolveStlUrl = useCallback((buildResult) => {
    let stlFile = null;

    // Check buildResult.files.cad structure
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

    // Fallback to top-level stlUrl
    if (!stlFile && buildResult.stlUrl) {
      stlFile = buildResult.stlUrl;
    }

    if (!stlFile) return null;
    const stlPath = stlFile.startsWith('/') ? stlFile : `/exports/cad/${stlFile}`;
    return `${API_HOST}${stlPath}`;
  }, []);

  const addProductToScene = useCallback(async (buildResult, isModification = false) => {
    let scene = state.currentScene;
    if (!scene) {
      scene = await initializeScene();
      if (!scene) return;
    }

    // Handle assembly parts
    if (buildResult.isAssembly && Array.isArray(buildResult.files) && buildResult.files.length > 1) {
      const addedProducts = [];
      for (let i = 0; i < buildResult.files.length; i++) {
        const part = buildResult.files[i];
        let stlFile = null;
        if (part.files) {
          if (typeof part.files === 'object' && !Array.isArray(part.files) && part.files.stl) {
            stlFile = part.files.stl;
          } else if (Array.isArray(part.files)) {
            stlFile = part.files.find(f => f.endsWith('.stl'));
          }
        }
        if (!stlFile) continue;
        const stlPath = stlFile.startsWith('/') ? stlFile : `/exports/cad/${stlFile}`;

        const response = await fetch(`${API_HOST}/api/scene/${scene.sceneId}/add-product`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            buildId: buildResult.buildId + `_part${i + 1}`,
            instanceName: part.partName || `Part ${i + 1}`,
            position: { x: i * 50, y: 0, z: 0 },
            rotation: { x: 0, y: 0, z: 0 },
            scale: { x: 1, y: 1, z: 1 },
          }),
        });
        const data = await response.json();
        if (data.success) {
          addedProducts.push({
            instanceId: data.product.instanceId,
            buildId: buildResult.buildId + `_part${i + 1}`,
            instanceName: part.partName || `Part ${i + 1}`,
            position: data.product.position,
            rotation: data.product.rotation,
            scale: data.product.scale,
            stlUrl: `${API_HOST}${stlPath}`,
            productType: part.partName,
            designData: buildResult.design,
          });
        }
      }
      if (addedProducts.length > 0) {
        if (isModification) {
          dispatch({ type: 'REPLACE_ALL_PRODUCTS', payload: addedProducts });
        } else {
          dispatch({ type: 'ADD_PRODUCTS', payload: addedProducts });
        }
      }
      return;
    }

    // Single-part design
    const stlUrl = resolveStlUrl(buildResult);
    if (!stlUrl) {
      console.warn('No STL file found in build result');
      return;
    }

    let productPosition = { x: 0, y: 0, z: 0 };
    if (isModification && state.sceneProducts.length > 0) {
      const lastProduct = state.sceneProducts[state.sceneProducts.length - 1];
      productPosition = lastProduct.position || { x: 0, y: 0, z: 0 };
    } else if (!isModification) {
      productPosition = { x: state.sceneProducts.length * 100, y: 0, z: 0 };
    }

    const response = await fetch(`${API_HOST}/api/scene/${scene.sceneId}/add-product`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        buildId: buildResult.buildId,
        instanceName: buildResult.design?.product_type || 'Product',
        position: productPosition,
        rotation: { x: 0, y: 0, z: 0 },
        scale: { x: 1, y: 1, z: 1 },
      }),
    });

    const data = await response.json();
    if (data.success) {
      const newProduct = {
        instanceId: data.product.instanceId,
        buildId: buildResult.buildId,
        instanceName: data.product.instanceName,
        position: data.product.position,
        rotation: data.product.rotation,
        scale: data.product.scale,
        stlUrl,
        productType: buildResult.design?.product_type,
        designData: buildResult.design,
      };
      if (isModification) {
        dispatch({ type: 'REPLACE_LAST_PRODUCT', payload: newProduct });
      } else {
        dispatch({ type: 'ADD_PRODUCT', payload: newProduct });
      }
    }
  }, [state.currentScene, state.sceneProducts, dispatch, initializeScene, resolveStlUrl]);

  const handleBuild = useCallback(async (prompt) => {
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: prompt,
      timestamp: new Date(),
    };
    dispatch({ type: 'ADD_MESSAGE', payload: userMessage });

    // If there's an uploaded file with editable solid geometry, use NLP edit flow
    const uploaded = state.uploadedFile;
    const useNLPEdit = uploaded && uploaded.editable && uploaded.importCode;

    const isModification = (state.currentDesign && state.currentDesign.code) || useNLPEdit;
    const buildingMessage = {
      id: Date.now() + 1,
      type: 'assistant',
      status: 'building',
      content: useNLPEdit
        ? `Editing ${uploaded.filename} with AI...`
        : isModification
          ? 'Modifying your existing design...'
          : 'Let me design that for you...',
      steps: [],
      healingLog: [],
      timestamp: new Date(),
    };
    dispatch({ type: 'ADD_MESSAGE', payload: buildingMessage });
    dispatch({ type: 'BUILD_START' });

    // ── NLP Edit flow for uploaded files ──
    if (useNLPEdit) {
      try {
        dispatch({ type: 'BUILD_PROGRESS', payload: 30 });
        dispatch({
          type: 'UPDATE_BUILD_STEP',
          payload: { stepData: { step: 2, message: 'Analyzing your edit request with AI...', status: 'active' } },
        });

        const editResult = await nlpEditUploadedFile(
          uploaded.buildId,
          prompt,
          uploaded.importCode,
          state.currentDesign,
        );
        dispatch({ type: 'BUILD_PROGRESS', payload: 80 });

        if (editResult.success) {
          dispatch({
            type: 'UPDATE_BUILD_STEP',
            payload: { stepData: { step: 4, message: '3D model rebuilt', status: 'done' } },
          });

          dispatch({ type: 'SET_DESIGN', payload: editResult.design });
          dispatch({ type: 'SET_BUILD_ID', payload: editResult.buildId });

          const buildResult = {
            buildId: editResult.buildId,
            stlUrl: editResult.stlUrl,
            stepUrl: editResult.stepUrl,
            parametricScript: editResult.parametricScript,
            parameters: editResult.parameters,
            explanation: editResult.explanation,
            design: editResult.design,
          };
          dispatch({ type: 'BUILD_COMPLETE', payload: { result: buildResult } });
          dispatch({
            type: 'UPDATE_LAST_MESSAGE',
            payload: { status: 'success', content: editResult.explanation?.design_intent || 'Edit applied!', result: buildResult },
          });

          // Update uploaded file for chained edits
          dispatch({
            type: 'SET_UPLOADED_FILE',
            payload: { ...uploaded, importCode: editResult.design?.code || uploaded.importCode, buildId: editResult.buildId },
          });

          // Replace in scene
          const stlUrl = editResult.stlUrl ? `${API_HOST}${editResult.stlUrl}` : null;
          if (stlUrl) {
            const updatedProduct = {
              ...(state.sceneProducts[state.sceneProducts.length - 1] || {}),
              stlUrl: stlUrl + '?t=' + Date.now(),
              buildId: editResult.buildId,
            };
            dispatch({ type: 'REPLACE_LAST_PRODUCT', payload: updatedProduct });
          }
        }
      } catch (err) {
        dispatch({ type: 'BUILD_ERROR' });
        dispatch({ type: 'UPDATE_LAST_MESSAGE', payload: { status: 'error', content: err.message } });
      }
      return;
    }

    // ── Standard build flow ──
    try {
      const buildResult = await buildProductStream(
        prompt,
        state.currentDesign,
        (stepData) => {
          dispatch({ type: 'UPDATE_BUILD_STEP', payload: { stepData } });
          if (stepData.step && STEP_PROGRESS[stepData.step]) {
            dispatch({ type: 'BUILD_PROGRESS', payload: STEP_PROGRESS[stepData.step] });
          }
        },
        state.currentProjectId
      );

      dispatch({ type: 'BUILD_COMPLETE', payload: { result: buildResult } });

      dispatch({
        type: 'UPDATE_LAST_MESSAGE',
        payload: {
          status: 'success',
          content: buildResult.reasoning || "Here's your design!",
          result: buildResult,
        },
      });

      // Save chat messages to DB (fire-and-forget)
      if (buildResult.projectId) {
        dispatch({ type: 'SET_PROJECT_ID', payload: buildResult.projectId });
        try {
          await saveMessage(buildResult.projectId, 'user', prompt);
          await saveMessage(
            buildResult.projectId,
            'assistant',
            buildResult.explanation?.design_intent || 'Design created',
            buildResult,
            'success'
          );
        } catch (msgErr) {
          console.warn('Failed to save chat messages:', msgErr);
        }
      }

      await addProductToScene(buildResult, !!isModification);
    } catch (err) {
      dispatch({ type: 'BUILD_ERROR' });
      dispatch({
        type: 'UPDATE_LAST_MESSAGE',
        payload: { status: 'error', content: err.message },
      });
    }
  }, [state.currentDesign, state.currentProjectId, state.uploadedFile, state.sceneProducts, dispatch, addProductToScene]);

  const handleRebuild = useCallback(async (paramValues) => {
    if (!state.currentBuildId) return;
    try {
      const result = await rebuildWithParameters(state.currentBuildId, paramValues);
      if (result.success) {
        // Build a result object and replace the product
        const stlPath = result.stlUrl || result.files?.stl;
        if (stlPath) {
          const fullUrl = stlPath.startsWith('http') ? stlPath : `${API_HOST}${stlPath}`;
          const updatedProduct = {
            ...state.sceneProducts[state.sceneProducts.length - 1],
            stlUrl: fullUrl + '?t=' + Date.now(), // cache-bust
          };
          dispatch({ type: 'REPLACE_LAST_PRODUCT', payload: updatedProduct });
        }
      }
      return result;
    } catch (error) {
      console.error('Rebuild failed:', error);
      throw error;
    }
  }, [state.currentBuildId, state.sceneProducts, dispatch]);

  const handleProjectSelect = useCallback(async (project) => {
    try {
      const data = await getProject(project.id);
      if (!data.success || !data.project) return;
      const proj = data.project;
      dispatch({ type: 'SET_PROJECT_ID', payload: proj.id });

      if (proj.messages && proj.messages.length > 0) {
        const restoredMessages = proj.messages.map((msg, idx) => ({
          id: Date.now() + idx,
          type: msg.role,
          content: msg.content,
          status: msg.status || (msg.role === 'assistant' ? 'success' : undefined),
          result: msg.build_result || undefined,
          timestamp: new Date(msg.created_at),
        }));
        dispatch({ type: 'SET_MESSAGES', payload: restoredMessages });
      } else {
        dispatch({ type: 'SET_MESSAGES', payload: [] });
      }

      if (proj.builds && proj.builds.length > 0) {
        const lastBuild = proj.builds[proj.builds.length - 1];
        dispatch({
          type: 'SET_DESIGN',
          payload: {
            code: lastBuild.code,
            parameters: lastBuild.parameters,
            explanation: lastBuild.explanation,
          },
        });
        dispatch({ type: 'SET_BUILD_ID', payload: lastBuild.build_id });

        if (lastBuild.stl_path) {
          const buildResult = {
            buildId: lastBuild.build_id,
            stlUrl: lastBuild.stl_path,
            design: {
              code: lastBuild.code,
              parameters: lastBuild.parameters,
              explanation: lastBuild.explanation,
            },
          };
          await addProductToScene(buildResult);
        }
      } else {
        dispatch({ type: 'SET_DESIGN', payload: null });
        dispatch({ type: 'SET_BUILD_ID', payload: null });
      }
    } catch (error) {
      console.error('Failed to load project:', error);
    }
  }, [dispatch, addProductToScene]);

  const handleNewProject = useCallback(() => {
    dispatch({ type: 'SET_SHOW_PROJECT_BROWSER', payload: false });
    dispatch({ type: 'SET_MESSAGES', payload: [] });
    dispatch({ type: 'SET_DESIGN', payload: null });
    dispatch({ type: 'SET_PROJECT_ID', payload: null });
    dispatch({ type: 'SET_BUILD_ID', payload: null });
    dispatch({ type: 'SET_RESULT', payload: null });
    dispatch({ type: 'SET_STATUS', payload: 'idle' });
    dispatch({ type: 'SET_SCENE_PRODUCTS', payload: [] });
    dispatch({ type: 'SET_SCENE', payload: null });
    dispatch({ type: 'SET_UPLOADED_FILE', payload: null });
    initializeScene();
  }, [dispatch, initializeScene]);

  // ── File Upload handler ──────────────────────────────────────────────
  const handleUploadComplete = useCallback(async (uploadResult) => {
    // uploadResult comes from the /api/upload response
    const stlUrl = uploadResult.stlFile
      ? `${API_HOST}${uploadResult.stlFile}`
      : null;

    // Store uploaded file metadata for NLP editing
    dispatch({
      type: 'SET_UPLOADED_FILE',
      payload: {
        buildId: uploadResult.buildId,
        filename: uploadResult.originalFilename,
        importCode: uploadResult.importCode,
        editable: uploadResult.editable,
        boundingBox: uploadResult.boundingBox,
        geometryInfo: uploadResult.geometryInfo,
        format: uploadResult.format,
        stlUrl,
        stepUrl: uploadResult.stepFile ? `${API_HOST}${uploadResult.stepFile}` : null,
      },
    });

    // Set as current design so NLP edits use the import code
    if (uploadResult.importCode) {
      dispatch({
        type: 'SET_DESIGN',
        payload: {
          code: uploadResult.importCode,
          parameters: [],
          explanation: {
            design_intent: `Imported ${uploadResult.originalFilename} (${uploadResult.format})`,
          },
        },
      });
    }

    // Set build ID for exports
    dispatch({ type: 'SET_BUILD_ID', payload: uploadResult.buildId });

    // Set result for export panel
    dispatch({
      type: 'SET_RESULT',
      payload: {
        buildId: uploadResult.buildId,
        stlUrl: uploadResult.stlFile,
        stepUrl: uploadResult.stepFile,
      },
    });
    dispatch({ type: 'SET_STATUS', payload: 'success' });

    // Build geometry info message
    const bb = uploadResult.boundingBox || {};
    const gi = uploadResult.geometryInfo || {};
    let infoLines = [`**${uploadResult.originalFilename}** imported successfully!`];
    if (bb.width) infoLines.push(`📐 Size: ${bb.width} × ${bb.depth} × ${bb.height} mm`);
    if (gi.faces) infoLines.push(`🔷 Geometry: ${gi.faces} faces, ${gi.edges || gi.vertices || '?'} edges`);
    if (gi.volume) infoLines.push(`📦 Volume: ${gi.volume.toLocaleString()} mm³`);
    if (uploadResult.editable) {
      infoLines.push(`\n✅ **Full NLP editing supported** — describe changes in the chat to modify this model.`);
    } else {
      infoLines.push(`\n⚠️ Mesh file — view & export supported. For full NLP editing, upload a STEP or IGES file.`);
    }

    dispatch({
      type: 'ADD_MESSAGE',
      payload: {
        id: Date.now(),
        type: 'assistant',
        status: 'success',
        content: infoLines.join('\n'),
        result: {
          buildId: uploadResult.buildId,
          stlUrl: uploadResult.stlFile,
          stepUrl: uploadResult.stepFile,
        },
        timestamp: new Date(),
      },
    });

    // Add to 3D scene
    await addProductToScene({
      buildId: uploadResult.buildId,
      stlUrl: uploadResult.stlFile,
      design: { product_type: uploadResult.originalFilename },
    });
  }, [dispatch, addProductToScene]);

  // ── NLP edit for uploaded files ──────────────────────────────────────
  const handleNLPEdit = useCallback(async (prompt) => {
    const uploaded = state.uploadedFile;
    if (!uploaded) return null;

    dispatch({ type: 'BUILD_START' });

    try {
      const result = await nlpEditUploadedFile(
        uploaded.buildId,
        prompt,
        uploaded.importCode,
        state.currentDesign,
      );

      if (result.success) {
        // Update design with AI-modified code
        dispatch({
          type: 'SET_DESIGN',
          payload: result.design,
        });
        dispatch({ type: 'SET_BUILD_ID', payload: result.buildId });
        dispatch({
          type: 'SET_RESULT',
          payload: {
            buildId: result.buildId,
            stlUrl: result.stlUrl,
            stepUrl: result.stepUrl,
            parametricScript: result.parametricScript,
            parameters: result.parameters,
            explanation: result.explanation,
          },
        });
        dispatch({ type: 'SET_STATUS', payload: 'success' });
        dispatch({ type: 'BUILD_PROGRESS', payload: 100 });

        // Update uploaded file with new import code for chained edits
        dispatch({
          type: 'SET_UPLOADED_FILE',
          payload: {
            ...uploaded,
            importCode: result.design?.code || uploaded.importCode,
            buildId: result.buildId,
          },
        });

        // Replace model in scene
        const stlUrl = result.stlUrl
          ? `${API_HOST}${result.stlUrl}`
          : null;
        if (stlUrl) {
          const updatedProduct = {
            ...(state.sceneProducts[state.sceneProducts.length - 1] || {}),
            stlUrl: stlUrl + '?t=' + Date.now(),
            buildId: result.buildId,
          };
          dispatch({ type: 'REPLACE_LAST_PRODUCT', payload: updatedProduct });
        }

        return result;
      }
    } catch (err) {
      dispatch({ type: 'BUILD_ERROR' });
      throw err;
    }
  }, [state.uploadedFile, state.currentDesign, state.sceneProducts, dispatch]);

  return {
    handleBuild,
    handleRebuild,
    handleProjectSelect,
    handleNewProject,
    initializeScene,
    addProductToScene,
    handleUploadComplete,
    handleNLPEdit,
  };
}
