"""
Cheque Field Annotation UI - Flask Backend
Serves images and manages annotation state
"""
import sys
from pathlib import Path

# Determine paths based on script location
SCRIPT_DIR = Path(__file__).parent  # phase3/
PROJECT_ROOT = SCRIPT_DIR.parent    # cheque/
TRAIN_CSV = PROJECT_ROOT / "datasets" / "splits" / "train.csv"
IMAGES_ROOT = PROJECT_ROOT / "datasets"

sys.path.insert(0, str(SCRIPT_DIR))

from flask import Flask, render_template, request, jsonify, send_file
import json
import base64
import cv2
import numpy as np
from data.annotations.annotation_manager import AnnotationManager, AnnotationValidator, ImageAnnotation, FieldAnnotation
from extraction.cheque_field_extractor_v2 import ChequeFieldExtractorV2

app = Flask(__name__, static_url_path='/static', template_folder='.')

# Initialize extractor for heuristic suggestions
try:
    EXTRACTOR = ChequeFieldExtractorV2()
    print("[OK] Extractor loaded for heuristic suggestions")
except Exception as e:
    EXTRACTOR = None
    print(f"[WARNING] Extractor not available: {e}")

def get_uid(img_path):
    """Extract unique ID from image path"""
    p = Path(img_path)
    stem = p.stem
    if '_forgery' in stem.lower() or '_' in stem:
        return stem
    parts = stem.split()
    if parts:
        return f"{parts[-1]}_reference"
    return stem

def detect_region_content(region):
    """Heuristic: detect if region has text-like content"""
    if region.size == 0:
        return 0.0
    gray = cv2.cvtColor(region, cv2.COLOR_RGB2GRAY) if len(region.shape) == 3 else region
    edges = cv2.Canny(gray, 50, 150)
    edge_ratio = np.sum(edges > 0) / edges.size if edges.size > 0 else 0
    contrast = np.std(gray) / 256.0
    score = min((edge_ratio * 0.6 + contrast * 0.4), 1.0)
    return score

# Initialize manager (MANDATORY train.csv validation)
try:
    MANAGER = AnnotationManager(
        output_dir="data/annotations",
        train_csv=str(TRAIN_CSV)
    )
    TRAIN_IMAGES = list(MANAGER.train_images.keys())

    # Build mapping from unique_id to image_path
    UID_TO_IMAGE = {}
    for image_path in TRAIN_IMAGES:
        uid = get_uid(image_path)
        UID_TO_IMAGE[uid] = image_path

    print(f"[OK] Loaded {len(TRAIN_IMAGES)} training images")
    print(f"[OK] Built UID mapping for {len(UID_TO_IMAGE)} unique images")
except Exception as e:
    print(f"FATAL: {e}")
    sys.exit(1)

@app.route('/api/suggest/<uid>', methods=['GET'])
def suggest_boxes(uid):
    """Generate heuristic box suggestions for image (not verified)"""
    try:
        if not EXTRACTOR or uid not in UID_TO_IMAGE:
            return jsonify({'suggestions': [], 'note': 'Suggestions unavailable'}), 200

        actual_path = UID_TO_IMAGE[uid]
        full_path = PROJECT_ROOT / actual_path

        if not full_path.exists():
            return jsonify({'error': 'Image not found'}), 404

        img = cv2.imread(str(full_path))
        if img is None:
            return jsonify({'error': 'Cannot decode image'}), 400

        # Convert BGR to RGB for consistency
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        height, width = img.shape[:2]

        suggestions = []
        for field_name, field_def in EXTRACTOR.FIELD_DEFINITIONS.items():
            x_min, y_min, x_max, y_max = field_def['region']
            px_min = max(0, int(x_min * width))
            py_min = max(0, int(y_min * height))
            px_max = min(width, int(x_max * width))
            py_max = min(height, int(y_max * height))

            if px_max <= px_min or py_max <= py_min:
                continue

            region = img_rgb[py_min:py_max, px_min:px_max]
            content_score = detect_region_content(region)

            if content_score > 0.05:
                suggestions.append({
                    'field': field_name,
                    'box': [x_min, y_min, x_max - x_min, y_max - y_min],
                    'confidence': round(content_score, 2),
                    'description': field_def['description']
                })

        return jsonify({
            'uid': uid,
            'suggestions': suggestions,
            'note': 'Heuristic suggestions based on template regions. All require manual verification.',
            'method': 'Template-based content detection'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

FIELD_INFO = {
    'cheque_number': {'class': 0, 'description': 'Cheque number'},
    'bank_name': {'class': 1, 'description': 'Bank name'},
    'account_number': {'class': 2, 'description': 'Account number'},
    'date': {'class': 3, 'description': 'Date'},
    'payee_name': {'class': 4, 'description': 'Payee name'},
    'amount': {'class': 5, 'description': 'Amount'},
    'signature': {'class': 6, 'description': 'Signature'},
    'micr_code': {'class': 7, 'description': 'MICR code'},
    'amount_words': {'class': 8, 'description': 'Amount in words'},
    'ifsc_code': {'class': 9, 'description': 'IFSC code'},
}

@app.route('/')
def index():
    return render_template('annotation_ui.html')

@app.route('/api/images', methods=['GET'])
def get_images_list():
    """Get list of all training images"""
    return jsonify({
        'total': len(TRAIN_IMAGES),
        'images': [{'path': img, 'uid': get_uid(img), 'parent_id': MANAGER.train_images[img].get('parent_id', ''), 'bank': MANAGER.train_images[img].get('bank', '')} for img in TRAIN_IMAGES]
    })

@app.route('/api/image/<uid>', methods=['GET'])
def get_image(uid):
    """Get image file as base64 using unique_id"""
    try:
        # Look up actual image path from UID mapping
        if uid not in UID_TO_IMAGE:
            return jsonify({'error': f'Unknown image ID: {uid}'}), 404

        actual_path = UID_TO_IMAGE[uid]
        # train.csv paths already include "datasets/", so use PROJECT_ROOT directly
        full_path = PROJECT_ROOT / actual_path

        if not full_path.exists():
            return jsonify({'error': f'Image file not found: {full_path}'}), 404

        img = cv2.imread(str(full_path))
        if img is None:
            return jsonify({'error': 'Cannot decode image'}), 400
        
        _, buffer = cv2.imencode('.jpg', img)
        b64 = base64.b64encode(buffer).decode('utf-8')

        # Get metadata from train.csv
        metadata = MANAGER.train_images.get(actual_path, {})

        return jsonify({
            'uid': uid,
            'image_path': actual_path,
            'image': f'data:image/jpeg;base64,{b64}',
            'width': img.shape[1],
            'height': img.shape[0],
            'parent_id': metadata.get('parent_id', ''),
            'bank': metadata.get('bank', '')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/annotation/<unique_id>', methods=['GET'])
def get_annotation(unique_id):
    """Get existing annotation"""
    ann = MANAGER.get_annotation(unique_id)
    if not ann:
        return jsonify({'status': 'new'})
    
    return jsonify({
        'status': ann.status,
        'image_path': ann.image_path,
        'fields': {
            fname: {
                'status': f.status,
                'box': f.box,
                'verified': f.verified,
                'notes': f.notes
            }
            for fname, f in ann.fields.items()
        }
    })

@app.route('/api/annotation/save', methods=['POST'])
def save_annotation():
    """Save annotation"""
    try:
        data = request.json
        unique_id = data.get('unique_id')
        image_path = data.get('image_path')
        parent_id = data.get('parent_id')
        bank = data.get('bank')
        fields_data = data.get('fields', {})
        save_as = data.get('save_as', 'draft')  # draft, in_progress, complete
        
        # Get or create annotation
        ann = MANAGER.get_annotation(unique_id)
        if not ann:
            ann = MANAGER.create_annotation(image_path, unique_id, parent_id, bank)
            if not ann:
                return jsonify({'error': 'Cannot create annotation'}), 400
            MANAGER.register_annotation(ann)
        
        # Update fields
        for fname, fdata in fields_data.items():
            ann.fields[fname] = FieldAnnotation(
                fname,
                fdata.get('status', 'draft'),
                fdata.get('box'),
                fdata.get('verified', False),
                fdata.get('notes')
            )
        
        # Save based on state
        if save_as == 'draft':
            success = MANAGER.save_draft(ann)
        elif save_as == 'in_progress':
            success = MANAGER.save_in_progress(ann)
        elif save_as == 'complete':
            success = MANAGER.mark_complete(unique_id)
        else:
            success = False
        
        if success:
            return jsonify({'status': 'saved', 'message': f'Saved as {save_as}'})
        else:
            return jsonify({'error': f'Save failed'}), 500
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/progress', methods=['GET'])
def get_progress():
    """Get annotation progress"""
    summary = MANAGER.get_progress_summary()
    return jsonify(summary)

@app.route('/api/proposal/<uid>', methods=['GET'])
def get_proposal(uid):
    """Unverified alignment proposal for a training cheque (read-only)"""
    proposals_file = PROJECT_ROOT / 'phase3' / 'data' / 'pseudo_labels' / 'alignment_proposals.json'
    if uid not in UID_TO_IMAGE or not proposals_file.exists():
        return jsonify({'status': 'none'})
    entry = json.loads(proposals_file.read_text(encoding='utf-8')).get(uid)
    if not entry or entry.get('status') != 'aligned':
        return jsonify({'status': 'none'})
    fields = {
        name: {'status': 'detected', 'box': f['box'], 'is_verified': False}
        for name, f in entry['fields'].items() if f.get('box')
    }
    return jsonify({'status': 'proposal', 'template_uid': entry.get('template_uid'), 'fields': fields})

@app.route('/api/fields', methods=['GET'])
def get_fields():
    """Get field definitions"""
    return jsonify(FIELD_INFO)

if __name__ == '__main__':
    print("Starting annotation UI backend...")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=False, port=5000)
