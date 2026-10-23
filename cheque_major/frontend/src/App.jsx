import React, { useState, useEffect } from 'react'
import Header from './components/Header'
import ImageUpload from './components/ImageUpload'
import QualityReport from './components/QualityReport'
import ExtractedText from './components/ExtractedText'
import ProcessingStatus from './components/ProcessingStatus'
import { apiRequest } from './api'
import './App.css'

export default function App() {
  const [uploadId, setUploadId] = useState(null)
  const [uploadedImage, setUploadedImage] = useState(null)
  const [qualityData, setQualityData] = useState(null)
  const [processingResults, setProcessingResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [config, setConfig] = useState(null)

  // Load configuration on mount
  useEffect(() => {
    const loadConfig = async () => {
      try {
        setConfig(await apiRequest('/api/config'))
      } catch (err) {
        setError(err.message)
      }
    }
    loadConfig()
  }, [])

  const handleImageSelect = async (imageFile) => {
    setError(null)
    setLoading(true)

    try {
      const formData = new FormData()
      formData.append('image', imageFile)

      const data = await apiRequest('/api/upload', {
        method: 'POST',
        body: formData,
      })

      setUploadId(data.upload_id)
      setUploadedImage({
        name: imageFile.name,
        size: data.file_size_mb,
        url: /\.tiff?$/i.test(imageFile.name)
          ? `/api/preview/${data.upload_id}`
          : URL.createObjectURL(imageFile),
      })
      setQualityData(data.quality)
      setProcessingResults(null)
      setLoading(false)
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  const handleProcessImage = async (options = {}) => {
    if (!uploadId) return

    setLoading(true)
    setError(null)

    try {
      const data = await apiRequest('/api/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          upload_id: uploadId,
          run_ocr: options.runOcr !== false,
          run_vlm: options.runVlm !== false,
          run_verification: options.runVerification || false,
        }),
      })
      setProcessingResults(data)
      setLoading(false)
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  const handleReset = () => {
    setUploadId(null)
    setUploadedImage(null)
    setQualityData(null)
    setProcessingResults(null)
    setError(null)
  }

  return (
    <div className="app">
      <Header />

      <main className="app-main">
        <div className="app-container">
          {/* Error banner */}
          {error && (
            <div className="error-banner">
              <div className="error-message">
                <strong>Error:</strong> {error}
              </div>
              <button
                className="error-close"
                onClick={() => setError(null)}
                aria-label="Close error"
              >
                ×
              </button>
            </div>
          )}

          {/* Main layout */}
          {!uploadedImage ? (
            // Upload section
            <div className="section">
              <ImageUpload
                onImageSelect={handleImageSelect}
                loading={loading}
                config={config}
              />
            </div>
          ) : (
            // Analysis section
            <div className="analysis-layout">
              {/* Preview section */}
              <aside className="preview-panel">
                <div className="preview-card">
                  <h3 className="preview-title">Image Preview</h3>
                  <div className="preview-image">
                    <img src={uploadedImage.url} alt="Uploaded cheque" />
                  </div>
                  <div className="preview-info">
                    <div className="info-row">
                      <span className="label">File:</span>
                      <span className="value">{uploadedImage.name}</span>
                    </div>
                    <div className="info-row">
                      <span className="label">Size:</span>
                      <span className="value">{uploadedImage.size} MB</span>
                    </div>
                  </div>
                  <div className="preview-actions">
                    <button
                      className="btn btn-secondary btn-full"
                      onClick={handleReset}
                    >
                      Upload New Image
                    </button>
                  </div>
                </div>
              </aside>

              {/* Results section */}
              <section className="results-panel">
                {/* Quality Report */}
                {qualityData && (
                  <div className="section">
                    <QualityReport
                      quality={qualityData}
                      loading={loading}
                    />
                  </div>
                )}

                {/* Processing Status */}
                <ProcessingStatus
                  uploadId={uploadId}
                  qualityData={qualityData}
                  processingResults={processingResults}
                  loading={loading}
                  config={config}
                  onProcess={handleProcessImage}
                />

                {/* Extracted text */}
                {processingResults && (
                  <div className="section">
                    <ExtractedText results={processingResults} />
                  </div>
                )}
              </section>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
