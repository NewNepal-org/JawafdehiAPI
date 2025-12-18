import { 
  initializeApp,
  loadExistingSession,
  startUpload,
  updateSessionStatus,
  completeProcessing,
  handleError,
  resetApp,
  retryProcessing,
  addProcessingHistoryEntry,
  setCurrentView
} from './appSlice'
import ApiService from '../utils/ApiService'

// Thunk action creators for async operations
export const initializeAppThunk = () => (dispatch) => {
  const systemInfo = {
    userAgent: navigator.userAgent,
    timestamp: new Date().toISOString(),
    pageUrl: window.location.href,
    urlParams: getURLParams()
  }
  
  dispatch(initializeApp(systemInfo))
}

export const checkForExistingSessionThunk = () => (dispatch) => {
  const urlParams = new URLSearchParams(window.location.search)
  const sessionId = urlParams.get('session_id') || urlParams.get('session')
  
  if (sessionId) {
    dispatch(addProcessingHistoryEntry(`Loading existing session: ${sessionId}`))
    dispatch(loadExistingSessionThunk(sessionId))
  }
}

export const loadExistingSessionThunk = (sessionId) => async (dispatch) => {
  try {
    dispatch(setCurrentView('loading'))
    
    const sessionData = await ApiService.getSession(sessionId)
    
    dispatch(loadExistingSession({ sessionData }))
    dispatch(addProcessingHistoryEntry(`Loaded session ${sessionData.id} with status: ${sessionData.status}`))
    
    updatePageTitle(`Session ${sessionId}`)
    
  } catch (error) {
    dispatch(handleErrorThunk(`Failed to load session: ${error.message}`))
  }
}

export const handleUploadStartThunk = (sessionData, progress = 0) => (dispatch) => {
  dispatch(startUpload({ sessionData, progress }))
  dispatch(addProcessingHistoryEntry(`Upload started for session ${sessionData.id}`))
  
  updatePageTitle(`Processing Session ${sessionData.id}`)
  updateURL(sessionData.id)
}

export const handleStatusUpdateThunk = (updatedSessionData) => (dispatch) => {
  dispatch(updateSessionStatus(updatedSessionData))
  dispatch(addProcessingHistoryEntry(`Status updated: ${updatedSessionData.status}`))
}

export const handleProcessingCompleteThunk = (finalSessionData) => (dispatch) => {
  dispatch(completeProcessing(finalSessionData))
  dispatch(addProcessingHistoryEntry(`Processing completed with status: ${finalSessionData.status}`))
}

export const handleErrorThunk = (error) => (dispatch) => {
  dispatch(handleError(error.message || error))
  dispatch(addProcessingHistoryEntry(`Error: ${error.message || error}`))
}

export const handleNewUploadThunk = () => (dispatch) => {
  dispatch(resetApp())
  
  updatePageTitle('Agni AI Document Processing')
  clearURL()
}

export const handleRetryThunk = () => (dispatch, getState) => {
  const { app } = getState()
  
  if (app.sessionData) {
    dispatch(retryProcessing())
  } else {
    dispatch(handleNewUploadThunk())
  }
}

// Utility functions
const updatePageTitle = (title) => {
  document.title = `${title} | Agni AI`
}

const updateURL = (sessionId) => {
  const newUrl = new URL(window.location)
  newUrl.searchParams.set('session_id', sessionId)
  window.history.pushState({ sessionId }, '', newUrl)
}

const clearURL = () => {
  const newUrl = new URL(window.location)
  newUrl.searchParams.delete('session_id')
  newUrl.searchParams.delete('session')
  window.history.pushState({}, '', newUrl)
}

const getURLParams = () => {
  const urlParams = new URLSearchParams(window.location.search)
  const paramsObj = Object.fromEntries(urlParams.entries())
  return Object.keys(paramsObj).length > 0 ? JSON.stringify(paramsObj) : 'None'
}