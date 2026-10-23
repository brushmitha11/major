import React from 'react'
import './ExtractedText.css'

const FIELD_LABELS = [
  ['bank_name', 'Bank name'],
  ['cheque_number', 'Cheque number'],
  ['micr_code', 'MICR code'],
  ['account_number', 'Account number'],
  ['date', 'Date'],
  ['payee_name', 'Payee name'],
  ['amount_figures', 'Amount in figures'],
  ['amount_words', 'Amount in words'],
  ['ifsc_code', 'IFSC code'],
]

export default function ExtractedText({ results }) {
  if (!results?.fields) return null
  return (
    <div className="extracted-text">
      <table>
        <tbody>
          {FIELD_LABELS.map(([key, label]) => (
            <tr key={key}>
              <th>{label}</th>
              <td>{results.fields[key] ?? '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
