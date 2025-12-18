/**
 * Error Display Component
 * Shows error states and recovery options
 */

function ErrorDisplay({ error, onRetry, onNewUpload }) {
  return (
    <div className="card mt-4" id="error-card">
      <div className="card-header bg-danger text-white">
        <h5 className="card-title mb-0">
          <i className="fas fa-exclamation-triangle mr-2"></i>
          Processing Error
        </h5>
      </div>
      
      <div className="card-body">
        <div className="alert alert-danger">
          <i className="fas fa-exclamation-triangle mr-2"></i>
          <strong>Error: </strong>
          {error || 'An unknown error occurred.'}
        </div>
        
        <p className="text-muted">
          The document processing encountered an error. You can try again or upload a different document.
        </p>
        
        <ErrorActionButtons 
          onRetry={onRetry}
          onNewUpload={onNewUpload}
        />
      </div>
    </div>
  )
}

function ErrorActionButtons({ onRetry, onNewUpload }) {
  return (
    <div className="mt-3">
      <button
        type="button"
        className="btn btn-warning"
        onClick={onRetry}
      >
        <i className="fas fa-redo mr-2"></i>
        Try Again
      </button>
      
      <button
        type="button"
        className="btn btn-secondary ml-2"
        onClick={onNewUpload}
      >
        <i className="fas fa-plus mr-2"></i>
        Upload New Document
      </button>
    </div>
  )
}

export default ErrorDisplay