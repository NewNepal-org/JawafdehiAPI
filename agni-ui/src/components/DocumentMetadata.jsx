/**
 * Document Metadata Display Component
 * Shows extracted document metadata in a clean, organized format
 */

import CollapsiblePanel from './CollapsiblePanel'

function DocumentMetadata({ metadata }) {
  if (!metadata) {
    return null
  }

  const formatDate = (dateString) => {
    if (!dateString || dateString === 'null') return null
    try {
      const date = new Date(dateString)
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      })
    } catch (error) {
      return dateString
    }
  }

  const getDocumentTypeDisplay = (type) => {
    const typeMap = {
      'report': 'Report',
      'letter': 'Letter',
      'policy': 'Policy Document',
      'investigation': 'Investigation Report',
      'investigation_report': 'Investigation Report',
      'court_case': 'Court Case',
      'audit': 'Audit Report',
      'audit_report': 'Audit Report',
      'complaint': 'Complaint',
      'notice': 'Notice'
    }
    return typeMap[type] || type?.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const isValidValue = (value) => {
    return value && value !== 'null' && value.trim() !== ''
  }

  const hasContent = isValidValue(metadata.title) || isValidValue(metadata.summary) || 
                    isValidValue(metadata.author) || isValidValue(metadata.publication_date) || 
                    isValidValue(metadata.document_type) || isValidValue(metadata.source)

  if (!hasContent) {
    return null
  }

  return (
    <CollapsiblePanel
      id="documentMetadataCollapse"
      title="Document Metadata"
      icon="fas fa-file-alt"
      className="document-metadata-container mb-4"
    >
            <div className="row">
              {/* Title */}
              {isValidValue(metadata.title) && (
                <div className="col-12 mb-3">
                  <div className="metadata-item">
                    <div className="metadata-label">
                      <i className="fas fa-heading text-muted mr-2"></i>
                      <strong>Title</strong>
                    </div>
                    <div className="metadata-value">
                      {metadata.title}
                    </div>
                  </div>
                </div>
              )}

              {/* Summary */}
              {isValidValue(metadata.summary) && (
                <div className="col-12 mb-3">
                  <div className="metadata-item">
                    <div className="metadata-label">
                      <i className="fas fa-align-left text-muted mr-2"></i>
                      <strong>Summary</strong>
                    </div>
                    <div className="metadata-value">
                      <div className="summary-text">
                        {metadata.summary}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Author and Source Row */}
              <div className="col-md-6 mb-3">
                {isValidValue(metadata.author) && (
                  <div className="metadata-item">
                    <div className="metadata-label">
                      <i className="fas fa-user text-muted mr-2"></i>
                      <strong>Author</strong>
                    </div>
                    <div className="metadata-value">
                      {metadata.author}
                    </div>
                  </div>
                )}
              </div>

              <div className="col-md-6 mb-3">
                {isValidValue(metadata.source) && (
                  <div className="metadata-item">
                    <div className="metadata-label">
                      <i className="fas fa-building text-muted mr-2"></i>
                      <strong>Source</strong>
                    </div>
                    <div className="metadata-value">
                      {metadata.source}
                    </div>
                  </div>
                )}
              </div>

              {/* Document Type and Date Row */}
              <div className="col-md-6 mb-3">
                {isValidValue(metadata.document_type) && (
                  <div className="metadata-item">
                    <div className="metadata-label">
                      <i className="fas fa-tag text-muted mr-2"></i>
                      <strong>Document Type</strong>
                    </div>
                    <div className="metadata-value">
                      <span className="badge badge-secondary">
                        {getDocumentTypeDisplay(metadata.document_type)}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              <div className="col-md-6 mb-3">
                {isValidValue(metadata.publication_date) && (
                  <div className="metadata-item">
                    <div className="metadata-label">
                      <i className="fas fa-calendar text-muted mr-2"></i>
                      <strong>Publication Date</strong>
                    </div>
                    <div className="metadata-value">
                      {formatDate(metadata.publication_date)}
                    </div>
                  </div>
                )}
              </div>
            </div>
            {/* Metadata Quality Indicator */}
            <div className="metadata-quality mt-3 pt-3 border-top">
              <div className="d-flex align-items-center justify-content-between">
                <div className="text-muted small">
                  <i className="fas fa-info-circle mr-1"></i>
                  Extracted metadata from document analysis
                </div>
                <MetadataQualityBadge metadata={metadata} />
              </div>
            </div>
    </CollapsiblePanel>
  )
}

function MetadataQualityBadge({ metadata }) {
  const fields = ['title', 'summary', 'author', 'publication_date', 'document_type', 'source']
  const isValidValue = (value) => value && value !== 'null' && value.trim() !== ''
  const filledFields = fields.filter(field => isValidValue(metadata[field]))
  const completeness = Math.round((filledFields.length / fields.length) * 100)

  const getBadgeClass = () => {
    if (completeness >= 80) return 'badge-success'
    if (completeness >= 60) return 'badge-warning'
    return 'badge-secondary'
  }

  const getQualityText = () => {
    if (completeness >= 80) return 'High Quality'
    if (completeness >= 60) return 'Moderate Quality'
    return 'Basic Quality'
  }

  return (
    <div className="metadata-quality-badge">
      <span className={`badge ${getBadgeClass()}`}>
        {getQualityText()} ({completeness}%)
      </span>
    </div>
  )
}

export default DocumentMetadata