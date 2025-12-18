/**
 * Enhanced Session Progress Bar Component
 * Shows detailed progress through processing stages with visual indicators and status
 */

import { useState, useEffect } from 'react'

// Centralized status configuration map matching Django SessionStatus choices
const STATUS_MAP = {
  pending: {
    text: 'Document queued for processing',
    alertClass: 'alert-info',
    iconClass: 'fas fa-clock',
    progressClass: 'bg-info progress-bar-animated',
    textClass: 'text-muted',
    progress: 10,
    order: 0,
    message: 'Your document is in the processing queue. This usually takes a few seconds.',
    estimatedTime: 5000 // 5 seconds
  },
  processing_metadata: {
    text: 'Processing document metadata',
    alertClass: 'alert-info',
    iconClass: 'fas fa-file-alt',
    progressClass: 'bg-info progress-bar-animated',
    textClass: 'text-info',
    progress: 25,
    order: 1,
    message: 'Extracting document metadata and basic information. This may take 15-30 seconds.',
    estimatedTime: 20000 // 20 seconds
  },
  metadata_extracted: {
    text: 'Metadata extraction completed',
    alertClass: 'alert-info',
    iconClass: 'fas fa-check',
    progressClass: 'bg-info progress-bar-animated',
    textClass: 'text-info',
    progress: 40,
    order: 2,
    message: 'Document metadata has been extracted successfully. Preparing for entity extraction.',
    estimatedTime: 2000 // 2 seconds
  },
  processing_entities: {
    text: 'Processing entities and relationships',
    alertClass: 'alert-info',
    iconClass: 'fas fa-brain',
    progressClass: 'bg-info progress-bar-animated',
    textClass: 'text-info',
    progress: 70,
    order: 3,
    message: 'AI is analyzing document content and extracting entities. This may take 30-60 seconds.',
    estimatedTime: 45000 // 45 seconds
  },
  awaiting_review: {
    text: 'Awaiting human review',
    alertClass: 'alert-warning',
    iconClass: 'fas fa-user-check',
    progressClass: 'bg-warning',
    textClass: 'text-warning',
    progress: 90,
    order: 4,
    message: 'Processing completed. Extracted entities are awaiting human review and approval.',
    estimatedTime: 0
  },
  completed: {
    text: 'Processing completed successfully',
    alertClass: 'alert-success',
    iconClass: 'fas fa-check-circle',
    progressClass: 'bg-success',
    textClass: 'text-success',
    progress: 100,
    order: 5,
    message: 'Processing completed successfully! Review the extracted information below.',
    estimatedTime: 0
  },
  failed: {
    text: 'Processing failed',
    alertClass: 'alert-danger',
    iconClass: 'fas fa-exclamation-triangle',
    progressClass: 'bg-danger',
    textClass: 'text-danger',
    progress: 100,
    order: 6,
    message: 'Processing failed. Please check the error details and try again.',
    estimatedTime: 0
  }
}

function SessionProgressBar({ sessionData, currentStatus }) {
  const [startTime] = useState(Date.now())
  const [elapsedTime, setElapsedTime] = useState(0)

  // Update elapsed time every second
  useEffect(() => {
    const interval = setInterval(() => {
      setElapsedTime(Date.now() - startTime)
    }, 1000)

    return () => clearInterval(interval)
  }, [startTime])

  const getProcessingStages = () => {
    return [
      {
        id: 'upload',
        label: 'Upload',
        description: 'Document uploaded',
        status: 'completed',
        icon: 'fas fa-upload',
        estimatedTime: 0
      },
      {
        id: 'pending',
        label: 'Queue',
        description: 'Waiting for processing',
        status: getCurrentStageStatus('pending'),
        icon: STATUS_MAP.pending.iconClass,
        estimatedTime: STATUS_MAP.pending.estimatedTime
      },
      {
        id: 'processing_metadata',
        label: 'Metadata',
        description: 'Processing metadata',
        status: getCurrentStageStatus('processing_metadata'),
        icon: STATUS_MAP.processing_metadata.iconClass,
        estimatedTime: STATUS_MAP.processing_metadata.estimatedTime
      },
      {
        id: 'processing_entities',
        label: 'Entities',
        description: 'Extracting entities',
        status: getCurrentStageStatus('processing_entities'),
        icon: STATUS_MAP.processing_entities.iconClass,
        estimatedTime: STATUS_MAP.processing_entities.estimatedTime
      },
      {
        id: 'awaiting_review',
        label: 'Review',
        description: 'Awaiting review',
        status: getCurrentStageStatus('awaiting_review'),
        icon: STATUS_MAP.awaiting_review.iconClass,
        estimatedTime: STATUS_MAP.awaiting_review.estimatedTime
      },
      {
        id: 'completed',
        label: 'Complete',
        description: 'Processing finished',
        status: getCurrentStageStatus('completed'),
        icon: STATUS_MAP.completed.iconClass,
        estimatedTime: STATUS_MAP.completed.estimatedTime
      }
    ]
  }

  const getCurrentStageStatus = (stageId) => {
    const currentIndex = STATUS_MAP[currentStatus]?.order ?? 0
    const stageIndex = STATUS_MAP[stageId]?.order ?? 0

    if (currentStatus === 'failed') {
      return stageIndex <= currentIndex ? 'failed' : 'pending'
    }

    if (stageIndex < currentIndex) return 'completed'
    if (stageIndex === currentIndex) return 'active'
    return 'pending'
  }

  const getOverallProgress = () => {
    return STATUS_MAP[currentStatus]?.progress || 0
  }

  const getEstimatedTimeRemaining = () => {
    const currentStatusConfig = STATUS_MAP[currentStatus]
    
    if (!currentStatusConfig || currentStatus === 'completed' || currentStatus === 'failed' || currentStatus === 'awaiting_review') {
      return null
    }

    const remainingTime = Math.max(0, currentStatusConfig.estimatedTime - elapsedTime)
    return Math.ceil(remainingTime / 1000)
  }

  const stages = getProcessingStages()
  const overallProgress = getOverallProgress()
  const estimatedTimeRemaining = getEstimatedTimeRemaining()

  return (
    <div className="session-progress-container mb-4">
      {/* Overall Progress Bar */}
      <div className="mb-3">
        <div className="d-flex justify-content-between align-items-center mb-2">
          <span className="font-weight-bold">Document Processing Progress</span>
          <div className="text-muted small">
            {estimatedTimeRemaining && (
              <span>
                Est. remaining: {estimatedTimeRemaining}s
              </span>
            )}
          </div>
        </div>
        
        <div className="progress mb-2" style={{ height: '8px' }}>
          <div
            className={`progress-bar progress-bar-striped ${
              STATUS_MAP[currentStatus]?.progressClass || 'bg-info progress-bar-animated'
            }`}
            role="progressbar"
            style={{ width: `${overallProgress}%` }}
            aria-valuenow={overallProgress}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
        
        <div className="text-center small text-muted">
          {overallProgress}% Complete
        </div>
      </div>

      {/* Stage Indicators */}
      <div className="stages-container">
        <div className="row">
          {stages.map((stage, index) => (
            <div key={stage.id} className="col">
              <StageIndicator
                stage={stage}
                isLast={index === stages.length - 1}
                sessionData={sessionData}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Current Status Details */}
      <CurrentStatusDetails 
        currentStatus={currentStatus}
        sessionData={sessionData}
      />
    </div>
  )
}

function StageIndicator({ stage, isLast }) {
  const getStageClasses = () => {
    const baseClasses = 'stage-indicator text-center'
    
    switch (stage.status) {
      case 'completed':
        return `${baseClasses} stage-completed`
      case 'active':
        return `${baseClasses} stage-active`
      case 'failed':
        return `${baseClasses} stage-failed`
      default:
        return `${baseClasses} stage-pending`
    }
  }

  const getIconClasses = () => {
    const baseClasses = stage.icon
    
    switch (stage.status) {
      case 'completed':
        return `${baseClasses} text-success`
      case 'active':
        return `${baseClasses} text-info`
      case 'failed':
        return `${baseClasses} text-danger`
      default:
        return `${baseClasses} text-muted`
    }
  }

  return (
    <div className={getStageClasses()}>
      <div className="stage-icon-container mb-2">
        <div className="stage-icon">
          <i className={getIconClasses()} />
          {stage.status === 'active' && (
            <div className="spinner-border spinner-border-sm position-absolute" 
                 style={{ top: '-2px', right: '-2px' }} />
          )}
        </div>
        {!isLast && (
          <div className={`stage-connector ${
            stage.status === 'completed' ? 'connector-completed' : 'connector-pending'
          }`} />
        )}
      </div>
      
      <div className="stage-label">
        <div className="font-weight-bold small">{stage.label}</div>
        <div className="text-muted" style={{ fontSize: '0.75rem' }}>
          {stage.description}
        </div>
      </div>
    </div>
  )
}

function CurrentStatusDetails({ currentStatus, sessionData }) {
  const getStatusMessage = () => {
    return STATUS_MAP[currentStatus]?.message || STATUS_MAP.pending.message
  }

  const getProcessingStats = () => {
    if (!sessionData) return null

    return (
      <div className="row">
        <div className="col">
          <div className="stat-item">
            <span className="stat-label">Session ID: </span>
            <span className="stat-value font-monospace" title={sessionData.id}>
              {sessionData.id}
            </span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="current-status-details mt-4 p-3 bg-light rounded">
      {getProcessingStats()}

      <div className="status-message mb-2">
        <i className="fas fa-info-circle text-info mr-2" />
        {getStatusMessage()}
      </div>

      {currentStatus === 'failed' && sessionData?.error_message && (
        <div className="alert alert-danger mt-3 mb-0">
          <strong>Error Details:</strong> {sessionData.error_message}
        </div>
      )}
      
  
    </div>
  )
}

export default SessionProgressBar