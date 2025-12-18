# Agni UI - Standalone React Application

A standalone React application for the Agni AI document processing interface, integrated within the JawafdehiAPI Django project. Built with modern React development practices and designed to work seamlessly with the Django backend.

## Features

- **Document Upload**: Support for .txt, .md, .doc, .docx, .pdf files
- **AI Processing**: Real-time status updates with polling
- **Entity Extraction**: Display of extracted entities and corruption cases
- **Bilingual Support**: English and Nepali language support
- **Debug Panel**: Development debugging and monitoring
- **Responsive Design**: Bootstrap-based responsive UI

## Technology Stack

- **React 18** with JSX support
- **Redux Toolkit** for state management
- **React Redux** for React-Redux integration
- **Vite** for fast development and building
- **Bootstrap 5** for responsive UI components
- **Font Awesome** for icons
- **ESLint** for code quality

## Development Setup

### Prerequisites

- Node.js 18+ or Bun
- Running JawafdehiAPI Django backend on `http://localhost:8000`

### Installation

```bash
# Navigate to the agni-ui directory within JawafdehiAPI
cd services/JawafdehiAPI/agni-ui

# Install dependencies
npm install
# or with bun
bun install

# Copy environment configuration
cp .env.example .env

# Start development server
npm run dev
# or with bun
bun run dev
```

The application will be available at `http://localhost:7999` and will proxy API requests to the Django backend.

### Environment Configuration

Copy `.env.example` to `.env` and configure:

```env
# Django API backend
VITE_API_BASE_URL=http://localhost:8000

# Enable debug mode (disables CSRF for development)
VITE_DEBUG=true

# Other configuration options...
```

## API Integration

The application connects to the Django JawafdehiAPI backend:

- **Upload Endpoint**: `POST /api/agni/sessions/`
- **Status Endpoint**: `GET /api/agni/sessions/{id}/`

### CSRF Handling

In development mode (`VITE_DEBUG=true`), CSRF verification is bypassed. In production, the application expects proper CSRF tokens from the Django backend.

## Project Structure

```
src/
├── components/           # React components
│   ├── HeaderCard.jsx   # Application header
│   ├── UploadForm.jsx   # File upload form
│   ├── ProcessingStatus.jsx  # AI processing status
│   ├── ResultsDisplay.jsx    # Processing results
│   ├── ErrorDisplay.jsx      # Error handling
│   ├── HelpCard.jsx          # Usage instructions
│   └── DebugPanel.jsx        # Debug information
├── store/               # Redux state management
│   ├── appSlice.js      # Main application slice
│   ├── actions.js       # Async action creators
│   ├── selectors.js     # State selectors
│   ├── store.js         # Store configuration
│   └── index.js         # Store exports
├── hooks/               # Custom React hooks
│   └── useAppState.js   # App state management hook
├── utils/
│   └── ApiService.js    # Backend API communication
├── App.jsx              # Main application component
├── main.jsx            # Application entry point
└── index.css           # Global styles
```

## Component Architecture

### State Management

The application uses **Redux Toolkit** for centralized state management with a single reducer pattern:

#### Redux Store Structure

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

#### Key Redux Files

- **`appSlice.js`**: Main Redux slice with reducers and actions
- **`actions.js`**: Async thunk actions for complex operations
- **`selectors.js`**: Memoized selectors for accessing state
- **`store.js`**: Store configuration with Redux Toolkit
- **`useAppState.js`**: Custom hook for easy component integration

#### Usage Pattern

```javascript
import { useAppState } from '../hooks/useAppState'

function MyComponent() {
  const {
    currentView,
    sessionData,
    handleUploadStart,
    handleError
  } = useAppState()
  
  // Component logic using Redux state and actions
}
```
## Development Features

### Debug Panel

The debug panel provides:
- Processing history timeline
- System information
- Session data inspection
- Manual debug entries
- Data export functionality

### Auto-Upload

Files are automatically uploaded upon selection for faster workflow.

### Status Polling

Real-time status updates every 5 seconds during processing with error recovery.

## Building for Production

```bash
# Build the application
npm run build
# or with bun
bun run build

# Preview the build
npm run preview
# or with bun
bun run preview
```

The built files will be in the `dist/` directory.

## Integration with Django

To integrate the built application with Django:

1. Build the application: `npm run build`
2. Copy `dist/` contents to Django static files
3. Update Django templates to serve the built files
4. Configure CSRF tokens for production

## Nepali Context Examples

The application includes authentic Nepali context in examples and test data:

- **Organizations**: नेपाल सरकार, काठमाडौं महानगरपालिका
- **Locations**: काठमाडौं, पोखरा, चितवन
- **Names**: राम बहादुर, सीता देवी, गोपाल शर्मा

## Accessibility

The application follows WCAG 2.1 AA guidelines:

- Semantic HTML structure
- Keyboard navigation support
- Screen reader compatibility
- Color contrast compliance
- Focus management

## Contributing

1. Follow the existing code style
2. Add tests for new features
3. Update documentation
4. Use authentic Nepali examples
5. Ensure accessibility compliance

## License

This project is part of the Jawafdehi platform for promoting transparency and accountability in Nepali governance.