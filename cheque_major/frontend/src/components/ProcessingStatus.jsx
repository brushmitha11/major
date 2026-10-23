import React, { useState } from 'react'
import { CheckCircle, Clock, AlertCircle } from 'lucide-react'
import './ProcessingStatus.css'

export default function ProcessingStatus({
  uploadId,
  qualityData,
  processingResults,
  loading,
  config,
  onProcess,
}) {
  const [expanded, setExpanded] = useState(true)

  const qualityPassed = qualityData?.quality_band?.level !== 'POOR'
  const isProcessing = loading

  const handleProcess = () => {
    const options = {
      runOcr: config?.features?.ocr_enabled,
      runVlm: config?.features?.vlm_enabled,
      runVerification: config?.features?.verification_enabled,
    }
    onProcess(options)
  }

  return (
    <div className="processing-status">
      <div
        className="status-header"
        onClick={() => setExpanded(!expanded)}
        role="button"
        tabIndex={0}
      >
        <h3 className="status-title">Processing Pipeline</h3>
        <button
          className={`expand-button ${expanded ? 'expanded' : ''}`}
          aria-label="Toggle details"
        >
          ▼
        </button>
      </div>

      {expanded && (
        <div className="status-content">
          {/* Pipeline steps */}
          <div className="pipeline">
            {/* Step 1: Upload */}
            <div className="pipeline-step completed">
              <div className="step-marker">
                <CheckCircle size={24} />
              </div>
              <div className="step-info">
                <h4 className="step-title">Image Uploaded</h4>
                <p className="step-description">Cheque image received and saved</p>
              </div>
            </div>

            {/* Step 2: Quality Analysis */}
            <div className={`pipeline-step ${qualityPassed ? 'completed' : 'failed'}`}>
              <div className="step-marker">
                {qualityPassed ? <CheckCircle size={24} /> : <AlertCircle size={24} />}
              </div>
              <div className="step-info">
                <h4 className="step-title">Quality Analysis</h4>
                <p className="step-description">
                  {qualityPassed
                    ? `Quality score: ${qualityData?.overall_score}/100`
                    : 'Quality check failed'}
                </p>
              </div>
            </div>

            {/* Step 3: Text Extraction (conditional) */}
            {config?.features?.ocr_enabled || config?.features?.vlm_enabled ? (
              <div
                className={`pipeline-step ${
                  processingResults
                    ? 'completed'
                    : isProcessing
                      ? 'pending'
                      : 'idle'
                }`}
              >
                <div className="step-marker">
                  {processingResults ? (
                    <CheckCircle size={24} />
                  ) : isProcessing ? (
                    <div className="spinner-small"></div>
                  ) : (
                    <Clock size={24} />
                  )}
                </div>
                <div className="step-info">
                  <h4 className="step-title">Text Extraction</h4>
                  <p className="step-description">
                    {processingResults
                      ? 'Printed and handwritten text extracted'
                      : 'Ready to extract text from cheque'}
                  </p>
                </div>
              </div>
            ) : null}

            {/* Step 4: Verification (conditional) */}
            {config?.features?.verification_enabled ? (
              <div className="pipeline-step idle">
                <div className="step-marker">
                  <Clock size={24} />
                </div>
                <div className="step-info">
                  <h4 className="step-title">Cheque Verification</h4>
                  <p className="step-description">Verify authenticity and signature</p>
                </div>
              </div>
            ) : null}
          </div>

          {/* Action buttons */}
          <div className="status-actions">
            {!processingResults && qualityPassed && (
              <button
                className="btn btn-primary"
                onClick={handleProcess}
                disabled={isProcessing}
              >
                {isProcessing ? (
                  <>
                    <div className="btn-spinner"></div>
                    Processing...
                  </>
                ) : (
                  'Extract Text & Verify'
                )}
              </button>
            )}

            {processingResults && (
              <div className="status-message success-message">
                <CheckCircle size={20} />
                <span>Processing complete!</span>
              </div>
            )}

            {!qualityPassed && (
              <div className="status-message warning-message">
                <AlertCircle size={20} />
                <span>
                  Image quality is poor. Please upload a better image for accurate results.
                </span>
              </div>
            )}
          </div>

          {/* Status info */}
          <div className="status-info">
            <p className="info-text">
              <strong>Upload ID:</strong> {uploadId}
            </p>
            {qualityData && (
              <p className="info-text">
                <strong>Quality Band:</strong> {qualityData.quality_band.label}
              </p>
            )}
            {processingResults && (
              <p className="info-text">
                <strong>Status:</strong> All tests passed. Results displayed above.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
