/**
 * Entity Matching Component
 * Displays entity matching session data with status and entity details
 */

import { useDispatch } from 'react-redux'
import { handleStatusUpdateThunk } from '../store/actions'
import ApiService from '../utils/ApiService'

// Add CSS styles for entity table layout
const entityTableStyles = `
  .entity-table { 
    table-layout: fixed; 
    width: 100%; 
  }
  .entity-table td:first-child { 
    width: 100px; 
  }
  .entity-table td:nth-child(2) { 
    width: 110px; 
  }
  .entity-table td:nth-child(3) { 
    width: auto; 
  }
  .confidence { 
    font-size: 0.75rem; 
  }
  .entity-type { 
    font-size: 0.7rem; 
    font-weight: 600; 
    text-transform: uppercase; 
  }
  .json-viewer {
    background: #1e1e1e;
    color: #d4d4d4;
    font-family: 'SF Mono', Monaco, 'Courier New', monospace;
    font-size: 0.8rem;
    max-height: 500px;
    overflow: auto;
    line-height: 1.6;
  }
  .json-viewer pre {
    background: transparent;
    border: none;
    color: inherit;
    margin: 0;
  }
`

// Inject styles if not already present
if (!document.getElementById('entity-matching-styles')) {
  const styleSheet = document.createElement('style')
  styleSheet.id = 'entity-matching-styles'
  styleSheet.textContent = entityTableStyles
  document.head.appendChild(styleSheet)
}

function EntityMatching({ sessionData }) {
  const dispatch = useDispatch()
  
  if (!sessionData) return null

  const { progress, entities = [], metadata } = sessionData
  
  // Callback to refresh session data after entity deletion
  const handleEntityDeleted = async () => {
    try {
      // Fetch fresh session data (same as polling mechanism)
      const updatedSessionData = await ApiService.getSession(sessionData.id)
      
      // Dispatch the update action (same as polling does)
      dispatch(handleStatusUpdateThunk(updatedSessionData))
    } catch (error) {
      console.error('Failed to refresh session data after deletion:', error)
      // Show user-friendly error message
      alert('Failed to refresh data. Please refresh the page manually.')
    }
  }

  return (
    <div className="card mt-4">
      <div className="card-header bg-info text-white">
        <h5 className="card-title mb-0">
          <i className="fas fa-link mr-2" />
          Entity Matching
        </h5>
      </div>
      
      <div className="card-body">
        <ProgressStats progress={progress} />
        <EntityList entities={entities} sessionId={sessionData.id} onEntityDeleted={handleEntityDeleted} />
      </div>
    </div>
  )
}

function ProgressStats({ progress }) {
  if (!progress) return null
  
  const { total_entities, needs_disambiguation, auto_matched } = progress
  
  return (
    <div className="row mb-4">
      <div className="col-md-3 col-6 mb-2">
        <div className="border rounded p-2 text-center">
          <h5 className="mb-0 text-primary">{total_entities}</h5>
          <small className="text-muted">Extracted</small>
        </div>
      </div>
      <div className="col-md-3 col-6 mb-2">
        <div className="border rounded p-2 text-center">
          <h5 className="mb-0 text-success">{auto_matched}</h5>
          <small className="text-muted">Auto-matched</small>
        </div>
      </div>
      <div className="col-md-3 col-6 mb-2">
        <div className="border rounded p-2 text-center">
          <h5 className="mb-0 text-warning">{needs_disambiguation}</h5>
          <small className="text-muted">Needs Review</small>
        </div>
      </div>
      <div className="col-md-3 col-6 mb-2">
        <div className="border rounded p-2 text-center">
          <h5 className="mb-0 text-secondary">{total_entities - auto_matched - needs_disambiguation}</h5>
          <small className="text-muted">New Entity</small>
        </div>
      </div>
    </div>
  )
}

function EntityList({ entities, sessionId, onEntityDeleted }) {
  if (!entities.length) return null

  return (
    <div>
      <h6 className="mb-3">Entities ({entities.length})</h6>
      {entities.map((entity, index) => (
        <EntityCard key={index} entity={entity} index={index} sessionId={sessionId} onEntityDeleted={onEntityDeleted} />
      ))}
    </div>
  )
}

function EntityCard({ entity, index, sessionId, onEntityDeleted }) {
  const { entity_type, names, status, confidence, candidates = [] } = entity
  const primaryName = names?.[0]?.name || 'Unknown'
  const nepaliName = names?.find(n => n.language === 'ne')?.name
  
  const statusConfig = {
    needs_disambiguation: { 
      class: 'warning', 
      icon: 'question-circle',
      label: '⚠️ NEEDS REVIEW',
      bgClass: 'bg-warning'
    },
    create_new: { 
      class: 'info', 
      icon: 'plus-circle',
      label: '➕ CREATE',
      bgClass: 'bg-success'
    },
    auto_matched: { 
      class: 'success', 
      icon: 'check-circle',
      label: '✓ AUTO MATCHED',
      bgClass: 'bg-success'
    }
  }
  
  const config = statusConfig[status] || { 
    class: 'secondary', 
    icon: 'circle',
    label: '— NO CHANGE',
    bgClass: 'bg-secondary'
  }
  
  const entityId = `entity${index + 1}`
  
  return (
    <div className={`card mb-3 border-${config.class}`} id={`${entityId}-card`}>
      <div 
        className={`card-header py-2 ${config.bgClass} text-white d-flex justify-content-between align-items-center`}
        style={{ cursor: 'pointer' }}
        data-toggle="collapse" 
        data-target={`#${entityId}-body`}
      >
        <div>
          <span className="badge badge-light mr-2">{config.label}</span>
          <strong>{primaryName}</strong>
          <span className="badge badge-light ml-2">{entity_type}</span>
        </div>
        <div className="d-flex align-items-center ml-auto">
          {confidence && (
            <span className="badge badge-light mr-2" style={{ fontSize: '0.75rem' }}>
              {Math.round(confidence * 100)}%
            </span>
          )}
          <small>▼</small>
        </div>
      </div>
      
      <div className="collapse" id={`${entityId}-body`}>
        <div className="card-body py-3">
          <EntityDetails entity={entity} candidates={candidates} entityId={entityId} sessionId={sessionId} onEntityDeleted={onEntityDeleted} />
        </div>
      </div>
    </div>
  )
}

function EntityDetails({ entity, candidates, entityId, sessionId, onEntityDeleted }) {
  const { entity_type, names, status, confidence, entity_data = {}, matched_id } = entity
  const primaryName = names?.[0]?.name || 'Unknown'
  const nepaliName = names?.find(n => n.language === 'ne')?.name
  
  return (
    <div>
      {/* Entity description */}
      <p className="text-muted small mb-2">
        {status === 'auto_matched' && matched_id && `Matched existing entity: ${matched_id} — High confidence automatic match`}
        {status === 'needs_disambiguation' && `${candidates.length} potential matches found`}
        {status === 'create_new' && 'No existing matches found - will create new entity'}
      </p>
      
      {/* Tab buttons */}
      <div className="btn-group btn-group-sm mb-2" role="group">
        <button 
          type="button" 
          className="btn btn-outline-secondary btn-sm" 
          onClick={(e) => toggleEntityTab(entityId, 'extracted', e.target)}
        >
          Extracted
        </button>
        <button 
          type="button" 
          className="btn btn-outline-secondary btn-sm" 
          onClick={(e) => toggleEntityTab(entityId, 'current', e.target)}
        >
          Current
        </button>
        <button 
          type="button" 
          className="btn btn-outline-secondary btn-sm active" 
          onClick={(e) => toggleEntityTab(entityId, 'proposed', e.target)}
        >
          Proposed
        </button>
        <button 
          type="button" 
          className="btn btn-outline-secondary btn-sm" 
          onClick={(e) => toggleEntityTab(entityId, 'json', e.target)}
        >
          JSON
        </button>
      </div>
      
      {/* Extracted view */}
      <div id={`${entityId}-extracted`} className="json-viewer p-3 rounded" style={{ display: 'none' }}>
        <pre className="mb-0 small">{JSON.stringify(entity, null, 2)}</pre>
      </div>
      
      {/* Current view */}
      <div id={`${entityId}-current`} style={{ display: 'none' }}>
        {matched_id ? (
          <table className="table table-sm table-borderless mb-0 small entity-table">
            <tbody>
              <tr><td className="text-muted">Name</td><td className="text-muted">PRIMARY (en)</td><td>{primaryName}</td></tr>
              {nepaliName && (
                <tr><td className="text-muted">Name</td><td className="text-muted">PRIMARY (ne)</td><td>{nepaliName}</td></tr>
              )}
              <tr><td className="text-muted">Type</td><td></td><td>{entity_type}</td></tr>
              <tr><td className="text-muted">Entity ID</td><td></td><td>{matched_id}</td></tr>
            </tbody>
          </table>
        ) : (
          <div className="alert alert-light text-muted small mb-0">
            <em>No existing entity — this is a new record</em>
          </div>
        )}
      </div>
      
      {/* Proposed view (default) */}
      <div id={`${entityId}-proposed`}>
        <table className="table table-sm table-borderless mb-0 small entity-table">
          <tbody>
            <tr>
              <td className="text-muted" style={{ width: '100px' }}>Name</td>
              <td className="text-muted" style={{ width: '110px' }}>PRIMARY (en)</td>
              <td>{primaryName}</td>
            </tr>
            {nepaliName && (
              <tr>
                <td className="text-muted">Name</td>
                <td className="text-muted">PRIMARY (ne)</td>
                <td>{nepaliName}</td>
              </tr>
            )}
            <tr>
              <td className="text-muted">Type</td>
              <td></td>
              <td>
                {entity_type}
                <i className={`fas fa-${entity_type === 'person' ? 'user' : entity_type === 'organization' ? 'building' : 'map-marker-alt'} ml-2 text-muted`} />
              </td>
            </tr>
            {confidence && (
              <tr>
                <td className="text-muted">Confidence</td>
                <td></td>
                <td>
                  <span className={`badge badge-${confidence > 0.9 ? 'success' : confidence > 0.7 ? 'warning' : 'secondary'}`}>
                    {Math.round(confidence * 100)}%
                  </span>
                </td>
              </tr>
            )}
            
            {/* Display entity_data fields */}
            {entity_data.positions && (
              <tr>
                <td className="text-muted">Positions</td>
                <td></td>
                <td>{entity_data.positions}</td>
              </tr>
            )}
            {entity_data.arrest_date && (
              <tr>
                <td className="text-muted">Arrest Date</td>
                <td></td>
                <td>{entity_data.arrest_date}</td>
              </tr>
            )}
            {entity_data.release_date && (
              <tr>
                <td className="text-muted">Release Date</td>
                <td></td>
                <td>{entity_data.release_date}</td>
              </tr>
            )}
            {entity_data.bail_amount_npr && (
              <tr>
                <td className="text-muted">Bail Amount</td>
                <td></td>
                <td>NPR {parseInt(entity_data.bail_amount_npr).toLocaleString()}</td>
              </tr>
            )}
            {entity_data.charges && (
              <tr>
                <td className="text-muted">Charges</td>
                <td></td>
                <td>{entity_data.charges}</td>
              </tr>
            )}
            
            {/* Display other entity_data fields dynamically */}
            {Object.entries(entity_data).map(([key, value]) => {
              if (['positions', 'arrest_date', 'release_date', 'bail_amount_npr', 'charges'].includes(key)) {
                return null; // Already displayed above
              }
              return (
                <tr key={key}>
                  <td className="text-muted">{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</td>
                  <td></td>
                  <td>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</td>
                </tr>
              );
            })}
            
            {candidates.length > 0 && (
              <tr>
                <td className="text-muted">Candidates</td>
                <td></td>
                <td>
                  <span className="text-info">{candidates.length} potential match(es)</span>
                  <div className="mt-1">
                    {candidates.slice(0, 3).map((candidate, idx) => (
                      <div key={idx} className="small text-muted">
                        • {candidate.nes_id || candidate.name} 
                        {candidate.confidence && ` (${Math.round(candidate.confidence * 100)}%)`}
                        {candidate.reason && <span className="text-muted"> - {candidate.reason}</span>}
                      </div>
                    ))}
                    {candidates.length > 3 && (
                      <div className="small text-muted">
                        ... and {candidates.length - 3} more
                      </div>
                    )}
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      
      {/* JSON view */}
      <div id={`${entityId}-json`} className="json-viewer p-3 rounded" style={{ display: 'none' }}>
        <pre className="mb-0 small" style={{ color: '#d4d4d4', backgroundColor: '#1e1e1e' }}>
          {JSON.stringify(entity, null, 2)}
        </pre>
      </div>
      
      {/* Action buttons for disambiguation */}
      {status === 'needs_disambiguation' && candidates.length > 0 && (
        <div className="mt-3 pt-3 border-top">
          <small className="text-muted font-weight-bold">Select Match:</small>
          <div className="mt-2">
            {candidates.map((candidate, idx) => (
              <button 
                key={idx}
                className="btn btn-outline-primary btn-sm mr-2 mb-2"
                onClick={() => console.log('Selected candidate:', candidate)}
              >
                {candidate.nes_id || candidate.name} 
                {candidate.confidence && ` (${Math.round(candidate.confidence * 100)}%)`}
              </button>
            ))}
            <button 
              className="btn btn-outline-secondary btn-sm mb-2"
              onClick={() => console.log('Create new entity')}
            >
              ➕ Create New
            </button>
          </div>
        </div>
      )}
      
      {/* Entity actions */}
      <div className="mt-3 pt-3 border-top d-flex justify-content-between align-items-center">
        <button 
          className="btn btn-outline-danger btn-sm"
          onClick={() => handleDeleteEntity(entity, entityId, sessionId, onEntityDeleted)}
        >
          <i className="fas fa-trash mr-1"></i>
          Delete Entity
        </button>
        
        <div>
          <button 
            className="btn btn-outline-secondary btn-sm mr-2"
            onClick={() => console.log('Reject entity:', entity)}
          >
            Reject
          </button>
          <button 
            className="btn btn-success btn-sm"
            onClick={() => console.log('Approve entity:', entity)}
          >
            ✓ Approve
          </button>
        </div>
      </div>
    </div>
  )
}

// Tab switching function
function toggleEntityTab(entityId, view, button) {
  // Hide all views
  const views = ['extracted', 'current', 'proposed', 'json']
  views.forEach(v => {
    const element = document.getElementById(`${entityId}-${v}`)
    if (element) {
      element.style.display = 'none'
    }
  })
  
  // Show selected view
  const selectedView = document.getElementById(`${entityId}-${view}`)
  if (selectedView) {
    selectedView.style.display = 'block'
  }
  
  // Update button states
  if (button) {
    // Remove active class from all buttons in the group
    const buttonGroup = button.parentElement
    Array.from(buttonGroup.children).forEach(btn => {
      btn.classList.remove('active')
    })
    
    // Add active class to clicked button
    button.classList.add('active')
  }
}

// Entity deletion handler
async function handleDeleteEntity(entity, entityId, sessionId, onEntityDeleted) {
  const entityName = entity.names?.[0]?.name || 'Unknown'
  
  try {
    // Extract entity index from entityId (e.g., "entity1" -> 0)
    const entityIndex = parseInt(entityId.replace('entity', '')) - 1
    
    const response = await ApiService.deleteEntity(sessionId, entityIndex)
    
    if (response.success) {
      onEntityDeleted()
    } else {
      alert(`Failed to delete entity: ${response.message || 'Unknown error'}`)
    }
  } catch (error) {
    console.error('Delete entity error:', error)
    alert(`Failed to delete entity: ${error.message}`)
  }
}

export default EntityMatching