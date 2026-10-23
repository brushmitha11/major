# 🔍 Cheque Image Quality Assessment System

## Overview

This system provides two ways to assess cheque image quality:
1. **Web Application** - Upload and check individual cheque images with visual feedback
2. **Batch Analysis** - Analyze all images in the dataset and generate quality reports

---

## 🚀 Quick Start

### Start Backend API
```bash
cd C:\Users\Rushmitha\OneDrive\Desktop\cheque\phase3
pip install fastapi uvicorn opencv-python numpy pandas
python api/main.py
```
✅ Backend runs on: `http://localhost:8000`

### Start Frontend Application
```bash
cd C:\Users\Rushmitha\OneDrive\Desktop\cheque\phase3\web
npm install
npm run dev
```
✅ Frontend runs on: `http://localhost:5173`

---

## 📱 Web Application Usage

### Upload and Check a Cheque Image

1. **Open** the frontend: `http://localhost:5173`
2. **Upload** a cheque image by:
   - Clicking "Click to upload"
   - Or dragging and dropping an image
3. **Click** "Assess Image Quality"
4. **View Quality Status Popup**:

   **If Quality is GOOD (✅)**
   - Shows: Quality Score (e.g., 85.3%)
   - Message: "Image meets quality standards"
   - Options:
     - ✅ **Proceed with Verification** - Continue to detailed analysis
     - Close - Return to upload

   **If Quality is NOT GOOD (⚠️)**
   - Shows: Quality Score with status (UNCERTAIN or POOR)
   - Displays: Issues detected (e.g., "Low contrast detected")
   - Recommendation: How to improve
   - Option: Try Another Image

### Component Scores
After proceeding from quality check, view:
- **Sharpness** - Image clarity and focus
- **Contrast** - Difference between light and dark
- **Brightness** - Overall image illumination
- **Skew** - Document alignment/rotation
- **Completeness** - Cheque content coverage

---

## 📊 Batch Dataset Analysis

### Analyze All Images in Dataset

```bash
cd C:\Users\Rushmitha\OneDrive\Desktop\cheque\phase3
python analyze_dataset_quality.py
```

### Output Files Generated

1. **dataset_quality_report.json** - Detailed report with all metrics
2. **dataset_quality_report.csv** - Easy-to-view spreadsheet format

### Console Output Example

```
🔍 Starting Dataset Quality Analysis...
📁 Dataset root: C:\...\cheque\datasets

[1/4] Analyzing: 100829_amount_forgery_comparison.jpg
  ✓ Score: 78.5% | Status: GOOD

📈 DATASET QUALITY STATISTICS
Total images analyzed: 4
Quality Status Distribution:
  GOOD: 3 images (75.0%)
  UNCERTAIN: 1 image (25.0%)

Quality Score Statistics:
  Average: 0.815 (81.5%)
  Min: 0.623 (62.3%)
  Max: 0.924 (92.4%)
  Median: 0.798 (79.8%)

🌟 TOP 5 BEST QUALITY IMAGES
  100829_amount_forgery_comparison.jpg: 92.4% (GOOD)

⚠️  BOTTOM 5 WORST QUALITY IMAGES
  309135_multi_field_forgery_comparison.jpg: 62.3% (UNCERTAIN)
```

---

## 🎨 UI Features

### Visual Feedback
- **Green (GOOD)**: Quality score 0.7+, ready for verification
- **Yellow (UNCERTAIN)**: Quality score 0.4-0.7, needs review
- **Red (POOR)**: Quality score <0.4, upload new image

### Quality Metrics Shown
- Overall quality score (0-100%)
- 5 component breakdown with progress bars
- Specific issues and recommendations
- User-friendly messages explaining results

---

## 📈 Quality Metrics Explanation

| Metric | What It Measures |
|--------|------------------|
| **Sharpness** | How clear and in-focus the cheque is |
| **Contrast** | Difference between text/numbers and background |
| **Brightness** | Overall illumination level (not too dark/bright) |
| **Skew** | Whether cheque is straight (not rotated/tilted) |
| **Completeness** | Whether all parts of cheque are visible |

---

## ✅ Quality Thresholds

| Status | Score Range | Recommendation |
|--------|------------|-----------------|
| **GOOD** | 0.70 - 1.00 | Proceed with verification |
| **UNCERTAIN** | 0.40 - 0.69 | May have minor issues; consider re-uploading |
| **POOR** | 0.00 - 0.39 | Do not proceed; requires new image |

---

## 📝 Example Workflow

### Single Image Upload
```
1. Open http://localhost:5173
2. Upload cheque_scan.jpg
3. Click "Assess Image Quality"
4. See popup: "Image Quality is GOOD! ✅"
5. Click "Proceed with Verification"
6. View detailed component scores
7. Ready for next processing step
```

### Batch Analysis
```
1. Run: python analyze_dataset_quality.py
2. See progress: [1/100] Analyzing image.jpg
3. Get summary statistics
4. Review: dataset_quality_report.csv
5. Identify problem images
6. Use insights to improve collection process
```

---

## 🔧 Troubleshooting

### Backend Won't Start
```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Install missing dependencies
pip install fastapi uvicorn opencv-python numpy pandas
```

### Frontend Won't Start
```bash
# Clear node_modules and reinstall
rmdir /s node_modules package-lock.json
npm install
npm run dev
```

### Images Not Loading
- Ensure images are in: `C:\Users\Rushmitha\OneDrive\Desktop\cheque\datasets\`
- Supported formats: JPG, PNG, TIFF, BMP
- Check file permissions and ensure files are not corrupted

### Quality Engine Errors
```bash
# Ensure Python dependencies are installed
pip install --upgrade opencv-python numpy pandas
```

---

## 📊 Report Files Format

### JSON Report (`dataset_quality_report.json`)
```json
{
  "analysis_timestamp": "2026-10-09T10:00:00",
  "total_images": 4,
  "status_distribution": {
    "GOOD": 3,
    "UNCERTAIN": 1
  },
  "quality_statistics": {
    "mean": 0.815,
    "min": 0.623,
    "max": 0.924,
    "median": 0.798
  },
  "detailed_results": [...]
}
```

### CSV Report (`dataset_quality_report.csv`)
```
file_name,quality_score,quality_status,sharpness,contrast,...
image1.jpg,0.924,GOOD,0.95,0.89,...
image2.jpg,0.623,UNCERTAIN,0.65,0.52,...
```

---

## 🎯 Next Steps

After quality assessment:
1. **GOOD images** → Proceed to cheque verification (field detection, amount reading, etc.)
2. **UNCERTAIN images** → Review issues and consider re-uploading
3. **POOR images** → Reject and request new image with better quality

---

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review error messages in the popup
3. Check backend logs: `http://localhost:8000/docs`

---

**Last Updated**: 2026-10-09
