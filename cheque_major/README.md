# Cheque Verification System

An AI-powered multi-bank cheque image quality assessment and verification system with a professional React frontend and Flask backend. Integrates PaddleOCR for printed text extraction and Qwen2.5-VL for handwritten text extraction.

## Features

- **Image Quality Assessment**: Comprehensive analysis of cheque images
  - Resolution and dimensions analysis
  - Sharpness detection (Laplacian variance)
  - Brightness and illumination assessment
  - Contrast analysis
  - Skew and rotation detection
  - Configurable quality scoring (0-100)

- **Professional UI Dashboard**
  - Drag-and-drop file upload
  - Image preview and zoom
  - Real-time quality metrics
  - Confidence score display
  - Processing pipeline visualization
  - Responsive design (desktop & mobile)

- **Model Integration Ready**
  - PaddleOCR for printed text extraction
  - Qwen2.5-VL for handwritten text extraction
  - Cheque and signature verification model
  - Pluggable architecture for adding models

- **Production-Ready**
  - Proper error handling and validation
  - File upload constraints (size, format)
  - Temporary file management
  - CORS support
  - Security-focused design

## System Architecture

```
cheque-major/
├── backend/
│   ├── app.py                 # Main Flask application
│   ├── config.py              # Configuration and settings
│   ├── requirements.txt        # Python dependencies
│   ├── models/
│   │   ├── quality_analyzer.py    # Image quality analysis
│   │   ├── ocr_extractor.py       # PaddleOCR integration
│   │   ├── vlm_extractor.py       # Qwen2.5-VL integration
│   │   └── verification_model.py  # Cheque verification
│   ├── api/
│   │   ├── routes.py          # API endpoints
│   │   └── schemas.py         # Request/response schemas
│   ├── utils/
│   │   └── validators.py      # Validation utilities
│   └── uploads/               # Temporary uploaded files
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── Header.jsx
    │   │   ├── ImageUpload.jsx
    │   │   ├── QualityReport.jsx
    │   │   ├── ConfidenceReport.jsx
    │   │   ├── ProcessingStatus.jsx
    │   │   ├── ConfidenceCard.jsx
    │   │   ├── MetricBar.jsx
    │   │   └── RecommendationAlert.jsx
    │   ├── App.jsx
    │   ├── main.jsx
    │   └── index.css
    ├── index.html
    ├── vite.config.js
    └── package.json
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- Node.js 16+
- npm or yarn

### Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create uploads directory**
   ```bash
   mkdir uploads
   ```

5. **Run backend server**
   ```bash
   python app.py
   ```
   The backend will be available at `http://localhost:5000`

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```
   The frontend will be available at `http://localhost:3000`

### Running Both Servers

**Option 1: Two terminals**
```bash
# Terminal 1
cd backend && python app.py

# Terminal 2
cd frontend && npm run dev
```

**Option 2: Using a tool like concurrently**
Install concurrently globally:
```bash
npm install -g concurrently
```

From root directory:
```bash
concurrently "cd backend && python app.py" "cd frontend && npm run dev"
```

## API Endpoints

### Health Check
```
GET /api/health
```
Returns system status and enabled services.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "services": {
    "ocr": "enabled",
    "vlm": "enabled",
    "verification": "disabled"
  }
}
```

### Upload Image
```
POST /api/upload
Content-Type: multipart/form-data
```

**Request:**
- `image`: File (multipart form)

**Response:**
```json
{
  "success": true,
  "upload_id": "20240115_103000_cheque.jpg",
  "file_size_mb": 2.5,
  "quality": {
    "overall_score": 85.5,
    "quality_band": {
      "level": "GOOD",
      "label": "Good",
      "color": "green"
    },
    "metrics": {
      "resolution": { "score": 95, "status": "PASS", "message": "..." },
      "sharpness": { "score": 87, "status": "PASS", "message": "..." },
      "brightness": { "score": 82, "status": "PASS", "message": "..." },
      "contrast": { "score": 78, "status": "PASS", "message": "..." },
      "skew": { "score": 90, "status": "PASS", "message": "..." },
      "text_visibility": { "score": 75, "status": "WARN", "message": "..." }
    },
    "recommendations": [
      {
        "type": "OK",
        "severity": "INFO",
        "message": "Image quality is good. Ready for processing."
      }
    ]
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Process Image
```
POST /api/process
Content-Type: application/json
```

**Request:**
```json
{
  "upload_id": "20240115_103000_cheque.jpg",
  "run_ocr": true,
  "run_vlm": true,
  "run_verification": false
}
```

**Response:**
```json
{
  "upload_id": "20240115_103000_cheque.jpg",
  "ocr": {
    "status": "PENDING",
    "message": "PaddleOCR integration pending",
    "text": null,
    "confidence": null
  },
  "vlm": {
    "status": "PENDING",
    "message": "Qwen2.5-VL integration pending",
    "text": null,
    "confidence": null
  },
  "verification": null,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Get Configuration
```
GET /api/config
```

**Response:**
```json
{
  "features": {
    "ocr_enabled": true,
    "vlm_enabled": true,
    "verification_enabled": false
  },
  "constraints": {
    "max_file_size_mb": 20,
    "allowed_formats": ["jpg", "jpeg", "png", "gif", "bmp", "webp"]
  },
  "quality_thresholds": {
    "MIN_WIDTH": 500,
    "MIN_HEIGHT": 300,
    "MIN_RESOLUTION_MP": 0.25,
    "SHARPNESS_THRESHOLD": 100,
    "MIN_BRIGHTNESS": 40,
    "MAX_BRIGHTNESS": 215,
    "MIN_CONTRAST": 30,
    "SKEW_TOLERANCE_DEGREES": 15
  },
  "quality_bands": {
    "GOOD": { "min": 80, "label": "Good" },
    "ACCEPTABLE": { "min": 60, "max": 79, "label": "Acceptable with caution" },
    "POOR": { "max": 59, "label": "Poor - recapture recommended" }
  }
}
```

## Image Quality Scoring

The overall quality score (0-100) is a weighted combination of:

| Metric | Weight | Calculation |
|--------|--------|-------------|
| Resolution | 15% | Based on megapixels (min 0.25MP) |
| Sharpness | 25% | Laplacian variance (normalized) |
| Brightness | 15% | Distance from optimal range (100-150) |
| Contrast | 15% | Standard deviation of pixel values |
| Skew | 10% | Angle tolerance (±15°) |
| Text Visibility | 20% | OCR/VLM extraction confidence |

**Quality Bands:**
- **80-100: Good** - Ready for immediate processing
- **60-79: Acceptable** - Manual review recommended for critical decisions
- **0-59: Poor** - Recapture strongly recommended

### Configuring Quality Metrics

Edit `backend/config.py`:

```python
QUALITY_THRESHOLDS = {
    'MIN_WIDTH': 500,           # Minimum image width
    'MIN_HEIGHT': 300,          # Minimum image height
    'MIN_RESOLUTION_MP': 0.25,  # Minimum resolution in megapixels
    'SHARPNESS_THRESHOLD': 100, # Laplacian variance threshold
    'MIN_BRIGHTNESS': 40,       # Minimum brightness (0-255 scale)
    'MAX_BRIGHTNESS': 215,      # Maximum brightness
    'MIN_CONTRAST': 30,         # Minimum contrast (std dev)
    'SKEW_TOLERANCE_DEGREES': 15, # Maximum allowed rotation
}

QUALITY_WEIGHTS = {
    'resolution': 0.15,
    'sharpness': 0.25,
    'brightness': 0.15,
    'contrast': 0.15,
    'skew': 0.10,
    'text_visibility': 0.20,
}

QUALITY_BANDS = {
    'GOOD': {'min': 80, 'label': 'Good'},
    'ACCEPTABLE': {'min': 60, 'max': 79, 'label': 'Acceptable with caution'},
    'POOR': {'max': 59, 'label': 'Poor - recapture recommended'},
}
```

## Integrating Models

### PaddleOCR Integration

When PaddleOCR is available:

1. **Install PaddleOCR** (in `backend/requirements.txt`):
   ```
   paddleocr==2.7.0.3
   paddlepaddle==2.5.1
   ```

2. **Update `backend/models/ocr_extractor.py`**:
   ```python
   from paddleocr import PaddleOCR
   
   def extract(self, image_path):
       ocr = PaddleOCR(use_angle_cls=True, lang='en')
       result = ocr.ocr(image_path, cls=True)
       
       text = ' '.join([line[0][1] for line in result])
       confidence = sum([line[0][2] for line in result]) / len(result)
       
       return {
           'status': 'SUCCESS',
           'text': text,
           'confidence': confidence,
       }
   ```

3. **Enable in config**:
   ```python
   ENABLE_PADDLE_OCR = True
   ```

### Qwen2.5-VL Integration

When Qwen2.5-VL is available:

1. **Install dependencies** (in `backend/requirements.txt`):
   ```
   transformers==4.35.0
   torch==2.0.0
   pillow==10.0.0
   ```

2. **Update `backend/models/vlm_extractor.py`**:
   ```python
   from transformers import AutoProcessor, Qwen2VLForConditionalGeneration
   from PIL import Image
   
   def extract(self, image_path):
       processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-3B")
       model = Qwen2VLForConditionalGeneration.from_pretrained("Qwen/Qwen2-VL-3B")
       
       image = Image.open(image_path)
       inputs = processor(images=[image], return_tensors="pt")
       output = model.generate(**inputs)
       text = processor.decode(output[0], skip_special_tokens=True)
       
       return {
           'status': 'SUCCESS',
           'text': text,
           'confidence': 0.85,
       }
   ```

3. **Enable in config**:
   ```python
   ENABLE_QWEN_VLM = True
   ```

### Cheque Verification Model Integration

When your verification model is available:

1. **Update `backend/models/verification_model.py`**:
   ```python
   def verify_cheque(self, image_path, ocr_output=None, vlm_output=None):
       # Load your trained model
       model = load_verification_model('path/to/model')
       
       # Extract features and run inference
       prediction = model.predict(image_path)
       
       return {
           'status': 'SUCCESS',
           'confidence': prediction.confidence,
           'decision': 'AUTHENTIC' if prediction.score > 0.7 else 'REQUIRES_REVIEW',
           'reason': prediction.reason,
       }
   ```

2. **Enable in config**:
   ```python
   ENABLE_VERIFICATION_MODEL = True
   ```

## Testing the Application

### Test Workflow

1. **Start both servers** (backend on 5000, frontend on 3000)

2. **Upload a test image**:
   - Go to `http://localhost:3000`
   - Upload a cheque image
   - View quality analysis results

3. **Test different image scenarios**:
   - Clear, well-lit image → Expect: HIGH quality
   - Blurry image → Expect: LOW sharpness score
   - Dark image → Expect: LOW brightness score
   - Rotated image → Expect: Skew warning
   - Low resolution → Expect: LOW resolution score

4. **API testing** (using curl or Postman):
   ```bash
   # Upload
   curl -X POST \
     -F "image=@cheque.jpg" \
     http://localhost:5000/api/upload

   # Get config
   curl http://localhost:5000/api/config

   # Get health
   curl http://localhost:5000/api/health
   ```

### Sample Test Images

You can use cheque images from:
- IDRBT dataset (as mentioned in your project)
- Generated test images with various quality levels
- Real cheques from different banks

## Troubleshooting

### Common Issues

**Port already in use**
```bash
# Find and kill process on port 5000 (backend)
lsof -i :5000 | grep LISTEN | awk '{print $2}' | xargs kill -9

# Find and kill process on port 3000 (frontend)
lsof -i :3000 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

**CORS errors**
- Ensure backend is running on `http://localhost:5000`
- Check `vite.config.js` proxy configuration

**File upload errors**
- Check `backend/uploads/` directory exists and is writable
- Verify file size is under 20MB
- Check file format is in allowed list

**Models not loading**
- Verify model files are in correct path
- Check CUDA availability if using GPU
- Monitor memory usage during model loading

## Production Deployment

### Backend (Flask)

For production, use a production WSGI server:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Frontend (React)

Build for production:

```bash
cd frontend
npm run build
```

Deploy the `dist/` directory to your static hosting (CDN, S3, etc.).

## Configuration

### Environment Variables

Create `.env` files:

**`backend/.env`**:
```
FLASK_ENV=production
PADDLE_OCR_URL=http://localhost:8001/extract/text
QWEN_VLM_URL=http://localhost:8002/extract/handwriting
VERIFICATION_MODEL_URL=http://localhost:8003/verify
```

**`frontend/.env.local`**:
```
VITE_API_URL=http://localhost:5000
```

## Performance Considerations

1. **Image Processing**: Large images (>10MB) may take longer to analyze
2. **Model Inference**: Depending on model size and hardware:
   - OCR: ~1-2 seconds per image
   - VLM: ~3-5 seconds per image
   - Verification: ~1-2 seconds per image
3. **Concurrent Requests**: Flask development server supports single-threaded requests; use production server for multiple concurrent uploads

## Security Notes

- **File Upload Validation**: All files are validated for extension, size, and MIME type
- **Temporary File Cleanup**: Configure cleanup interval in `config.py`
- **CORS**: Currently allows all origins; restrict in production
- **Sensitive Data**: Keep model endpoints and credentials in backend only

## Future Enhancements

- [ ] Batch upload support
- [ ] Webhook notifications for processing completion
- [ ] Database integration for result persistence
- [ ] User authentication and authorization
- [ ] Advanced analytics and reporting
- [ ] Model A/B testing framework
- [ ] Real-time processing status updates (WebSocket)
- [ ] PDF export of quality reports

## License

[Specify your license]

## Support

For issues, questions, or contributions, please contact [your contact information].
