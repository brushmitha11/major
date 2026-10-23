import React, { useRef, useState } from 'react'
import { Upload, AlertCircle } from 'lucide-react'
import './ImageUpload.css'

export default function ImageUpload({ onImageSelect, loading, config }) {
  const fileInputRef = useRef(null)
  const [dragActive, setDragActive] = useState(false)
  const [validationError, setValidationError] = useState(null)

  const maxSizeMb = config?.constraints?.max_file_size_mb || 20
  const allowedFormats = config?.constraints?.allowed_formats || ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tif', 'tiff']

  const validateFile = (file) => {
    setValidationError(null)

    // Check file size
    const sizeMb = file.size / (1024 * 1024)
    if (sizeMb > maxSizeMb) {
      setValidationError(`File too large (${sizeMb.toFixed(1)}MB). Maximum: ${maxSizeMb}MB`)
      return false
    }

    // Check file type
    const ext = file.name.split('.').pop().toLowerCase()
    if (!allowedFormats.includes(ext)) {
      setValidationError(`Unsupported format. Allowed: ${allowedFormats.join(', ')}`)
      return false
    }

    // Some browsers report an empty MIME type for .tif files, so the extension is the fallback check
    if (file.type && !file.type.startsWith('image/')) {
      setValidationError('File must be an image')
      return false
    }

    return true
  }

  const handleFileSelect = (file) => {
    if (validateFile(file)) {
      onImageSelect(file)
    }
  }

  const handleClick = () => {
    fileInputRef.current?.click()
  }

  const handleInputChange = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      handleFileSelect(file)
    }
  }

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    const file = e.dataTransfer.files?.[0]
    if (file) {
      handleFileSelect(file)
    }
  }

  return (
    <div className="image-upload">
      <div className="upload-card">
        <div
          className={`upload-area ${dragActive ? 'active' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={handleClick}
        >
          <div className="upload-content">
            <div className="upload-icon">
              <Upload size={48} />
            </div>
            <h2 className="upload-title">Upload Cheque Image</h2>
            <p className="upload-description">
              Drag and drop your cheque image here or click to browse
            </p>
            <p className="upload-hint">
              Supported formats: {allowedFormats.join(', ')} • Max size: {maxSizeMb}MB
            </p>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleInputChange}
            className="upload-input"
            disabled={loading}
          />
        </div>

        {/* Validation error */}
        {validationError && (
          <div className="validation-error">
            <AlertCircle size={20} />
            <span>{validationError}</span>
          </div>
        )}

        {/* Loading state */}
        {loading && (
          <div className="upload-loading">
            <div className="spinner"></div>
            <p>Processing image...</p>
          </div>
        )}

        {/* Help text */}
        <div className="upload-help">
          <h3 className="help-title">Tips for Best Results</h3>
          <ul className="help-list">
            <li>Ensure the cheque is fully visible in the frame</li>
            <li>Use good lighting to avoid shadows and glare</li>
            <li>Keep the camera steady for sharp focus</li>
            <li>Align the cheque horizontally (not rotated)</li>
            <li>Avoid blur, overexposure, or underexposure</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
