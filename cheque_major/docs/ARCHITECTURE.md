# System Architecture & Design

## Overview

The Cheque Verification System is built with a clean separation between frontend (React) and backend (Flask), enabling independent scaling and development.

## Backend Architecture

### Layer Structure

```
┌─────────────────────────────────────┐
│         Flask Application           │
├─────────────────────────────────────┤
│         API Routes                  │  (routes.py)
├─────────────────────────────────────┤
│    Models & Analysis Modules        │  (models/)
│  - QualityAnalyzer                  │
│  - OCRExtractor                     │
│  - VLMExtractor                     │
│  - VerificationModel                │
├─────────────────────────────────────┤
│         Utilities                   │  (utils/)
│  - File Validation                  │
│  - Image Processing                 │
└─────────────────────────────────────┘
```

### Component Descriptions

#### 1. Flask Application (`app.py`)
- Entry point for the backend
- CORS configuration for frontend communication
- Error handling middleware
- Request logging

#### 2. Configuration (`config.py`)
- Centralized configuration management
- Feature flags for model integration
- Quality thresholds and weights
- Model endpoint URLs
- Environment-specific settings

#### 3. Models Package (`models/`)

**QualityAnalyzer** (`quality_analyzer.py`)
- Analyzes cheque images for quality issues
- Calculates 6 key metrics
- Returns weighted quality score (0-100)
- Generates actionable recommendations

**OCRExtractor** (`ocr_extractor.py`)
- Wrapper for PaddleOCR text extraction
- Supports local and remote service calls
- Parses printed text from cheques
- Returns confidence scores

**VLMExtractor** (`vlm_extractor.py`)
- Wrapper for Qwen2.5-VL handwritten text extraction
- Supports local and remote service calls
- Extracts handwritten content (signatures, notes)
- Returns confidence scores

**VerificationModel** (`verification_model.py`)
- Wrapper for trained verification model
- Supports cheque and signature verification
- Calls remote verification service
- Returns authenticity decisions and confidence

#### 4. API Routes (`api/routes.py`)
- `/api/health` - System health check
- `/api/upload` - Image upload and quality analysis
- `/api/process` - Text extraction and verification
- `/api/status/<upload_id>` - Check processing status
- `/api/quality/<upload_id>` - Re-analyze quality
- `/api/config` - System configuration (for frontend)

#### 5. Utilities (`utils/`)
- File validation (extension, size, MIME type)
- Secure filename generation
- Directory management

### Data Flow

```
User Upload
    ↓
ImageUpload Component
    ↓
POST /api/upload
    ↓
Flask: Validate file
    ↓
Save to uploads/ directory
    ↓
QualityAnalyzer: Analyze image
    ↓
Return quality report to frontend
    ↓
User Reviews Quality → Decides to Process
    ↓
POST /api/process
    ↓
Flask: Retrieve uploaded image
    ↓
OCRExtractor: Extract printed text
VLMExtractor: Extract handwritten text
VerificationModel: Verify cheque
    ↓
Return results to frontend
    ↓
ConfidenceReport displays results
```

## Frontend Architecture

### Component Hierarchy

```
App (State Management)
├── Header
├── ImageUpload (or Analysis Layout)
└── Analysis Section (when image uploaded)
    ├── Preview Panel (sticky)
    │   └── PreviewCard
    └── Results Panel
        ├── QualityReport
        │   ├── Score Gauge
        │   └── MetricBar components
        ├── ProcessingStatus
        └── ConfidenceReport
            └── ConfidenceCard components
```

### Component Responsibilities

| Component | Purpose |
|-----------|---------|
| `App` | State management, API coordination |
| `Header` | Navigation and branding |
| `ImageUpload` | Drag-drop interface, file validation |
| `QualityReport` | Display quality metrics and score |
| `ProcessingStatus` | Show pipeline progress, trigger processing |
| `ConfidenceReport` | Display model confidence scores |
| `MetricBar` | Visual progress/score indicator |
| `RecommendationAlert` | Actionable improvement suggestions |
| `ConfidenceCard` | Individual model result card |

### State Management

Using React hooks for simplicity (suitable for MVP):

```javascript
const [uploadId, setUploadId] = useState(null)
const [uploadedImage, setUploadedImage] = useState(null)
const [qualityData, setQualityData] = useState(null)
const [processingResults, setProcessingResults] = useState(null)
const [loading, setLoading] = useState(false)
const [error, setError] = useState(null)
const [config, setConfig] = useState(null)
```

For larger scale, consider Redux or Zustand.

### Styling Approach

- **CSS Variables** for theming and consistency
- **Mobile-first** responsive design
- **Dark mode** support via CSS media query
- **BEM-like** class naming for maintainability

## Image Quality Scoring Algorithm

### Overview

Quality score = Σ(metric_score × weight) for all metrics

### Metrics

#### 1. Resolution (15% weight)
```
Formula: min(100, (megapixels / 2.0) * 100)
where megapixels = (width × height) / 1,000,000

Pass Criteria:
- width >= 500px
- height >= 300px
- resolution >= 0.25 MP
```

#### 2. Sharpness (25% weight - Highest importance)
```
Formula: min(100, (laplacian_variance / 500) * 100)

Laplacian Variance = variance of Laplacian edge detection

Pass Criteria:
- laplacian_variance >= 100 (typical range: 50-500)

Blurry images have low variance, sharp images high variance.
```

#### 3. Brightness (15% weight)
```
Formula: 
if brightness in [100, 150]: score = 100
else: score = max(0, 100 - (distance_from_optimal / 100) * 50)

Optimal range: 100-150 (on 0-255 scale)
Pass Criteria:
- brightness >= 40
- brightness <= 215
```

#### 4. Contrast (15% weight)
```
Formula: min(100, standard_deviation)

std_dev = standard deviation of pixel intensity

Pass Criteria:
- std_dev >= 30

Low contrast makes text hard to read.
```

#### 5. Skew (10% weight)
```
Formula: max(0, 100 - abs(angle_degrees) * 5)

Uses Hough line detection to measure rotation angle.

Pass Criteria:
- abs(angle) <= 15°

Cheque should be horizontally aligned.
```

#### 6. Text Visibility (20% weight)
```
Formula: 
if model_confidence available: 
    score = confidence * 100
else if text_extracted:
    score = 100 (partial - extraction attempted)
else:
    score = 50 (pending - awaiting extraction)

Pass Criteria:
- confidence >= 0.7 = PASS
- confidence >= 0.5 = WARN
- confidence < 0.5 = FAIL

Important: Does NOT penalize on word count alone.
Uses extraction confidence from OCR/VLM output.
```

### Quality Bands

| Band | Range | Recommendation | Color |
|------|-------|-----------------|-------|
| GOOD | 80-100 | Ready for processing | Green |
| ACCEPTABLE | 60-79 | Manual review recommended | Yellow |
| POOR | 0-59 | Recapture recommended | Red |

### Score Calculation Example

```python
# Example cheque image
metrics = {
    'resolution': {'score': 95},      # 500x300 = 0.15MP
    'sharpness': {'score': 87},       # Laplacian var = 435
    'brightness': {'score': 82},      # Mean brightness = 125
    'contrast': {'score': 78},        # Std dev = 78
    'skew': {'score': 90},            # Angle = 2°
    'text_visibility': {'score': 75}, # OCR confidence = 0.75
}

weights = {
    'resolution': 0.15,
    'sharpness': 0.25,
    'brightness': 0.15,
    'contrast': 0.15,
    'skew': 0.10,
    'text_visibility': 0.20,
}

overall = (95*0.15) + (87*0.25) + (82*0.15) + (78*0.15) + (90*0.10) + (75*0.20)
        = 14.25 + 21.75 + 12.30 + 11.70 + 9.00 + 15.00
        = 84.00

Result: GOOD (84.00 >= 80)
```

## API Contract

### Request/Response Flow

#### Upload Request
```
POST /api/upload
Content-Type: multipart/form-data

Body:
- image: File

Response: 200 OK
{
  "success": true,
  "upload_id": string,
  "file_size_mb": number,
  "quality": {
    "overall_score": number (0-100),
    "quality_band": {
      "level": "GOOD" | "ACCEPTABLE" | "POOR",
      "label": string,
      "color": "green" | "yellow" | "red"
    },
    "metrics": {
      [metric_name]: {
        "score": number,
        "status": "PASS" | "WARN" | "FAIL",
        "message": string,
        [detailed_fields]: any
      }
    },
    "recommendations": [
      {
        "type": string,
        "severity": "INFO" | "LOW" | "MEDIUM" | "HIGH",
        "message": string
      }
    ]
  },
  "timestamp": string (ISO 8601)
}

Error: 400/413
{
  "error": string,
  "file_size_mb": number (if 413),
  "max_size_mb": number (if 413)
}
```

#### Process Request
```
POST /api/process
Content-Type: application/json

Body:
{
  "upload_id": string,
  "run_ocr": boolean (default: true),
  "run_vlm": boolean (default: true),
  "run_verification": boolean (default: false)
}

Response: 200 OK
{
  "upload_id": string,
  "ocr": {
    "status": "PENDING" | "SUCCESS" | "ERROR" | "DISABLED",
    "message": string,
    "text": string | null,
    "confidence": number | null,
    "fields": object
  },
  "vlm": {
    "status": "PENDING" | "SUCCESS" | "ERROR" | "DISABLED",
    "message": string,
    "text": string | null,
    "confidence": number | null,
    "fields": object
  },
  "verification": {
    "cheque": {
      "status": string,
      "confidence": number | null,
      "decision": string | null
    },
    "signature": {
      "status": string,
      "confidence": number | null,
      "decision": string | null
    }
  } | null,
  "timestamp": string
}
```

## Error Handling Strategy

### Backend Error Handling
- File validation errors: 400 Bad Request
- File too large: 413 Payload Too Large
- Processing errors: 500 Internal Server Error
- All errors logged for debugging

### Frontend Error Handling
- Display user-friendly error messages
- Retry logic for transient failures
- Error dismissal with clear dismiss button
- Network error detection and reporting

## Security Considerations

1. **File Upload**
   - Extension validation (whitelist approach)
   - MIME type verification
   - File size limits (20MB default)
   - Secure filename generation with timestamp

2. **Temporary File Management**
   - Upload directory separate from code
   - Automatic cleanup after 24 hours (configurable)
   - No public access to uploads directory

3. **API Security**
   - CORS configured for frontend domain
   - Input validation on all endpoints
   - No sensitive data in error messages

4. **Model Integration**
   - Model endpoints configured on backend only
   - API credentials not exposed to frontend
   - Timeouts for model requests

## Performance Optimization

### Image Quality Analysis
- Executed immediately after upload (fast operation)
- ~100-200ms per image on modern hardware
- Minimal memory footprint

### Model Integration
- Asynchronous in production (future enhancement)
- Configurable model request timeouts
- Support for local or remote models
- Batch processing ready (future enhancement)

### Frontend
- Code splitting with Vite
- Lazy loading of heavy components
- Image preview optimization (canvas)
- Efficient state management

## Testing Strategy

### Backend Testing
```python
# Unit tests for each metric calculation
def test_resolution_score()
def test_sharpness_detection()
def test_quality_scoring()

# Integration tests for API endpoints
def test_upload_endpoint()
def test_process_endpoint()
def test_config_endpoint()
```

### Frontend Testing
- Component unit tests (Jest)
- E2E tests (Cypress/Playwright)
- Manual testing of upload workflows

### Integration Testing
- Full upload → analysis → processing flow
- Error handling across layers
- File cleanup verification

## Scalability Roadmap

### Phase 1 (Current)
- Single-threaded backend
- File-based uploads
- Development environment

### Phase 2
- Production WSGI server (Gunicorn)
- Database integration (PostgreSQL)
- Async task queue (Celery)
- Redis caching

### Phase 3
- Microservices for models
- Kubernetes orchestration
- Multi-region deployment
- Real-time WebSocket updates

## Monitoring & Logging

### Backend Logging
- Request/response logging
- Model performance metrics
- File upload tracking
- Error logging with stack traces

### Frontend Analytics (Future)
- User action tracking
- Error reporting
- Performance monitoring
- Model accuracy feedback

## Maintenance & Updates

### Model Updates
- Config-based model URLs
- Zero-downtime model switching
- Version tracking for audit

### Quality Threshold Tuning
- A/B testing framework (future)
- Validation data integration
- Metric weight optimization

### Dependency Management
- Regular security updates
- Compatibility testing
- Version pinning for stability
