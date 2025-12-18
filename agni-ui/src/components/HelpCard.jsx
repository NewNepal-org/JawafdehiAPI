/**
 * Help Card Component
 * Shows how-it-works guide and usage instructions with Bootstrap 4 collapse animations
 * Can be used standalone or embedded in other components
 */

import CollapsiblePanel from './CollapsiblePanel'

function HelpCard({ isExpanded, onToggle }) {
  return (
    <CollapsiblePanel
      id="helpCardCollapse"
      title="How It Works"
      icon="fas fa-question-circle"
    >
        <div className="d-flex flex-wrap">
          <div className="flex-fill text-center mb-3 px-2">
            <i className="fas fa-upload fa-2x text-primary mb-2"></i>
            <h6>1. Upload Document</h6>
            <p className="text-muted small mb-0" style={{ wordWrap: 'break-word', overflowWrap: 'break-word', maxWidth: '300px', margin: '0 auto' }}>
              Select a document file (.txt, .md, .doc, .docx, .pdf) containing information about potential corruption cases.
            </p>
          </div>
          
          <div className="flex-fill text-center mb-3 px-2">
            <i className="fas fa-cogs fa-2x text-info mb-2"></i>
            <h6>2. AI Processing</h6>
            <p className="text-muted small mb-0" style={{ wordWrap: 'break-word', overflowWrap: 'break-word', maxWidth: '300px', margin: '0 auto' }}>
              Our AI analyzes the document to extract entities, relationships, and identify potential corruption cases.
            </p>
          </div>
          
          <div className="flex-fill text-center mb-3 px-2">
            <i className="fas fa-check-circle fa-2x text-success mb-2"></i>
            <h6>3. Review Results</h6>
            <p className="text-muted small mb-0" style={{ wordWrap: 'break-word', overflowWrap: 'break-word', maxWidth: '300px', margin: '0 auto' }}>
              Review extracted entities and approve or modify the AI findings before adding to the database.
            </p>
          </div>
        </div>
        
        <hr className="my-3" />
        
        <div className="d-flex flex-wrap">
          <div className="flex-fill mb-3 px-2">
            <h6 className="mb-2">
              <i className="fas fa-lightbulb mr-2 text-warning"></i>
              Tips for Better Results
            </h6>
            <ul className="text-muted small mb-0">
              <li>Use clear, well-structured documents</li>
              <li>Include specific dates, names, and amounts</li>
              <li>Provide AI guidance for complex documents</li>
              <li>Use Nepali or English text</li>
            </ul>
          </div>
          
          <div className="flex-fill mb-3 px-2">
            <h6 className="mb-2">
              <i className="fas fa-shield-alt mr-2 text-info"></i>
              Data Privacy
            </h6>
            <ul className="text-muted small mb-0">
              <li>Documents are processed securely</li>
              <li>No personal data is stored permanently</li>
              <li>All processing follows privacy guidelines</li>
              <li>Results contribute to public transparency</li>
            </ul>
          </div>
        </div>
      </CollapsiblePanel>
  )
}

export default HelpCard