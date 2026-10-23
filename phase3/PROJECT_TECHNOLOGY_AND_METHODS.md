# Cheque Field Extraction: Technologies, Methods and Algorithms

## 1. Goal

Extract the fields from Indian bank cheques:
- **Printed fields** (bank, account number, IFSC, MICR): PaddleOCR.
- **Handwritten fields**: date, amount in figures, amount in words, payee name.

The handwritten fields are the hard part, and most of the work below is about them.

## 2. Technologies

| Area | Technology | Used for |
|---|---|---|
| Language | Python 3.11 | All scripts |
| Image processing | OpenCV (`cv2`), NumPy, Pillow | Loading TIFF cheques, cropping field boxes, thresholding, line detection, PNG encoding |
| Deep learning | PyTorch | Training and running TrOCR |
| Models library | Hugging Face `transformers` | `TrOCRProcessor`, `VisionEncoderDecoderModel` |
| Printed-text OCR | PaddleOCR | Printed fields in `extract_fields.py` |
| Local LLM server | Ollama (CPU inference) | Serving Qwen2.5-VL 3B and 7B, and Granite 3.2 Vision |
| Vision-language models | Qwen2.5-VL 3B and 7B; Granite 3.2 Vision | Reading field crops zero-shot or few-shot |
| HTTP client | `requests` | Sending images and prompts to Ollama |
| Labeling and review | HTML pages with JavaScript, exported to CSV | Human review of proposed readings before they become training data |
| Viewing results | Static HTML pages opened in a browser | Results reports |

Hardware: Intel i5-1334U CPU, 16 GB RAM, integrated Intel Iris Xe graphics. There is no CUDA GPU, so all training and inference runs on the CPU.

## 3. Data

- **Source:** IDRBT cheque dataset (TIFF, 300 dpi), stored under `datasets/raw/idrbt/300/`.
- **Labels:** `data/annotations/metadata.json` holds verified field boxes (normalized x, y, width, height) for each labeled cheque.
- **Training data:** 45 cheques with confirmed field values, in `data/training/training_transcriptions_batch2.csv` to `batch10.csv`. Each row holds a cheque ID, a field, the confirmed value, and an unreadable flag.
- **Held-out test data:** 5 cheques with confirmed values in `data/evaluation/ground_truth_template.csv`. Their boxes are unverified candidates from template alignment (`heldout_box_candidates.json`), so scores on them depend on those boxes.
- **Excluded from amount training:** 309078, 309079, 309102 and 309117. The figures and words disagree on these cheques.
- **Known labeling conflict:** 100828 (held-out) has figures 22,23,000 but confirmed words "Two lakh Twenty three thousand".

## 4. Methods

### 4.1 Field cropping
- A field box is converted from normalized coordinates to pixels and padded by 3 pixels (`crop_box`, `extract_handwritten_v2.py`).
- Crops are padded to a square before the model sees them (`pad_to_square`).

### 4.2 Line cleanup and chunking (TrOCR path)
- **Otsu thresholding** (`cv2.threshold` with `THRESH_OTSU`) separates ink from background (`clean_line`).
- **Morphological opening** with a wide horizontal kernel removes stray marks and keeps text lines (`clean_line`).
- **Word-gap chunking** splits wide fields into word groups at large horizontal gaps (`chunk_line`), so each piece is short enough for TrOCR.
- **Date splitting:** the date box is cut into 8 equal cells, one per digit of DDMMYYYY. Each cell is read as one digit, and the digits are joined (`read_field` in `train_trocr_cheque.py`).

### 4.3 Constrained decoding (TrOCR)
- Token IDs that would violate the field type are banned with `bad_words_ids`:
  - amount in words and payee name: digit tokens banned;
  - amount in figures: letter tokens banned.

### 4.4 Amount in words from figures (rule-based)
- `amount_words.py` converts figures to words using the Indian numbering system (crore, lakh, thousand, hundred).
- Test on the 45 training cheques: 18 of 45 exact after normalization, mean character error rate 0.065. Most remaining differences are spelling variants on the cheques ("lacks", "fourty").
- Test on the 5 held-out cheques: 2 of 5 exact, character error rate 0.084. The model's own word readings scored 1 of 5, with character error rate 0.246.

### 4.5 Few-shot prompting (Qwen and Granite)
- No weights are changed. Each prompt contains the image crop plus up to 6 text-only examples of the same field, taken from the training transcriptions.
- **Leave-one-out:** for a training cheque, its own label is never in its prompt. Examples are sampled with a fixed seed per cheque.
- The prompt states the field format, for example "keep the '/-' suffix if present" (the model often drops it, which the scoring allows for).
- Decoding is deterministic (`temperature 0`), with `num_predict 40` and `num_ctx 2048` to stop runaway output.

### 4.6 TrOCR fine-tuning (`experiments/trocr_improved/train_improved.py`)
- Base model: `microsoft/trocr-base-handwritten`.
- Encoder frozen; only the decoder is trained.
- Optimizer: AdamW, learning rate 5e-6, batch size 4, 4 epochs, seed 2026.
- Split by cheque: 20% of training cheques are held out internally for validation. The best epoch is chosen on this validation loss.
- Trained on 146 samples from 45 cheques (118 for training, 28 for validation).

### 4.7 Scoring
- **Exact match:** strict string equality, and normalized equality (lowercase, no "/-", no punctuation, collapsed spaces).
- **Character error rate (CER):** Levenshtein distance divided by the length of the expected string.
- **Word error rate (WER):** Levenshtein distance over words, divided by the number of expected words.
- **Invalid output:** digits in a words or name field, or letters in a figures field.

## 5. Algorithms and models

| Component | Algorithm or model |
|---|---|
| Printed fields | PaddleOCR detection and recognition |
| Handwritten recognition (fine-tuned) | TrOCR: ViT image encoder, transformer text decoder, AdamW |
| Handwritten recognition (zero-shot and few-shot) | Qwen2.5-VL 3B and 7B (vision-language, inference only) |
| Amount to words | Rule-based Indian numbering conversion |
| Error metrics | Levenshtein edit distance (dynamic programming) |
| Batch training | Mini-batch gradient descent with frozen encoder |

## 6. Results so far (held-out, 5 cheques)

Scores are on 5 cheques, so one cheque changes a score by 20 percentage points. Treat them as indicative only.

| Model | Amount figures | Amount words | Payee name |
|---|---|---|---|
| TrOCR fine-tuned | 1/5, CER 0.20 | 0/5, CER 1.12 | 0/5, CER 1.12 |
| Qwen 3B zero-shot | 0/5, CER 0.26 | 0/5, CER 0.43 | 2/5, CER 0.08 |
| Qwen 7B zero-shot | 0/5, CER 0.19 | 1/5, CER 0.31 | 3/5, CER 0.08 |
| Qwen 7B few-shot | 4/5, CER 0.02 | 1/5, CER 0.13 | 3/5, CER 0.05 |
| Qwen 3B few-shot (normalized) | 4/5, CER 0.02 | 1/5, CER 0.25 | 2/5, CER 0.22 |
| Granite 3.2 Vision few-shot | 0/5 | 0/5 | 0/5 |
| Words derived from figures (3B) | n/a | 2/5, CER 0.08 | n/a |

Granite 3.2 Vision was rejected: it often copied the example list instead of reading the cheque, and sometimes said the image contained no cheque.

A 45-cheque evaluation of Qwen 3B few-shot is in progress (`experiments/vision_qwen/fewshot3b_batch_*.log`). Its results are not yet reported.

## 7. Limitations

- The held-out set is 5 cheques with unverified boxes, so the scores have wide error bars.
- TrOCR overfits on 45 cheques and does not generalize to the held-out cheques.
- Qwen models are not trained on cheques. Gains come from prompting, and they run slowly on CPU.
- Amount figures with a missing digit, such as 42 for 44, flow straight into the words rule.
- Labels for some cheques conflict (for example 100828 and the four excluded cheques).

## 8. Project layout

- `extract_fields.py`: printed fields (PaddleOCR) and the handwritten pipeline entry point.
- `extract_handwritten_v2.py`: crops, cleanup, chunking, TrOCR recognition.
- `train_trocr_cheque.py`: TrOCR fine-tuning and evaluation on the training and held-out sets.
- `amount_words.py`: figures-to-words conversion.
- `score_words_from_figures.py`: scores words derived from figures.
- `experiments/trocr_improved/`: improved TrOCR training with cheque-level validation.
- `experiments/vision_qwen/`: Qwen zero-shot and few-shot evaluation, and report generation.
- `data/`: annotations, training transcriptions, evaluation sets.
- `models/`: trained TrOCR checkpoints.
