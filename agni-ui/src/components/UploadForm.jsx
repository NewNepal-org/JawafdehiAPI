/**
 * Upload Form Component
 * Handles file selection, validation, and upload initiation
 */

import { useState } from 'react'
import ApiService from '../utils/ApiService'

function UploadForm({ onUploadStart, onError, uploadProgress }) {
  const [file, setFile] = useState(null)
  const [guidance, setGuidance] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const [errors, setErrors] = useState({})

  const handleFileChange = async (e) => {
    const selectedFile = e.target.files[0]
    
    if (selectedFile) {
      try {
        ApiService.validateFile(selectedFile)
        setFile(selectedFile)
        clearError('document')
        
        // Auto-upload immediately after file selection
        await startUpload(selectedFile)
      } catch (error) {
        setError('document', error.message)
        e.target.value = ''
        setFile(null)
      }
    } else {
      setFile(null)
    }
  }

  const startUpload = async (fileToUpload) => {
    setIsUploading(true)
    setErrors({})

    try {
      const sessionData = await ApiService.uploadDocument(fileToUpload, guidance)
      onUploadStart(sessionData)
    } catch (error) {
      onError(error)
      setIsUploading(false)
    }
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    
    if (!file) {
      setError('document', 'Please select a document file.')
      return
    }

    await startUpload(file)
  }

  const setError = (field, message) => {
    setErrors(prev => ({ ...prev, [field]: message }))
  }

  const clearError = (field) => {
    setErrors(prev => {
      const newErrors = { ...prev }
      delete newErrors[field]
      return newErrors
    })
  }

  return (
    <div className="card" id="upload-form-card">
      <div className="card-body">
        <form 
          id="upload-form"
          encType="multipart/form-data"
          onSubmit={handleUpload}
        >
          <FileInput
            file={file}
            onChange={handleFileChange}
            error={errors.document}
            disabled={isUploading}
          />

          <GuidanceInput
            value={guidance}
            onChange={setGuidance}
            error={errors.guidance}
            disabled={isUploading}
          />

          {isUploading && (
            <UploadProgress progress={uploadProgress} />
          )}

          <ActionButtons
            onUpload={handleUpload}
            isUploading={isUploading}
            disabled={!file || isUploading}
          />
        </form>
      </div>
    </div>
  )
}

function FileInput({ onChange, error, disabled }) {
  return (
    <div className="form-group mb-4">
      <label 
        htmlFor="id_document"
        className="form-label required"
      >
        <i className="fas fa-file-upload mr-1"></i>
        Document
      </label>
      
      <div className="custom-file">
        <input
          type="file"
          name="document"
          id="id_document"
          accept=".txt,.md,.doc,.docx,.pdf"
          className={`form-control ${error ? 'is-invalid' : ''}`}
          onChange={onChange}
          disabled={disabled}
          required
        />
      </div>
      
      {error && (
        <div className="invalid-feedback d-block">
          {error}
        </div>
      )}
      
      <small className="form-text text-muted">
        <i className="fas fa-info-circle mr-1"></i>
        Supported formats: .txt, .md, .doc, .docx, .pdf (Max size: 10MB)
      </small>
    </div>
  )
}

function GuidanceInput({ value, onChange, error, disabled }) {
  return (
    <div className="form-group mb-4">
      <label 
        htmlFor="id_guidance"
        className="form-label"
      >
        <i className="fas fa-lightbulb mr-1"></i>
        AI Guidance
        <span className="badge badge-secondary ml-1">
          Optional
        </span>
      </label>
      
      <textarea
        name="guidance"
        id="id_guidance"
        rows={4}
        className={`form-control ${error ? 'is-invalid' : ''}`}
        placeholder="Provide specific guidance for AI extraction (e.g., focus on financial irregularities, specific entities, date ranges, etc.)"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      />
      
      {error && (
        <div className="invalid-feedback d-block">
          {error}
        </div>
      )}
      
      <small className="form-text text-muted">
        <i className="fas fa-info-circle mr-1"></i>
        Help the AI understand what to focus on during document analysis and entity extraction.
      </small>
    </div>
  )
}

function UploadProgress({ progress }) {
  return (
    <div id="upload-progress">
      <div className="alert alert-info">
        <div className="d-flex align-items-center mb-2">
          <div 
            className="spinner-border spinner-border-sm mr-2"
            role="status"
          >
            <span className="sr-only">Loading...</span>
          </div>
          <strong id="upload-status-text">
            Uploading document...
          </strong>
        </div>
        
        <div className="progress">
          <div
            id="progress-bar"
            className="progress-bar progress-bar-striped progress-bar-animated"
            role="progressbar"
            style={{ width: `${progress}%` }}
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
        
        <small 
          className="text-muted mt-1"
          id="upload-status-detail"
        >
          This may take a few moments depending on document size and complexity.
        </small>
      </div>
    </div>
  )
}

function ActionButtons({ onUpload, isUploading, disabled }) {
  return (
    <div 
      className="form-group mb-0"
      id="form-actions"
    >
      <button
        type="button"
        id="upload-btn"
        className="btn btn-primary btn-lg"
        onClick={onUpload}
        disabled={disabled}
      >
        <i className={`fas ${isUploading ? 'fa-spinner fa-spin' : 'fa-cloud-upload-alt'} mr-2`} />
        {isUploading ? 'Uploading...' : 'Upload and Start Processing'}
      </button>
      
      <button
        type="button"
        className="btn btn-secondary btn-lg ml-2"
        onClick={() => window.location.reload()}
      >
        <i className="fas fa-times mr-2" />
        Cancel
      </button>
    </div>
  )
}

export default UploadForm