import { useSelector, useDispatch } from 'react-redux'
import {
  selectCurrentView,
  selectSessionData,
  selectUploadProgress,
  selectError,
  selectDebugInfo,
  selectIsProcessing,
  selectIsComplete,
  selectHasError,
  selectSessionId
} from '../store/selectors'
import {
  handleUploadStartThunk,
  handleStatusUpdateThunk,
  handleProcessingCompleteThunk,
  handleErrorThunk,
  handleNewUploadThunk,
  handleRetryThunk
} from '../store/actions'
import { addProcessingHistoryEntry } from '../store/appSlice'

/**
 * Custom hook for accessing app state and actions
 * Provides a clean interface for components to interact with Redux
 */
export const useAppState = () => {
  const dispatch = useDispatch()
  
  // State selectors
  const currentView = useSelector(selectCurrentView)
  const sessionData = useSelector(selectSessionData)
  const uploadProgress = useSelector(selectUploadProgress)
  const error = useSelector(selectError)
  const debugInfo = useSelector(selectDebugInfo)
  const isProcessing = useSelector(selectIsProcessing)
  const isComplete = useSelector(selectIsComplete)
  const hasError = useSelector(selectHasError)
  const sessionId = useSelector(selectSessionId)
  
  // Action dispatchers
  const actions = {
    handleUploadStart: (sessionData, progress = 0) => {
      dispatch(handleUploadStartThunk(sessionData, progress))
    },
    
    handleStatusUpdate: (updatedSessionData) => {
      dispatch(handleStatusUpdateThunk(updatedSessionData))
    },
    
    handleProcessingComplete: (finalSessionData) => {
      dispatch(handleProcessingCompleteThunk(finalSessionData))
    },
    
    handleError: (error) => {
      dispatch(handleErrorThunk(error))
    },
    
    handleNewUpload: () => {
      dispatch(handleNewUploadThunk())
    },
    
    handleRetry: () => {
      dispatch(handleRetryThunk())
    },
    
    updateProcessingHistory: (event) => {
      dispatch(addProcessingHistoryEntry(event))
    }
  }
  
  return {
    // State
    currentView,
    sessionData,
    uploadProgress,
    error,
    debugInfo,
    isProcessing,
    isComplete,
    hasError,
    sessionId,
    
    // Actions
    ...actions
  }
}