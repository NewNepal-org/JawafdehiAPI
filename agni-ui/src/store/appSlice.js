import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  currentView: 'upload',
  sessionData: null,
  uploadProgress: 0,
  error: null,
  debugInfo: {
    processingHistory: ['Page loaded'],
    systemInfo: {}
  }
}

const appSlice = createSlice({
  name: 'app',
  initialState,
  reducers: {
    setCurrentView: (state, action) => {
      state.currentView = action.payload
    },
    
    setSessionData: (state, action) => {
      state.sessionData = action.payload
    },
    
    setUploadProgress: (state, action) => {
      state.uploadProgress = action.payload
    },
    
    setError: (state, action) => {
      state.error = action.payload
    },
    
    clearError: (state) => {
      state.error = null
    },
    
    setSystemInfo: (state, action) => {
      state.debugInfo.systemInfo = action.payload
    },
    
    addProcessingHistoryEntry: (state, action) => {
      const timestamp = new Date().toLocaleTimeString()
      const entry = `[${timestamp}] ${action.payload}`
      state.debugInfo.processingHistory.push(entry)
    },
    
    resetProcessingHistory: (state, action) => {
      state.debugInfo.processingHistory = action.payload || ['Started new upload session']
    },
    
    resetApp: (state) => {
      return {
        ...initialState,
        debugInfo: {
          processingHistory: ['Started new upload session'],
          systemInfo: state.debugInfo.systemInfo
        }
      }
    },
    
    initializeApp: (state, action) => {
      state.debugInfo.systemInfo = action.payload
    },
    
    loadExistingSession: (state, action) => {
      const { sessionData } = action.payload
      state.sessionData = sessionData
      state.currentView = sessionData.status === 'completed' || sessionData.status === 'failed' 
        ? 'results' 
        : 'processing'
    },
    
    startUpload: (state, action) => {
      const { sessionData, progress = 0 } = action.payload
      state.currentView = 'processing'
      state.sessionData = sessionData
      state.uploadProgress = progress
      state.error = null
    },
    
    updateSessionStatus: (state, action) => {
      state.sessionData = action.payload
    },
    
    completeProcessing: (state, action) => {
      state.currentView = 'results'
      state.sessionData = action.payload
    },
    
    handleError: (state, action) => {
      state.currentView = 'error'
      state.error = action.payload
    },
    
    retryProcessing: (state) => {
      if (state.sessionData) {
        state.currentView = 'processing'
        state.error = null
      }
    }
  }
})

export const {
  setCurrentView,
  setSessionData,
  setUploadProgress,
  setError,
  clearError,
  setSystemInfo,
  addProcessingHistoryEntry,
  resetProcessingHistory,
  resetApp,
  initializeApp,
  loadExistingSession,
  startUpload,
  updateSessionStatus,
  completeProcessing,
  handleError,
  retryProcessing
} = appSlice.actions

export default appSlice.reducer