import { useState, useEffect, useRef } from 'react'

function CollapsiblePanel({ id, title, icon, children, className = '' }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const collapseRef = useRef(null)

  useEffect(() => {
    const collapseElement = collapseRef.current
    if (!collapseElement) return

    const handleShow = () => setIsExpanded(true)
    const handleHide = () => setIsExpanded(false)

    $(collapseElement).on('show.bs.collapse', handleShow)
    $(collapseElement).on('hide.bs.collapse', handleHide)

    return () => {
      $(collapseElement).off('show.bs.collapse', handleShow)
      $(collapseElement).off('hide.bs.collapse', handleHide)
    }
  }, [])

  return (
    <div className={className}>
      <div 
        className="collapse-toggle p-3 bg-light border rounded cursor-pointer"
        data-toggle="collapse"
        data-target={`#${id}`}
        aria-expanded={isExpanded}
        aria-controls={id}
      >
        <h6 className="mb-0 d-flex justify-content-between align-items-center">
          <span>
            {icon && <i className={`${icon} mr-2`}></i>}
            {title}
          </span>
          <i className={`fas fa-chevron-${isExpanded ? 'up' : 'down'}`}></i>
        </h6>
      </div>
      
      <div className="collapse" id={id} ref={collapseRef}>
        <div className="p-3 border border-top-0 rounded-bottom">
          {children}
        </div>
      </div>
    </div>
  )
}

export default CollapsiblePanel