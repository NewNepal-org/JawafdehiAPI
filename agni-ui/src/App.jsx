import { useEffect } from 'react'
import { useDispatch } from 'react-redux'
import HeaderCard from './components/HeaderCard'
import UploadForm from './components/UploadForm'
import ProcessingStatus from './components/ProcessingStatus'
import ResultsDisplay from './components/ResultsDisplay'
import ErrorDisplay from './components/ErrorDisplay'
import DebugPanel from './components/DebugPanel'
import { useAppState } from './hooks/useAppState'
import {
  initializeAppThunk,
  checkForExistingSessionThunk
} from './store/actions'

function App() {
  const dispatch = useDispatch()
  const {
    currentView,
    sessionData,
    uploadProgress,
    error,
    debugInfo,
    handleUploadStart,
    handleStatusUpdate,
    handleProcessingComplete,
    handleError,
    handleNewUpload,
    handleRetry,
    updateProcessingHistory
  } = useAppState()

  useEffect(() => {
    dispatch(initializeAppThunk())
    dispatch(checkForExistingSessionThunk())
  }, [dispatch])

  return (
    <div className="container-fluid py-4">
      <HeaderCard 
        sessionData={sessionData}
        currentView={currentView}
      />
      
      {currentView === 'upload' && (
        <UploadForm
          onUploadStart={handleUploadStart}
          onError={handleError}
          uploadProgress={uploadProgress}
        />
      )}
      
      {currentView === 'processing' && (
        <ProcessingStatus
          sessionData={sessionData}
          onStatusUpdate={handleStatusUpdate}
          onComplete={handleProcessingComplete}
        />
      )}
      
      {currentView === 'results' && (
        <ResultsDisplay
          sessionData={sessionData}
          onNewUpload={handleNewUpload}
        />
      )}
      
      {currentView === 'error' && (
        <ErrorDisplay
          error={error}
          onRetry={handleRetry}
          onNewUpload={handleNewUpload}
        />
      )}
      
      <DebugPanel 
        sessionData={sessionData}
        debugInfo={debugInfo}
        onUpdateHistory={updateProcessingHistory}
      />
    </div>
  )
}

export default App