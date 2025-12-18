/**
 * Processing Status Component
 * Shows AI processing progress with enhanced progress bar
 */

import { useState, useEffect } from 'react'
import { useSessionPolling } from '../hooks/useSessionPolling'
import SessionProgressBar from './SessionProgressBar'
import DocumentMetadata from './DocumentMetadata'
import EntityMatching from './EntityMatching'

function ProcessingStatus({ sessionData, onComplete }) {
  const [currentStatus, setCurrentStatus] = useState(sessionData?.status || 'pending')
  
  // Determine if we should poll (only when processing is active)
  const shouldPoll = currentStatus && !['completed', 'failed'].includes(currentStatus)
  
  // Start automatic polling for session updates
  useSessionPolling(sessionData?.id, shouldPoll)

  // Update status when sessionData changes
  useEffect(() => {
    if (sessionData?.status) {
      setCurrentStatus(sessionData.status)
      
      // Check if processing is complete
      if (sessionData.status === 'completed' || sessionData.status === 'failed') {
        onComplete(sessionData)
      }
    }
  }, [sessionData, onComplete])

  const isComplete = currentStatus === 'completed' || currentStatus === 'failed'

  return (
    <div className="mt-4">
      {/* Unified Processing Card */}
      <div className="card" id="processing-status-card">
        <div className="card-body">
          {/* Progress Bar with Status */}
          <SessionProgressBar 
            sessionData={sessionData}
            currentStatus={currentStatus}
          />
        </div>
      </div>

      {/* Document Metadata - Show when metadata is available */}
      {sessionData?.metadata && (
        <DocumentMetadata metadata={sessionData.metadata} />
      )}

      {/* Entity Matching - Show when awaiting review */}
      {currentStatus === 'awaiting_review' && (
        <EntityMatching sessionData={sessionData} />
      )}

      {/* Processing Tips */}
      {!isComplete && (
        <ProcessingTips currentStatus={currentStatus} />
      )}
    </div>
  )
}

function ProcessingTips({ currentStatus }) {
  const getTips = () => {
    const tips = {
      pending: [
        'Your document is being prepared for AI analysis',
        'Processing time depends on document size and complexity',
        'You can safely close this page and return later using the session URL'
      ],
      processing_metadata: [
        'AI is extracting document metadata and basic information',
        'This process typically takes 15-30 seconds',
        'Document structure and content are being analyzed'
      ],
      processing_entities: [
        'Identifying entities, organizations, and relationships',
        'Looking for corruption indicators and patterns',
        'This process typically takes 30-60 seconds'
      ],
      awaiting_review: [
        'Processing completed successfully',
        'Extracted entities are ready for human review',
        'Review and approve the extracted information below'
      ]
    }
    
    return tips[currentStatus] || []
  }

  const tips = getTips()
  
  if (tips.length === 0) return null

  return (
    <div className="card mt-3">
      <div className="card-header bg-light">
        <h6 className="card-title mb-0">
          <i className="fas fa-lightbulb mr-2 text-warning"></i>
          Processing Tips
        </h6>
      </div>
      <div className="card-body">
        <ul className="mb-0 pl-3">
          {tips.map((tip, index) => (
            <li key={index} className="mb-1 small text-muted">
              {tip}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default ProcessingStatus