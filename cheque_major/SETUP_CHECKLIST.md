# Setup Checklist

Complete checklist for getting the Cheque Verification System running.

## Pre-Setup Requirements

### System Requirements
- [ ] Python 3.8+ installed
- [ ] Node.js 16+ installed
- [ ] npm 8+ installed
- [ ] Git installed (optional, for version control)
- [ ] 500MB+ free disk space

**Verify installations:**
```bash
python --version
node --version
npm --version
```

### File Structure
- [ ] Project location: `D:\cheque_major` (or your chosen path)
- [ ] All files created (run `/docs/ARCHITECTURE.md` for verification)
- [ ] No missing files or directories

## Backend Setup

### Step 1: Navigate to Backend
```bash
cd D:\cheque_major\backend
```
- [ ] Terminal shows `D:\cheque_major\backend>` prompt

### Step 2: Create Virtual Environment
```bash
python -m venv venv
```
- [ ] `venv/` directory created
- [ ] Contains `Scripts/`, `Lib/`, `pyvenv.cfg`

### Step 3: Activate Virtual Environment
**Windows:**
```bash
venv\Scripts\activate
```
**macOS/Linux:**
```bash
source venv/bin/activate
```
- [ ] Terminal shows `(venv)` prefix
- [ ] Example: `(venv) D:\cheque_major\backend>`

### Step 4: Install Dependencies
```bash
pip install -r requirements.txt
```
- [ ] Flask==3.0.0 installed ✓
- [ ] Flask-CORS==4.0.0 installed ✓
- [ ] opencv-python==4.8.1.78 installed ✓
- [ ] numpy==1.24.3 installed ✓
- [ ] requests==2.31.0 installed ✓
- [ ] All packages installed successfully (no errors)

### Step 5: Create Uploads Directory
```bash
mkdir uploads
```
- [ ] `backend/uploads/` directory exists
- [ ] Directory is empty
- [ ] Directory is readable/writable

### Step 6: Run Backend Server
```bash
python app.py
```
- [ ] Output shows: `* Running on http://127.0.0.1:5000`
- [ ] No error messages in console
- [ ] Ctrl+C stops the server gracefully
- [ ] Leave this server running for next steps ✓

**Backend Status:** ✅ Ready

---

## Frontend Setup

### Step 1: Open New Terminal
- [ ] New terminal window opened
- [ ] Previous terminal still running backend

### Step 2: Navigate to Frontend
```bash
cd D:\cheque_major\frontend
```
- [ ] Terminal shows `D:\cheque_major\frontend>` prompt

### Step 3: Install Dependencies
```bash
npm install
```
- [ ] `node_modules/` directory created
- [ ] `package-lock.json` created
- [ ] React 18.2.0 installed ✓
- [ ] Vite installed ✓
- [ ] All packages installed (may take 2-3 minutes)
- [ ] No error messages (warnings OK)

### Step 4: Start Development Server
```bash
npm run dev
```
- [ ] Output shows: `Local:   http://localhost:3000/`
- [ ] Output shows: `ready in XYZ ms`
- [ ] No error messages
- [ ] Leave this server running

**Frontend Status:** ✅ Ready

---

## Verification

### Both Servers Running?
- [ ] Backend terminal: `(venv) D:\cheque_major\backend>` with Flask running
- [ ] Frontend terminal: Shows Vite dev server on port 3000
- [ ] No error messages in either terminal

### Browser Test
- [ ] Open `http://localhost:3000` in browser
- [ ] Page loads without errors
- [ ] See "Cheque Verification" header with teal background
- [ ] Upload area is visible
- [ ] File upload button is clickable

### API Health Check
**In new terminal, run:**
```bash
curl http://localhost:5000/api/health
```
Or use browser: `http://localhost:5000/api/health`

- [ ] Returns JSON with `"status": "healthy"`
- [ ] Shows service status (ocr, vlm, verification)
- [ ] No errors or connection refused

### Config Check
**In browser or terminal:**
```
http://localhost:5000/api/config
```
- [ ] Returns JSON with system configuration
- [ ] Shows quality_thresholds
- [ ] Shows quality_bands
- [ ] Shows feature flags (all disabled initially)

**System Status:** ✅ Fully Operational

---

## Image Upload Test

### Prepare Test Image
- [ ] Have a cheque image ready (JPG, PNG, or BMP)
- [ ] Image format: JPG, PNG, GIF, BMP, or WEBP
- [ ] File size: Under 20MB
- [ ] Recommended: High-quality, well-lit cheque image

### Upload Image
1. [ ] Go to `http://localhost:3000`
2. [ ] Drag image to upload area OR click to browse
3. [ ] Wait for processing spinner
4. [ ] Quality report appears below upload area

### Verify Results
- [ ] Upload ID displayed (e.g., `20240115_103000_cheque.jpg`)
- [ ] File size shown (MB)
- [ ] Quality score displays (0-100)
- [ ] Score gauge shows green/yellow/red indicator
- [ ] Quality band shown (GOOD/ACCEPTABLE/POOR)
- [ ] 6 metrics visible (Resolution, Sharpness, Brightness, Contrast, Skew, Text Visibility)
- [ ] Each metric shows score and status
- [ ] Recommendations displayed (if any issues)
- [ ] Image preview visible in left panel

### Test Different Images
- [ ] Clear, bright image → High score (80+)
- [ ] Blurry image → Low sharpness score
- [ ] Dark image → Low brightness score
- [ ] Rotated image → Skew warning
- [ ] Low resolution → Low resolution score

**Upload Testing:** ✅ Complete

---

## Troubleshooting

### Backend Won't Start
- [ ] Check Python version: `python --version`
- [ ] Check virtual environment active: `(venv)` in prompt
- [ ] Check port 5000 is free: `netstat -ano | findstr :5000`
- [ ] Check requirements installed: `pip list | grep Flask`
- [ ] Check `uploads/` directory exists: `dir uploads`

### Frontend Won't Start
- [ ] Check Node.js version: `node --version`
- [ ] Check `node_modules/` exists: `dir node_modules`
- [ ] Check port 3000 is free: `netstat -ano | findstr :3000`
- [ ] Clear cache: `npm cache clean --force`
- [ ] Reinstall: `rm -r node_modules package-lock.json && npm install`

### Connection Errors
- [ ] Check both servers are running
- [ ] Check ports: Backend 5000, Frontend 3000
- [ ] Check vite.config.js proxy: should point to `http://localhost:5000`
- [ ] Check firewall isn't blocking ports
- [ ] Try: http://localhost:5000/api/health directly

### Image Upload Fails
- [ ] Check file format (JPG/PNG/GIF/BMP/WEBP)
- [ ] Check file size < 20MB
- [ ] Check `uploads/` directory writable
- [ ] Check browser console (F12) for errors
- [ ] Check backend terminal for error messages

### Poor Quality Scores
This is normal if:
- [ ] Image is blurry
- [ ] Image is too dark
- [ ] Image is rotated
- [ ] Image is low resolution
- [ ] See recommendations for improvement

---

## Configuration (Optional)

### Change Quality Thresholds
Edit `backend/config.py` to adjust:
- Minimum image dimensions
- Sharpness threshold
- Brightness range
- Contrast minimum
- Skew tolerance
- [ ] Restart backend after changes

### Change Quality Weights
Edit `backend/config.py`:
```python
QUALITY_WEIGHTS = {
    'sharpness': 0.35,  # Increase from 0.25
    # ... adjust others (must sum to 1.0)
}
```
- [ ] Restart backend after changes
- [ ] Test with sample images

### Enable Feature Flags (Future)
When models are available, update `backend/config.py`:
```python
ENABLE_PADDLE_OCR = True
ENABLE_QWEN_VLM = True
ENABLE_VERIFICATION_MODEL = True
```
- [ ] Restart backend
- [ ] Models appear in frontend

---

## Stopping the Servers

### Graceful Shutdown
1. [ ] In backend terminal: Press `Ctrl+C`
   - Should show: `KeyboardInterrupt` then shutdown
2. [ ] In frontend terminal: Press `Ctrl+C`
   - Should show: clean shutdown

### Clean Up (Optional)
```bash
# Keep database clean
cd backend
rm -rf uploads/*  # Clear test uploads

# Free space (optional)
cd frontend
rm -rf node_modules  # Can reinstall with npm install
```

---

## Success Criteria

### ✅ System is Ready When:
- [x] Backend server running on port 5000
- [x] Frontend server running on port 3000
- [x] Browser loads `http://localhost:3000` without errors
- [x] API health check returns 200 OK
- [x] Can upload images successfully
- [x] Quality analysis displays correctly
- [x] No console errors in terminal
- [x] No browser console errors (F12)

### ✅ Ready for Next Steps:
- [x] All items above checked
- [x] Test images upload successfully
- [x] Quality scores make sense
- [x] UI displays correctly on your screen
- [x] Documentation reviewed (README.md)

---

## Next Steps

### Phase 1: Integration
1. [ ] Review `docs/ARCHITECTURE.md` for technical details
2. [ ] Read integration guide in `README.md`
3. [ ] Prepare PaddleOCR for integration
4. [ ] Prepare Qwen2.5-VL for integration
5. [ ] Prepare your verification model

### Phase 2: Testing
1. [ ] Test with IDRBT dataset images
2. [ ] Verify quality scores are calibrated
3. [ ] Adjust thresholds as needed
4. [ ] Test model integrations

### Phase 3: Deployment
1. [ ] Build frontend: `npm run build`
2. [ ] Deploy backend with Gunicorn
3. [ ] Deploy frontend to CDN
4. [ ] Configure production domains
5. [ ] Set up monitoring

---

## Support Resources

| Issue | Resource |
|-------|----------|
| Setup questions | `QUICKSTART.md` |
| API documentation | `README.md` |
| Technical details | `docs/ARCHITECTURE.md` |
| File structure | `PROJECT_STRUCTURE.md` |
| Implementation summary | `IMPLEMENTATION_SUMMARY.md` |
| Troubleshooting | Section above |

---

## Final Verification

```bash
# Terminal 1: Backend status
curl http://localhost:5000/api/health

# Terminal 2: Frontend status (if server running)
# Browser: http://localhost:3000

# Backend uptime check
# Should show active connections and requests in terminal
```

**Checklist Complete:** ✅

---

**You're all set!** 🎉

The system is now ready for:
- Image quality testing
- Model integration
- Production deployment

See `QUICKSTART.md` for rapid reference and `README.md` for detailed documentation.
