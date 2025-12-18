/**
 * Header Card Component
 * Shows application title, current session information, and how it works guide
 */

import { useState } from 'react'
import HelpCard from './HelpCard'

function HeaderCard({ sessionData }) {
  const [isHowItWorksExpanded, setIsHowItWorksExpanded] = useState(false)

  return (
    <div className="card mb-4" id="header-card">
      <div className="card-header bg-primary text-white">
        <div className="d-flex justify-content-between align-items-center">
          <div>
            <h4 className="card-title mb-0">
              <i className="fas fa-robot mr-2"></i>
              Agni AI Document Processing
            </h4>
          </div>
        </div>
      </div>
      
      <div className="card-body">
        <p className="card-text text-muted mb-3">
          <i className="fas fa-info-circle mr-2"></i>
          Upload documents to extract entities and identify potential corruption cases using AI analysis.
        </p>
        
        {/* How It Works Section */}
        <div className="border-top pt-3">
          <HelpCard 
            isExpanded={isHowItWorksExpanded}
            onToggle={() => setIsHowItWorksExpanded(!isHowItWorksExpanded)}
          />
        </div>
      </div>
    </div>
  )
}

export default HeaderCard