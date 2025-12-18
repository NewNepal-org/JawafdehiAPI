# Redux Migration Guide

This document outlines the migration from React's built-in state management to Redux Toolkit for the Agni UI application.

## Overview

The application has been successfully migrated from local React state to a centralized Redux store using Redux Toolkit, providing better state management, debugging capabilities, and scalability.

## Architecture Changes

### Before (React State)
- Local state in `App.jsx` using `useState`
- Props drilling for state and callbacks
- Manual state updates and side effects

### After (Redux Toolkit)
- Centralized state in Redux store
- Single reducer pattern with `appSlice`
- Async actions with thunks
- Custom hooks for component integration

## File Structure

```
src/
├── store/
│   ├── appSlice.js      # Main Redux slice with reducers
│   ├── actions.js       # Async thunk actions
│   ├── selectors.js     # State selectors
│   ├── store.js         # Store configuration
│   └── index.js         # Store exports
├── hooks/
│   └── useAppState.js   # Custom hook for Redux integration
```

## Key Benefits

1. **Centralized State**: All application state in one place
2. **Predictable Updates**: Redux DevTools for debugging
3. **Better Testing**: Isolated reducers and actions
4. **Scalability**: Easy to add new features and state
5. **Time Travel Debugging**: Redux DevTools support

## State Structure

```javascript
{
  currentView: 'upload' | 'processing' | 'results' | 'error',
  sessionData: SessionObject | null,
  uploadProgress: number,
  error: string | null,
  debugInfo: {
    processingHistory: string[],
    systemInfo: object
  }
}
```

## Usage Patterns

### Component Integration

```javascript
import { useAppState } from '../hooks/useAppState'

function MyComponent() {
  const {
    currentView,
    sessionData,
    handleUploadStart,
    handleError
  } = useAppState()
  
  // Use state and actions directly
}
```

### Direct Redux Usage

```javascript
import { useSelector, useDispatch } from 'react-redux'
import { selectCurrentView } from '../store/selectors'
import { setCurrentView } from '../store/appSlice'

function MyComponent() {
  const currentView = useSelector(selectCurrentView)
  const dispatch = useDispatch()
  
  const handleViewChange = (view) => {
    dispatch(setCurrentView(view))
  }
}
```

## Migration Benefits

1. **Removed Polling Indicator**: Simplified UI by removing the floating polling indicator
2. **Cleaner State Management**: No more complex state updates in components
3. **Better Debugging**: Redux DevTools for state inspection
4. **Improved Performance**: Memoized selectors prevent unnecessary re-renders
5. **Enhanced Maintainability**: Clear separation of concerns

## Development Tools

- **Redux DevTools**: Install browser extension for state debugging
- **ESLint**: Configured to work with Redux patterns
- **Hot Reloading**: Vite supports Redux state preservation during development

## Testing Considerations

- Test reducers in isolation
- Mock store for component testing
- Use Redux Toolkit's testing utilities
- Test async actions with proper mocking

## Future Enhancements

1. **RTK Query**: Consider for API state management
2. **Middleware**: Add custom middleware for logging/analytics
3. **Persistence**: Add state persistence if needed
4. **Normalization**: Normalize complex nested data structures

## Performance Notes

- Selectors are memoized for optimal performance
- Use `useAppState` hook for most component needs
- Direct Redux hooks for specific use cases
- Redux Toolkit uses Immer for immutable updates