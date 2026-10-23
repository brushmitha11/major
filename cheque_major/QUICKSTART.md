# Quick Start Guide

Get the Cheque Verification System up and running in 5 minutes.

## Prerequisites

Ensure you have installed:
- **Python 3.8+** - [Download](https://www.python.org/downloads/)
- **Node.js 16+** - [Download](https://nodejs.org/)
- **Git** - [Download](https://git-scm.com/)

Verify installation:
```bash
python --version    # Should be 3.8+
node --version      # Should be 16+
npm --version       # Should be 8+
```

## Option 1: Windows Quick Start (Recommended for Development)

### Step 1: Clone/Navigate to Project
```bash
cd D:\cheque_major
```

### Step 2: Start Backend (Terminal 1)
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
mkdir uploads
python app.py
```

You should see:
```
 * Running on http://127.0.0.1:5000
```

### Step 3: Start Frontend (Terminal 2)
```bash
cd frontend
npm install
npm run dev
```

You should see:
```
  VITE v5.0.0  ready in 123 ms

  ➜  Local:   http://localhost:3000/
```

### Step 4: Open in Browser
Navigate to `http://localhost:3000` and you're ready to test!

---

## Option 2: macOS/Linux Quick Start

### Step 1: Navigate to Project
```bash
cd cheque_major
```

### Step 2: Start Backend (Terminal 1)
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
mkdir -p uploads
python3 app.py
```

### Step 3: Start Frontend (Terminal 2)
```bash
cd frontend
npm install
npm run dev
```

### Step 4: Open in Browser
Navigate to `http://localhost:3000`

---

## Testing the Application

### Minimal Test Flow

1. **Backend Health Check** (verify backend is running)
   ```bash
   curl http://localhost:5000/api/health
   ```
   
   Expected response:
   ```json
   {
     "status": "healthy",
     "services": {
       "ocr": "disabled",
       "vlm": "disabled",
       "verification": "disabled"
     }
   }
   ```

2. **Test Image Upload**
   - Use any `.jpg`, `.png`, or `.jpeg` image (preferably a cheque)
   - Go to `http://localhost:3000`
   - Drag & drop image or click to upload
   - Wait for quality analysis

3. **View Results**
   - See quality score (0-100)
   - Review quality metrics
   - Read recommendations

### What to Expect

**For a clear, well-lit cheque image:**
- Overall score: 80-100 (GOOD)
- All metrics should show PASS status
- Green quality band

**For a blurry cheque image:**
- Sharpness metric will show LOW score
- Overall score will be lower
- Yellow/Red quality band
- Recommendations to improve focus

---

## Troubleshooting

### Issue: Port Already in Use

**Backend port 5000 already in use?**
```bash
# Windows
netstat -ano | findstr :5000

# macOS/Linux
lsof -i :5000
```

Then kill the process or use different port in `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Use 5001 instead
```

**Frontend port 3000 already in use?**
```bash
# Windows
netstat -ano | findstr :3000

# macOS/Linux
lsof -i :3000
```

Or update `vite.config.js`:
```javascript
server: {
    port: 3001,  // Use 3001 instead
    ...
}
```

### Issue: Module Not Found (Python)

Make sure virtual environment is activated:
```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

You should see `(venv)` prefix in terminal.

### Issue: npm install Fails

Clear npm cache and reinstall:
```bash
cd frontend
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### Issue: CORS Errors in Browser

Ensure:
1. Backend is running on `http://localhost:5000`
2. Frontend is running on `http://localhost:3000`
3. `vite.config.js` proxy is configured:
   ```javascript
   proxy: {
     '/api': {
       target: 'http://localhost:5000',
       changeOrigin: true,
     }
   }
   ```

---

## Using Real Cheque Images

### Recommended Test Approach

1. **Use IDRBT Dataset** (if available)
   - Place cheque images in a test directory
   - Upload through UI

2. **Generate Test Images**
   - Create cheques with varying quality
   - Test edge cases (blur, rotation, poor lighting)

3. **Test Different Banks**
   - Images from different bank cheque formats
   - Verify system handles different layouts

### Image Preparation

For best results, cheque images should be:
- **Resolution**: At least 500x300 pixels
- **Format**: JPG, PNG, or BMP
- **Size**: Under 20MB
- **Condition**: Clear, not blurry, good lighting
- **Alignment**: Cheque horizontal (not rotated >15°)

---

## Next Steps

### When Ready for Model Integration

1. **PaddleOCR** (Printed Text)
   - Install: `pip install paddleocr paddlepaddle`
   - Update: `backend/models/ocr_extractor.py`
   - Enable: Set `ENABLE_PADDLE_OCR = True` in config

2. **Qwen2.5-VL** (Handwritten Text)
   - Install: `pip install torch transformers pillow`
   - Update: `backend/models/vlm_extractor.py`
   - Enable: Set `ENABLE_QWEN_VLM = True` in config

3. **Verification Model** (Your Custom Model)
   - Update: `backend/models/verification_model.py`
   - Enable: Set `ENABLE_VERIFICATION_MODEL = True` in config

### Production Deployment

**Backend:**
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

**Frontend:**
```bash
npm run build
# Deploy dist/ folder to your hosting
```

---

## Key Files to Know

| File | Purpose |
|------|---------|
| `backend/app.py` | Main backend application |
| `backend/config.py` | Configuration & settings |
| `backend/models/quality_analyzer.py` | Image quality scoring |
| `frontend/src/App.jsx` | Main React component |
| `frontend/src/components/ImageUpload.jsx` | Upload interface |
| `README.md` | Full documentation |
| `docs/ARCHITECTURE.md` | Technical deep dive |

---

## Getting Help

1. **Check logs** in terminal where servers are running
2. **Browser console** (F12) for frontend errors
3. **Network tab** (F12) to inspect API calls
4. **Read** `docs/ARCHITECTURE.md` for technical details
5. **Review** `README.md` API endpoints section

---

## Configuration Customization

### Change Quality Thresholds

Edit `backend/config.py`:
```python
QUALITY_THRESHOLDS = {
    'MIN_WIDTH': 600,           # Increase from 500
    'SHARPNESS_THRESHOLD': 150, # Increase from 100
    # ... other settings
}
```

### Change Quality Score Weights

Edit `backend/config.py`:
```python
QUALITY_WEIGHTS = {
    'sharpness': 0.35,  # Increase from 0.25
    'text_visibility': 0.15,  # Decrease from 0.20
    # ... other weights (must sum to 1.0)
}
```

### Change Quality Bands

Edit `backend/config.py`:
```python
QUALITY_BANDS = {
    'GOOD': {'min': 85},          # Change from 80
    'ACCEPTABLE': {'min': 65, 'max': 84},  # Change range
}
```

---

## Common Commands

```bash
# Backend
cd backend
python app.py                    # Run in dev mode
pip install -r requirements.txt  # Install dependencies
python -m pytest                 # Run tests (when added)

# Frontend
cd frontend
npm run dev                      # Development mode
npm run build                    # Production build
npm run preview                  # Preview production build
npm run lint                     # Check code style
```

---

## Tips & Tricks

1. **Faster reload**: Use `--reload` flag or keep servers running
2. **Debug mode**: Set `DEBUG=True` in backend
3. **Clear cache**: `npm cache clean --force` if npm issues
4. **Check ports**: `netstat -ano | findstr :5000` (Windows)
5. **Virtual env**: Always activate before running backend

---

Enjoy! 🚀
