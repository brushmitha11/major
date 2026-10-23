# Automated Extraction of Handwritten Fields from Indian Bank Cheques

## 1. Introduction

Cheques remain a common payment instrument in India, and each one must be checked against several fields before it is processed. Some fields are printed, such as the bank name, account number, IFSC code and MICR line. Others are handwritten by the account holder: the date, the amount in figures, the amount in words, and the payee name. Printed fields are generally easy for standard OCR engines. Handwritten fields are not, because the writing varies widely between people, cheques are often photographed or scanned with noise, and the amount appears twice in two different forms that must agree.

This project builds a pipeline that reads the handwritten fields from scanned cheques. The printed fields are read with PaddleOCR. The handwritten fields are read in three ways that are compared against each other:

1. A fine-tuned TrOCR transformer model.
2. Zero-shot and few-shot prompting of Qwen2.5-VL vision-language models (3B and 7B parameters), served locally through Ollama.
3. A rule that derives the amount in words from the amount in figures.

The work is constrained by hardware. The machine has no CUDA GPU, only 16 GB of RAM and an integrated graphics processor, so every model runs on the CPU. This shapes the choice of methods: fine-tuning a large vision-language model is not practical, so the project relies on prompting with labeled examples, deterministic rules, and a small fine-tuned model for comparison.

The dataset is the IDRBT cheque collection, scanned at 300 dpi. Field locations are labeled in the dataset metadata, and field values were confirmed by hand before use in training or evaluation.

## 2. Methodology

### 2.1 Data preparation

- **Field boxes.** Each cheque has verified bounding boxes for every field, stored as normalized coordinates (x, y, width, height). Each box is converted to pixels and padded by three pixels before cropping.
- **Confirmed values.** Proposed readings were reviewed in batches. A reviewer corrected each value or marked it unreadable, and the confirmed values were exported to CSV. Only confirmed values are used for training or evaluation.
- **Splits.** Forty-five cheques with confirmed handwritten values form the training set (batches 2 to 10). Five cheques form the held-out test set, with confirmed values. Their boxes are candidate boxes from template alignment, not verified, so their scores carry extra uncertainty.
- **Exclusions.** Four cheques (309078, 309079, 309102, 309117) are excluded from amount training because their figures and words disagree. One held-out cheque (100828) also has a conflict between its figures and its confirmed words, and this is noted in the results.

### 2.2 Image processing

- Each crop is converted to grayscale. For the TrOCR path, Otsu thresholding separates ink from background, and a morphological opening with a wide horizontal kernel removes small marks.
- Wide fields are split at large horizontal gaps into word groups, so each piece is short enough for the recognizer.
- The date box is divided into eight equal cells, one for each digit of DDMMYYYY. Each cell is read as a single digit.

### 2.3 Model approaches

**TrOCR fine-tuning.** The base model is Microsoft's TrOCR-base-handwritten, a vision encoder with a transformer text decoder. The encoder is frozen and only the decoder is trained with AdamW at a learning rate of 5e-6, for four epochs and batch size four. Validation is split by cheque, not by sample, so the same cheque never appears in both training and validation. The checkpoint with the lowest validation loss is kept. Two constraints are applied during decoding: digit tokens are banned for words and names, and letter tokens are banned for figures.

**Qwen2.5-VL zero-shot.** The 3B and 7B models read each crop from a prompt that states the field, with no examples.

**Qwen2.5-VL few-shot.** Each prompt contains the crop and up to six text-only examples of the same field, drawn from the training transcriptions. For training cheques, a leave-one-out rule keeps a cheque's own label out of its prompt, so no answer is given to the model. Examples are sampled with a fixed seed per cheque. The prompt asks for the field's exact format. Decoding is deterministic, and output length is capped to prevent runaway generations.

**Rule-based amount in words.** The amount in figures is converted to words using the Indian numbering system (crore, lakh, thousand, hundred). Because the words are fully determined by the figures, this derivation avoids reading the handwritten words at all.

**Granite 3.2 Vision.** This model was tested with the same few-shot setup and rejected. It often returned the example list in place of a reading, and in some cases said the image contained no cheque.

### 2.4 Evaluation

Each field is scored in three ways:

- **Exact match,** both strict and after normalization. Normalization lowercases the text, removes the "/-" suffix and punctuation, and collapses spaces. Normalization is needed because the model is not required to copy the "/-" suffix.
- **Character error rate (CER),** the Levenshtein edit distance divided by the length of the expected text.
- **Word error rate (WER),** the same measure over words.

An invalid-output count flags digits in word or name fields and letters in figure fields.

### 2.5 Experimental procedure

1. Evaluate each model on the five held-out cheques with the same crops.
2. Evaluate the few-shot Qwen models on all 45 training cheques with leave-one-out prompting, in batches of ten cheques. Each batch's results are saved as they are produced, so a stopped run resumes without repeating finished reads.
3. Compare the words derived from figures with the words the model reads directly, on the same cheques.

## 3. Limitations

- The held-out set has five cheques, so one cheque changes a score by 20 percentage points. Results are indicative only.
- TrOCR overfits on 45 cheques and did not generalize to the held-out set.
- The Qwen models were not trained on cheques. Their gains come from prompting, and inference on the CPU is slow, which limits how many configurations can be tested.
- Errors in the figures carry straight into the derived words. For example, a misread 42 for 44 produces the wrong amount in words.
- Some labels conflict with each other, which caps the accuracy that can be measured.

## 4. Status

Held-out results are in the project technology document. The 45-cheque few-shot evaluation for Qwen 2.5-VL 3B is in progress, with batch 1 complete. Final results will be added once all batches finish.
