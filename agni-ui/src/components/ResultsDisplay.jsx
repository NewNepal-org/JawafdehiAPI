/**
 * Results Display Component
 * Shows processing results - success or failure
 */

function ResultsDisplay({ sessionData, onNewUpload }) {
  const isSuccess = sessionData?.status === 'completed'

  return (
    <div className="card mt-4" id="results-card">
      <div className={`card-header ${isSuccess ? 'bg-success' : 'bg-danger'} text-white`}>
        <h5 className="card-title mb-0">
          <i className={`fas ${isSuccess ? 'fa-check-circle' : 'fa-exclamation-triangle'} mr-2`} />
          {isSuccess ? 'Processing Complete' : 'Processing Failed'}
        </h5>
      </div>
      
      <div className="card-body">
        <div id="results-content">
          {isSuccess 
            ? <SuccessResults sessionData={sessionData} />
            : <ErrorResults sessionData={sessionData} />
          }
        </div>
        
        <ActionButtons
          sessionData={sessionData}
          onNewUpload={onNewUpload}
        />
      </div>
    </div>
  )
}

function SuccessResults({ sessionData }) {
  return (
    <div>
      <div className="row">
        <div className="col-md-6">
          <StatCard
            icon="fas fa-users fa-3x text-success mb-3"
            value={sessionData.entities_extracted || 0}
            label="Entities Extracted"
            borderClass="border-success"
          />
        </div>
        <div className="col-md-6">
          <StatCard
            icon="fas fa-gavel fa-3x text-info mb-3"
            value={sessionData.cases_identified || 0}
            label="Potential Cases Identified"
            borderClass="border-info"
          />
        </div>
      </div>
      
      <div className="alert alert-success mt-3">
        <i className="fas fa-check-circle mr-2" />
        Document processing completed successfully! You can now review the extracted entities and approve any changes.
      </div>
    </div>
  )
}

function ErrorResults({ sessionData }) {
  return (
    <div>
      <div className="alert alert-danger">
        <i className="fas fa-exclamation-triangle mr-2" />
        <strong>Error: </strong>
        {sessionData?.error_message || 'An unknown error occurred during processing.'}
      </div>
      
      <p className="text-muted">
        Please try uploading the document again. If the problem persists, contact support.
      </p>
    </div>
  )
}

function StatCard({ icon, value, label, borderClass }) {
  return (
    <div className={`card ${borderClass}`}>
      <div className="card-body text-center">
        <i className={icon} />
        <h5 className="card-title">{value}</h5>
        <p className="card-text text-muted">{label}</p>
      </div>
    </div>
  )
}

function ActionButtons({ sessionData, onNewUpload }) {
  return (
    <div className="mt-3">
      <button
        type="button"
        className="btn btn-primary"
        onClick={() => {
          // In standalone mode, show session details in console
          console.log('Session Details:', sessionData)
          alert(`Session ${sessionData?.id} details logged to console`)
        }}
      >
        <i className="fas fa-eye mr-2" />
        View Full Session Details
      </button>
      
      <button
        type="button"
        className="btn btn-secondary ml-2"
        onClick={onNewUpload}
      >
        <i className="fas fa-plus mr-2" />
        Upload Another Document
      </button>
    </div>
  )
}

export default ResultsDisplay