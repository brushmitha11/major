# Cheque Field Labeling Guide

Scope: the 78 real reference cheques listed in `data/dataset_tags/labeling_queue.csv`.
Do not label synthetic forgeries. Their edited fields make their boxes unreliable.

## Classes

| Class | What to box |
|---|---|
| cheque_number | The cheque number digits. If printed outside the MICR line, box that number. If it appears only inside the MICR line, box just its digits inside the MICR line. |
| micr_code | The full MICR line, including any cheque number printed inside it. Overlapping boxes with cheque_number are allowed. |
| amount_words | The handwritten or printed amount-in-words line, for example "One lakh Sixty thousand". Box the words only, not the "Rupees" label. |
| ifsc_code | The printed IFSC code, for example "UTIB0000426". Box the code only, not the "IFSC CODE" label. |
| bank_name | The printed bank name text or logo wording. |
| account_number | The printed account number digits, not the MICR line. |
| date | The date digits and separators, handwritten or printed. |
| payee_name | Only the handwritten or printed name on the payee line. Exclude the "Pay" label. |
| amount | The figures amount box only. Exclude the amount-in-words line. |
| signature | All strokes of the signature. |
| micr_code | The full MICR line at the bottom. |

## Status per field

- **detected**: the field is visible and readable. Draw one box and check it.
- **absent**: the field is not on this cheque.
- **unreadable**: the field is present but too blurred, cropped, or obscured to label reliably. Add a note.
- **not_applicable**: the template has no such field.

## Box rules

- Draw one box per field. Keep it tight, with about 1 to 2 pixels of margin.
- Boxes may overlap, for example a signature over the payee line.
- If a field is cut off at the image edge, mark it unreadable and note "cropped".
- Do not box the cheque border, printed lines, or stamps unless they are part of the field.

## Verification

- A box counts as verified only after a person confirms it in the tool.
- Record the annotator name or initials in the notes.
- If unsure, use unreadable and write what you could not decide.
