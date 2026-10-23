import React from 'react'
import { AlertCircle, CheckCircle } from 'lucide-react'
import ConfidenceCard from './ConfidenceCard'
import './ConfidenceReport.css'

export default function ConfidenceReport({ results, config }) {
  if (!results) return null

  const { ocr, vlm, verification } = results

  return (
    <div className="confidence-report">
      <h2 className="report-title">Confidence & Extraction Results</h2>

      <div className="confidence-disclaimer">
        <AlertCircle size={18} />
        <p>Confidence scores represent model predictions. Manual review is recommended for critical decisions.</p>
      </div>

      <div className="confidence-grid">
        {/* OCR Confidence */}
        {config?.features?.ocr_enabled && (
          <ConfidenceCard
            title="Printed Text Extraction"
            subtitle="PaddleOCR"
            status={getStatus(ocr)}
            confidence={getConfidence(ocr)}
            message={getMessage(ocr)}
            details={getDetails(ocr)}
            icon={getIcon(ocr)}
          />
        )}

        {/* VLM Confidence */}
        {config?.features?.vlm_enabled && (
          <ConfidenceCard
            title="Handwritten Text Extraction"
            subtitle="Qwen2.5-VL"
            status={getStatus(vlm)}
            confidence={getConfidence(vlm)}
            message={getMessage(vlm)}
            details={getDetails(vlm)}
            icon={getIcon(vlm)}
          />
        )}

        {/* Verification Results */}
        {verification && (
          <>
            <ConfidenceCard
              title="Cheque Verification"
              subtitle="Authenticity Check"
              status={getStatus(verification.cheque)}
              confidence={getConfidence(verification.cheque)}
              message={getMessage(verification.cheque)}
              details={getDetails(verification.cheque)}
              icon={getIcon(verification.cheque)}
            />
            <ConfidenceCard
              title="Signature Verification"
              subtitle="Signature Analysis"
              status={getStatus(verification.signature)}
              confidence={getConfidence(verification.signature)}
              message={getMessage(verification.signature)}
              details={getDetails(verification.signature)}
              icon={getIcon(verification.signature)}
            />
          </>
        )}

        {/* No verification available */}
        {!verification && config?.features?.verification_enabled !== false && (
          <ConfidenceCard
            title="Cheque & Signature Verification"
            subtitle="Awaiting Model"
            status="UNAVAILABLE"
            confidence={null}
            message="Verification model is not yet available. Image quality check passed. Ready to verify once model is integrated."
            icon={<AlertCircle size={32} />}
          />
        )}
      </div>

      {/* Summary */}
      <div className="confidence-summary">
        <h3 className="summary-title">Processing Summary</h3>
        <div className="summary-items">
          <div className="summary-item">
            <span className="summary-label">Extraction Status:</span>
            <span className="summary-value">
              {ocr?.status === 'PENDING' || vlm?.status === 'PENDING'
                ? 'In Progress'
                : 'Complete'}
            </span>
          </div>
          {verification && (
            <div className="summary-item">
              <span className="summary-label">Verification Status:</span>
              <span className="summary-value">
                {verification.cheque?.status === 'UNAVAILABLE'
                  ? 'Pending Model Integration'
                  : 'Complete'}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function getStatus(result) {
  if (!result) return 'UNAVAILABLE'
  if (result.status === 'PENDING') return 'PENDING'
  if (result.status === 'ERROR') return 'ERROR'
  if (result.status === 'UNAVAILABLE') return 'UNAVAILABLE'
  if (result.status === 'DISABLED') return 'DISABLED'

  if (result.confidence !== null && typeof result.confidence === 'number') {
    if (result.confidence >= 0.8) return 'HIGH'
    if (result.confidence >= 0.6) return 'MEDIUM'
    return 'LOW'
  }

  return 'UNKNOWN'
}

function getConfidence(result) {
  if (!result || result.confidence === null) return null
  if (typeof result.confidence === 'number') {
    return Math.round(result.confidence * 100)
  }
  return null
}

function getMessage(result) {
  if (!result) return 'Not available'
  if (result.status === 'PENDING') return 'Processing...'
  if (result.status === 'ERROR') return `Error: ${result.error || 'Unknown error'}`
  if (result.status === 'UNAVAILABLE') return 'Model is not available'
  if (result.status === 'DISABLED') return 'Feature is disabled'
  if (result.message) return result.message
  return 'Status unknown'
}

function getDetails(result) {
  if (!result) return []

  const details = []
  if (result.text) {
    details.push({ label: 'Text extracted', value: `${result.text.split(' ').length} words` })
  }
  if (result.decision) {
    details.push({ label: 'Decision', value: result.decision })
  }
  return details
}

function getIcon(result) {
  if (!result) return <AlertCircle size={32} />

  if (result.status === 'PENDING') {
    return <div className="icon-spinner"></div>
  }
  if (result.status === 'ERROR' || result.status === 'UNAVAILABLE') {
    return <AlertCircle size={32} />
  }

  const status = getStatus(result)
  if (status === 'HIGH') return <CheckCircle size={32} />

  return <AlertCircle size={32} />
}
