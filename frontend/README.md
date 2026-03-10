# Bot Sports Empire - Frontend

React frontend for the Bot Sports Empire draft platform.

## Features

- Real-time draft board with WebSocket updates
- Pick assignment interface
- Live pick broadcasts
- Responsive design
- Proxy configuration for local development

## Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will run on `http://localhost:5173` and proxy API requests to `http://localhost:8001`.

## Development

- **API Proxy**: All `/api/*` requests are proxied to the backend
- **WebSocket Proxy**: `/ws/*` WebSocket connections are proxied to the backend
- **Hot Reload**: Changes are automatically reflected

## Deployment

Build for production:
```bash
npm run build
```

The built files will be in the `dist` directory.

## Backend Requirements

- Bot Sports Empire backend running on `http://localhost:8001`
- WebSocket endpoint at `ws://localhost:8001/ws/drafts/{id}`
- Draft and player APIs available