# Project Structure

Complete file and directory layout of the Cheque Verification System.

```
cheque-major/
│
├── README.md                          # Main project documentation
├── QUICKSTART.md                      # 5-minute setup guide
├── PROJECT_STRUCTURE.md              # This file
├── .gitignore                         # Git ignore rules
│
├── docs/
│   └── ARCHITECTURE.md                # Technical architecture & design
│
├── backend/                           # Python Flask backend
│   ├── app.py                         # Flask application entry point
│   ├── config.py                      # Configuration & settings
│   ├── requirements.txt               # Python dependencies
│   ├── .env.example                   # Environment variable template
│   │
│   ├── models/                        # ML model wrappers
│   │   ├── __init__.py
│   │   ├── quality_analyzer.py        # Image quality analysis
│   │   ├── ocr_extractor.py           # PaddleOCR integration
│   │   ├── vlm_extractor.py           # Qwen2.5-VL integration
│   │   └── verification_model.py      # Cheque verification model
│   │
│   ├── api/                           # API endpoints & schemas
│   │   ├── __init__.py
│   │   └── routes.py                  # Flask routes & API logic
│   │
│   ├── utils/                         # Utility functions
│   │   ├── __init__.py
│   │   └── validators.py              # File & input validation
│   │
│   ├── uploads/                       # Temporary uploaded files
│   │   └── .gitkeep
│   │
│   └── venv/                          # Virtual environment (created by user)
│
├── frontend/                          # React application
│   ├── index.html                     # Entry HTML file
│   ├── vite.config.js                 # Vite configuration
│   ├── package.json                   # Node dependencies
│   ├── .env.example                   # Environment variable template
│   │
│   ├── src/
│   │   ├── main.jsx                   # React entry point
│   │   ├── index.css                  # Global styles
│   │   ├── App.jsx                    # Main App component
│   │   ├── App.css                    # App styles
│   │   │
│   │   └── components/
│   │       ├── Header.jsx             # Header component
│   │       ├── Header.css
│   │       │
│   │       ├── ImageUpload.jsx        # Upload interface
│   │       ├── ImageUpload.css
│   │       │
│   │       ├── QualityReport.jsx      # Quality metrics display
│   │       ├── QualityReport.css
│   │       │
│   │       ├── MetricBar.jsx          # Progress bar for metrics
│   │       ├── MetricBar.css
│   │       │
│   │       ├── RecommendationAlert.jsx # Recommendation alerts
│   │       ├── RecommendationAlert.css
│   │       │
│   │       ├── ProcessingStatus.jsx   # Pipeline status display
│   │       ├── ProcessingStatus.css
│   │       │
│   │       ├── ConfidenceReport.jsx   # Model confidence scores
│   │       ├── ConfidenceReport.css
│   │       │
│   │       ├── ConfidenceCard.jsx     # Individual model result card
│   │       └── ConfidenceCard.css
│   │
│   └── node_modules/                  # Dependencies (created by npm)
│
└── .github/                           # GitHub configuration (optional)
    ├── workflows/
    │   └── ci.yml                     # CI/CD pipeline
    └── ISSUE_TEMPLATE/
        └── bug_report.md              # Bug report template
```

## File Descriptions

### Root Level

| File | Purpose | Size |
|------|---------|------|
| `README.md` | Complete documentation with setup, API, and integration guide | ~8KB |
| `QUICKSTART.md` | Quick start guide for rapid setup | ~6KB |
| `PROJECT_STRUCTURE.md` | This file - directory overview | ~3KB |
| `.gitignore` | Git ignore patterns | ~1KB |

### Documentation (`docs/`)

| File | Purpose |
|------|---------|
| `ARCHITECTURE.md` | Detailed technical architecture, design patterns, and data flow |

### Backend (`backend/`)

**Core Application**
| File | Purpose | Lines |
|------|---------|-------|
| `app.py` | Flask application factory and middleware | ~50 |
| `config.py` | Configuration class with all settings | ~80 |
| `requirements.txt` | Python dependencies | ~25 |

**Models** (`backend/models/`)
| File | Purpose | Lines |
|------|---------|-------|
| `quality_analyzer.py` | Image quality analysis with 6 metrics | ~300 |
| `ocr_extractor.py` | PaddleOCR wrapper and integration | ~80 |
| `vlm_extractor.py` | Qwen2.5-VL wrapper and integration | ~80 |
| `verification_model.py` | Cheque/signature verification wrapper | ~120 |

**API** (`backend/api/`)
| File | Purpose | Lines |
|------|---------|-------|
| `routes.py` | Flask routes and API logic | ~300 |

**Utilities** (`backend/utils/`)
| File | Purpose | Lines |
|------|---------|-------|
| `validators.py` | File validation and security functions | ~50 |

### Frontend (`frontend/`)

**Configuration**
| File | Purpose |
|------|---------|
| `package.json` | Node dependencies and scripts |
| `vite.config.js` | Vite bundler configuration |
| `index.html` | HTML entry point |

**Source Code** (`frontend/src/`)
| File | Purpose | Lines |
|------|---------|-------|
| `main.jsx` | React entry point | ~10 |
| `App.jsx` | Main App component with state management | ~150 |
| `index.css` | Global styles and CSS variables | ~150 |
| `App.css` | App layout and structure styles | ~150 |

**Components** (`frontend/src/components/`)
| File | Purpose | Lines |
|------|---------|-------|
| `Header.jsx` | Header with branding | ~20 |
| `Header.css` | Header styles | ~50 |
| `ImageUpload.jsx` | Drag-drop file upload interface | ~120 |
| `ImageUpload.css` | Upload area styles | ~150 |
| `QualityReport.jsx` | Quality metrics and score display | ~100 |
| `QualityReport.css` | Quality report styles | ~200 |
| `MetricBar.jsx` | Progress bar component | ~25 |
| `MetricBar.css` | Metric bar styles | ~30 |
| `RecommendationAlert.jsx` | Alert component for recommendations | ~50 |
| `RecommendationAlert.css` | Alert styles | ~80 |
| `ProcessingStatus.jsx` | Pipeline status and controls | ~150 |
| `ProcessingStatus.css` | Pipeline styles | ~200 |
| `ConfidenceReport.jsx` | Model confidence scores display | ~150 |
| `ConfidenceReport.css` | Confidence report styles | ~120 |
| `ConfidenceCard.jsx` | Individual result card | ~80 |
| `ConfidenceCard.css` | Card styles | ~150 |

## Key Statistics

| Aspect | Count |
|--------|-------|
| Python files | 7 |
| React components | 8 |
| CSS files | 8 |
| Total backend lines | ~1,000 |
| Total frontend lines | ~1,500 |
| Total documentation | ~15KB |
| Configuration files | 5 |

## API Endpoint Structure

```
/api/
├── health                    GET   Health check
├── upload                    POST  Image upload & quality analysis
├── process                   POST  Extract text & verify
├── status/<upload_id>        GET   Check processing status
├── quality/<upload_id>       GET   Re-analyze quality
└── config                    GET   System configuration
```

## Frontend Component Tree

```
App
├── Header
│   ├── Logo/Icon
│   ├── Title
│   └── Subtitle
│
├── ImageUpload (initial view)
│   ├── Upload Area
│   ├── File Input (hidden)
│   ├── Validation Errors
│   ├── Loading Spinner
│   └── Help Tips
│
└── Analysis Layout (after upload)
    ├── Preview Panel (sticky)
    │   └── PreviewCard
    │       ├── Image Preview
    │       ├── File Info
    │       └── Action Buttons
    │
    └── Results Panel
        ├── QualityReport
        │   ├── Score Gauge
        │   ├── Metrics Grid
        │   │   └── MetricBar (x6)
        │   └── Recommendations
        │       └── RecommendationAlert (x multiple)
        │
        ├── ProcessingStatus
        │   ├── Pipeline Steps
        │   ├── Action Buttons
        │   └── Status Info
        │
        └── ConfidenceReport (after processing)
            ├── Disclaimer
            └── Confidence Cards Grid
                └── ConfidenceCard (x multiple)
```

## Data Flow

```
Browser
   ↓
[ImageUpload]
   ↓ (upload)
Frontend/src/App.jsx
   ↓ (POST /api/upload)
Backend/api/routes.py
   ↓ (validate)
Backend/utils/validators.py
   ↓ (save file)
Backend/uploads/
   ↓ (analyze)
Backend/models/quality_analyzer.py
   ↓ (return quality data)
App.jsx → [QualityReport]
   ↓ (trigger process)
   ↓ (POST /api/process)
Backend/api/routes.py
   ↓ (dispatch)
Backend/models/ocr_extractor.py
Backend/models/vlm_extractor.py
Backend/models/verification_model.py
   ↓ (return results)
App.jsx → [ConfidenceReport]
   ↓
Browser displays results
```

## Configuration Files Location

| File | Purpose | Location |
|------|---------|----------|
| Flask config | Application settings | `backend/config.py` |
| Vite config | Frontend build settings | `frontend/vite.config.js` |
| Package manager | Dependencies | `frontend/package.json` |
| Python deps | Backend dependencies | `backend/requirements.txt` |
| Environment vars | Local secrets | `backend/.env` & `frontend/.env.local` |

## Dependencies

### Backend (Python)
- **Flask** 3.0.0 - Web framework
- **Flask-CORS** 4.0.0 - CORS support
- **opencv-python** 4.8.1.78 - Image processing
- **numpy** 1.24.3 - Numerical computing
- **requests** 2.31.0 - HTTP client
- **Werkzeug** 3.0.1 - WSGI utilities

### Frontend (Node.js)
- **React** 18.2.0 - UI framework
- **axios** 1.6.0 - HTTP client (optional, fetch used)
- **lucide-react** 0.294.0 - Icons

## Development vs Production

### Development
- Flask development server (auto-reload)
- Vite dev server (fast HMR)
- Unminified assets
- Detailed error messages
- No authentication required

### Production
- Gunicorn WSGI server
- Vite build output (optimized)
- Minified assets
- Generic error messages
- CORS restricted
- Authentication layer (planned)

## Backup & Version Control

Recommended `.gitignore` items:
- `backend/venv/` - Virtual environment
- `backend/uploads/` - User uploaded files
- `backend/__pycache__/` - Python cache
- `frontend/node_modules/` - Dependencies
- `frontend/dist/` - Build output
- `.env` files - Secrets

All other files should be committed to version control.

## Future Additions

Planned directories/files:
```
cheque-major/
├── tests/                     # Automated test suites
│   ├── backend_tests/
│   └── frontend_tests/
├── .github/workflows/         # CI/CD pipelines
├── docker/                    # Docker configuration
├── kubernetes/                # K8s deployment files
└── migration/                 # Database migrations
```

---

This structure maintains clean separation of concerns and follows industry best practices for full-stack applications.
