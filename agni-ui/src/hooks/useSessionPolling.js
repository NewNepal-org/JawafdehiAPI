/**
 * Custom hook for polling session data
 * Automatically refreshes session data every 10 seconds when processing
 */

import { useEffect, useRef, useCallback } from 'react'
import { useDispatch } from 'react-redux'
import ApiService from '../utils/ApiService'
import { handleStatusUpdateThunk } from '../store/actions'

const POLLING_INTERVAL = 10000 // 10 seconds

export const useSessionPolling = (sessionId, isActive = true) => {
  const dispatch = useDispatch()
  const intervalRef = useRef(null)
  const isPollingRef = useRef(false)

  const pollSession = useCallback(async () => {
    if (!sessionId || isPollingRef.current) {
      return
    }

    try {
      isPollingRef.current = true
      const sessionData = await ApiService.getSession(sessionId)
      
      // Update the session data in the store
      dispatch(handleStatusUpdateThunk(sessionData))
      
      // Stop polling if processing is complete
      if (sessionData.status === 'completed' || sessionData.status === 'failed') {
        stopPolling()
      }
    } catch (error) {
      console.error('Failed to poll session data:', error)
      // Don't stop polling on error - the session might recover
    } finally {
      isPollingRef.current = false
    }
  }, [sessionId, dispatch])

  const startPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
    }
    
    intervalRef.current = setInterval(pollSession, POLLING_INTERVAL)
  }, [pollSession])

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  // Start/stop polling based on isActive flag
  useEffect(() => {
    if (isActive && sessionId) {
      startPolling()
    } else {
      stopPolling()
    }

    // Cleanup on unmount
    return () => {
      stopPolling()
    }
  }, [isActive, sessionId, startPolling, stopPolling])

  return {
    startPolling,
    stopPolling,
    isPolling: !!intervalRef.current
  }
}