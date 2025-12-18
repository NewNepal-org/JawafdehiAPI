/**
 * Debug Panel Component
 * Shows debug information and processing history
 */

import CollapsiblePanel from './CollapsiblePanel'

function DebugPanel({ sessionData, debugInfo, onUpdateHistory }) {
  return (
    <CollapsiblePanel
      id="debugPanelCollapse"
      title="Debug Information"
      icon="fas fa-bug"
      className="debug-panel mt-4"
    >
          <div className="row">
            <div className="col-md-6">
              <h6>
                <i className="fas fa-history mr-2"></i>
                Processing History
              </h6>
              <div 
                className="bg-dark text-light p-2 rounded small"
                style={{ height: '200px', overflowY: 'auto', fontFamily: 'monospace' }}
              >
                {debugInfo.processingHistory.map((entry, index) => (
                  <div key={index}>{entry}</div>
                ))}
              </div>
            </div>
            
            <div className="col-md-6">
              <h6>
                <i className="fas fa-info-circle mr-2"></i>
                System Information
              </h6>
              <div className="small">
                <SystemInfoItem 
                  label="Timestamp"
                  value={debugInfo.systemInfo.timestamp}
                />
                <SystemInfoItem 
                  label="Page URL"
                  value={debugInfo.systemInfo.pageUrl}
                />
                <SystemInfoItem 
                  label="URL Parameters"
                  value={debugInfo.systemInfo.urlParams}
                />
                <SystemInfoItem 
                  label="User Agent"
                  value={debugInfo.systemInfo.userAgent}
                />
              </div>
            </div>
          </div>
          
          {sessionData && (
            <div className="mt-3">
              <h6>
                <i className="fas fa-database mr-2"></i>
                Session Data
              </h6>
              <div 
                className="bg-light p-2 rounded small"
                style={{ fontFamily: 'monospace', overflowX: 'auto' }}
              >
                <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{JSON.stringify(sessionData, null, 2)}</pre>
              </div>
            </div>
          )}
          
          <div className="mt-3">
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary"
              onClick={() => onUpdateHistory('Manual debug refresh triggered')}
            >
              <i className="fas fa-refresh mr-1"></i>
              Add Debug Entry
            </button>
            
            <button
              type="button"
              className="btn btn-sm btn-outline-info ml-2"
              onClick={() => {
                const debugData = {
                  sessionData,
                  debugInfo,
                  timestamp: new Date().toISOString()
                }
                console.log('Debug Data:', debugData)
                navigator.clipboard?.writeText(JSON.stringify(debugData, null, 2))
                alert('Debug data copied to clipboard and logged to console')
              }}
            >
              <i className="fas fa-copy mr-1"></i>
              Copy Debug Data
            </button>
          </div>
    </CollapsiblePanel>
  )
}

function SystemInfoItem({ label, value }) {
  return (
    <div className="mb-1">
      <strong>{label}:</strong>{' '}
      <span className="text-muted text-break">
        {value || 'Not available'}
      </span>
    </div>
  )
}

export default DebugPanel