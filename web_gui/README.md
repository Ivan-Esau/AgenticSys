# AgenticSys Web GUI

A clean, modern web interface for the AgenticSys autonomous multi-agent system.

## Architecture

```
web_gui/
├── backend/
│   ├── api/              # API endpoints
│   │   ├── routes.py     # FastAPI routes
│   │   └── models.py     # Pydantic models
│   ├── core/             # Core business logic
│   │   ├── orchestrator.py  # System orchestrator
│   │   ├── monitor.py       # Real-time monitoring
│   │   └── websocket.py     # WebSocket handlers
│   ├── app.py            # FastAPI application
│   └── requirements.txt  # Backend dependencies
│
├── frontend/
│   ├── index.html        # Single page application
│   ├── css/
│   │   └── styles.css    # Modern, clean styling
│   ├── js/
│   │   ├── app.js        # Main application
│   │   ├── api.js        # API client
│   │   ├── websocket.js  # WebSocket client
│   │   └── ui.js         # UI components
│   └── assets/           # Icons, images
│
├── tests/                # Test files
└── README.md            # Documentation
```

## Features

- **Real-time Monitoring**: Live updates of agent activities and tool usage
- **Clean Interface**: Modern, responsive design
- **Full Control**: Start, stop, and configure the system
- **Detailed Logging**: See all agent outputs and tool interactions
- **Pipeline Visualization**: Track progress through the multi-agent pipeline

## Technology Stack

- **Backend**: FastAPI, WebSockets, Python 3.8+
- **Frontend**: Vanilla JavaScript (no heavy frameworks)
- **Styling**: Modern CSS with CSS Grid and Flexbox
- **Communication**: REST API + WebSockets for real-time updates