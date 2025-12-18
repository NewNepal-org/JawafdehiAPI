/**
 * API Service for Agni AI document processing
 * Handles all backend communication with Django API
 */

const ApiService = {
  /**
   * Get the base API URL
   */
  getBaseUrl() {
    // Use environment variable or default to localhost:8000
    return import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
  },

  /**
   * Upload a document and start processing
   */
  async uploadDocument(file, guidance = '') {
    const formData = new FormData()
    formData.append('document', file)
    formData.append('guidance', guidance)

    const response = await fetch(`${this.getBaseUrl()}/api/agni/sessions/`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: formData
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.message || 'Upload failed')
    }

    return response.json()
  },

  /**
   * Get session status and data
   */
  async getSession(sessionId) {
    const response = await fetch(`${this.getBaseUrl()}/api/agni/sessions/${sessionId}/`, {
      method: 'GET',
      headers: this.getHeaders()
    })

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Session not found')
      }
      if (response.status === 403) {
        throw new Error('Access denied')
      }
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  },

  /**
   * Delete entity from session
   */
  async deleteEntity(sessionId, entityIndex) {
    const response = await fetch(`${this.getBaseUrl()}/api/agni/sessions/${sessionId}/entities/${entityIndex}/delete/`, {
      method: 'DELETE',
      headers: this.getHeaders()
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.message || `HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  },

  /**
   * Validate file before upload
   */
  validateFile(file) {
    const allowedExtensions = ['.txt', '.md', '.doc', '.docx', '.pdf']
    const maxFileSize = 10 * 1024 * 1024 // 10MB

    if (!file) {
      throw new Error('Please select a document file.')
    }

    const fileName = file.name
    const fileExtension = fileName.toLowerCase().substring(fileName.lastIndexOf('.'))

    if (!allowedExtensions.includes(fileExtension)) {
      throw new Error('Invalid file type. Please select a .txt, .md, .doc, .docx, or .pdf file.')
    }

    if (file.size > maxFileSize) {
      throw new Error('File size too large. Maximum size is 10MB.')
    }

    return true
  },

    /**
   * Get headers for API requests (without CSRF token)
   */
  getHeaders() {
    const headers = {};

    const token = document.querySelector('[name=csrfmiddlewaretoken]')
    if (token?.value) {
      headers["X-CSRFToken"] = token.value
    }
    return headers;
  },
}

export default ApiService