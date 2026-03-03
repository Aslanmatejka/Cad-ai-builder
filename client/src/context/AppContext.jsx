import React, { createContext, useContext, useReducer, useCallback } from 'react';

const AppContext = createContext(null);
const MAX_HISTORY = 20;

const initialState = {
  status: 'idle', // 'idle' | 'building' | 'success' | 'error'
  result: null,
  messages: [],
  currentDesign: null,
  currentBuildId: null,
  currentProjectId: null,
  currentScene: null,
  sceneProducts: [],
  // Layout
  chatWidth: 50,
  isDragging: false,
  chatCollapsed: false,
  previewCollapsed: false,
  activeTab: 'chat', // mobile: 'chat' | 'preview'
  // Panels
  showProjectBrowser: false,
  showParameterPanel: true,
  // Upload
  uploadedFile: null,  // { buildId, filename, importCode, editable, boundingBox, ... }
  // Build progress
  buildProgress: 0,
  buildStartTime: null,
  // Undo/Redo
  history: [],
  historyIndex: -1,
};

function pushHistory(state) {
  const snapshot = {
    messages: state.messages,
    sceneProducts: state.sceneProducts,
    currentDesign: state.currentDesign,
    currentBuildId: state.currentBuildId,
    result: state.result,
  };
  const newHistory = state.history.slice(0, state.historyIndex + 1);
  newHistory.push(snapshot);
  if (newHistory.length > MAX_HISTORY) newHistory.shift();
  return { history: newHistory, historyIndex: newHistory.length - 1 };
}

function appReducer(state, action) {
  switch (action.type) {
    case 'SET_STATUS':
      return { ...state, status: action.payload };

    case 'SET_RESULT':
      return { ...state, result: action.payload };

    case 'SET_MESSAGES':
      return { ...state, messages: action.payload };

    case 'ADD_MESSAGE':
      return { ...state, messages: [...state.messages, action.payload] };

    case 'UPDATE_LAST_MESSAGE':
      return {
        ...state,
        messages: state.messages.map((msg, idx) =>
          idx === state.messages.length - 1 ? { ...msg, ...action.payload } : msg
        ),
      };

    case 'UPDATE_BUILD_STEP': {
      const { stepData } = action.payload;
      return {
        ...state,
        messages: state.messages.map((msg, idx) => {
          if (idx !== state.messages.length - 1 || msg.status !== 'building') return msg;
          let healingLog = msg.healingLog || [];
          if (stepData.step === 4 && stepData.status === 'error') {
            healingLog = [...healingLog, {
              message: stepData.message,
              detail: stepData.detail,
              attempt: stepData.healing?.attempt || 0,
            }];
          }
          return {
            ...msg,
            steps: [...(msg.steps || []).filter(s => s.step !== stepData.step), stepData],
            healingLog,
          };
        }),
      };
    }

    case 'BUILD_START':
      return {
        ...state,
        status: 'building',
        buildProgress: 0,
        buildStartTime: Date.now(),
      };

    case 'BUILD_PROGRESS':
      return { ...state, buildProgress: action.payload };

    case 'BUILD_COMPLETE': {
      const hist = pushHistory(state);
      return {
        ...state,
        status: 'success',
        result: action.payload.result,
        currentDesign: action.payload.result.design,
        currentBuildId: action.payload.result.buildId || state.currentBuildId,
        currentProjectId: action.payload.result.projectId || state.currentProjectId,
        buildProgress: 100,
        ...hist,
      };
    }

    case 'BUILD_ERROR':
      return { ...state, status: 'error', buildProgress: 0 };

    case 'SET_DESIGN':
      return { ...state, currentDesign: action.payload };

    case 'SET_BUILD_ID':
      return { ...state, currentBuildId: action.payload };

    case 'SET_PROJECT_ID':
      return { ...state, currentProjectId: action.payload };

    case 'SET_SCENE':
      return { ...state, currentScene: action.payload };

    case 'SET_SCENE_PRODUCTS':
      return { ...state, sceneProducts: action.payload };

    case 'ADD_PRODUCT': {
      return {
        ...state,
        sceneProducts: [...state.sceneProducts, action.payload],
      };
    }

    case 'REPLACE_LAST_PRODUCT': {
      const prev = state.sceneProducts;
      if (prev.length === 0) return { ...state, sceneProducts: [action.payload] };
      return { ...state, sceneProducts: [...prev.slice(0, -1), action.payload] };
    }

    case 'ADD_PRODUCTS': {
      return {
        ...state,
        sceneProducts: [...state.sceneProducts, ...action.payload],
      };
    }

    case 'REPLACE_ALL_PRODUCTS': {
      return { ...state, sceneProducts: action.payload };
    }

    // Layout
    case 'SET_CHAT_WIDTH':
      return { ...state, chatWidth: action.payload };

    case 'SET_DRAGGING':
      return { ...state, isDragging: action.payload };

    case 'TOGGLE_CHAT_COLLAPSED':
      return { ...state, chatCollapsed: !state.chatCollapsed, previewCollapsed: false };

    case 'TOGGLE_PREVIEW_COLLAPSED':
      return { ...state, previewCollapsed: !state.previewCollapsed, chatCollapsed: false };

    case 'SET_ACTIVE_TAB':
      return { ...state, activeTab: action.payload };

    case 'SET_SHOW_PROJECT_BROWSER':
      return { ...state, showProjectBrowser: action.payload };

    case 'TOGGLE_PARAMETER_PANEL':
      return { ...state, showParameterPanel: !state.showParameterPanel };

    case 'SET_UPLOADED_FILE':
      return { ...state, uploadedFile: action.payload };

    // Undo / Redo
    case 'UNDO': {
      if (state.historyIndex <= 0) return state;
      const newIndex = state.historyIndex - 1;
      const snapshot = state.history[newIndex];
      return {
        ...state,
        historyIndex: newIndex,
        messages: snapshot.messages,
        sceneProducts: snapshot.sceneProducts,
        currentDesign: snapshot.currentDesign,
        currentBuildId: snapshot.currentBuildId,
        result: snapshot.result,
        status: snapshot.result ? 'success' : 'idle',
      };
    }

    case 'REDO': {
      if (state.historyIndex >= state.history.length - 1) return state;
      const newIndex = state.historyIndex + 1;
      const snapshot = state.history[newIndex];
      return {
        ...state,
        historyIndex: newIndex,
        messages: snapshot.messages,
        sceneProducts: snapshot.sceneProducts,
        currentDesign: snapshot.currentDesign,
        currentBuildId: snapshot.currentBuildId,
        result: snapshot.result,
        status: snapshot.result ? 'success' : 'idle',
      };
    }

    case 'RESET_WORKSPACE':
      return {
        ...initialState,
        history: state.history,
        historyIndex: state.historyIndex,
      };

    default:
      return state;
  }
}

export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  const canUndo = state.historyIndex > 0;
  const canRedo = state.historyIndex < state.history.length - 1;

  const undo = useCallback(() => dispatch({ type: 'UNDO' }), []);
  const redo = useCallback(() => dispatch({ type: 'REDO' }), []);

  return (
    <AppContext.Provider value={{ state, dispatch, canUndo, canRedo, undo, redo }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  const context = useContext(AppContext);
  if (!context) throw new Error('useAppContext must be used within AppProvider');
  return context;
}

export default AppContext;
