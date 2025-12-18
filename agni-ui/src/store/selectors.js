// Selectors for accessing specific parts of the Redux state
export const selectCurrentView = (state) => state.app.currentView
export const selectSessionData = (state) => state.app.sessionData
export const selectUploadProgress = (state) => state.app.uploadProgress
export const selectError = (state) => state.app.error
export const selectDebugInfo = (state) => state.app.debugInfo
export const selectProcessingHistory = (state) => state.app.debugInfo.processingHistory
export const selectSystemInfo = (state) => state.app.debugInfo.systemInfo

// Computed selectors
export const selectIsProcessing = (state) => {
  const view = selectCurrentView(state)
  return view === 'processing'
}

export const selectIsComplete = (state) => {
  const sessionData = selectSessionData(state)
  return sessionData?.status === 'completed' || sessionData?.status === 'failed'
}

export const selectHasError = (state) => {
  const error = selectError(state)
  return error !== null
}

export const selectSessionId = (state) => {
  const sessionData = selectSessionData(state)
  return sessionData?.id
}