import React from 'react'
import './ConfidenceCard.css'

export default function ConfidenceCard({
  title,
  subtitle,
  status,
  confidence,
  message,
  details = [],
  icon,
}) {
  const getStatusColor = (s) => {
    switch (s) {
      case 'HIGH':
        return 'status-high'
      case 'MEDIUM':
        return 'status-medium'
      case 'LOW':
        return 'status-low'
      case 'PENDING':
        return 'status-pending'
      case 'ERROR':
        return 'status-error'
      case 'UNAVAILABLE':
      case 'DISABLED':
        return 'status-unavailable'
      default:
        return 'status-unknown'
    }
  }

  const getStatusLabel = (s) => {
    switch (s) {
      case 'HIGH':
        return 'High Confidence'
      case 'MEDIUM':
        return 'Medium Confidence'
      case 'LOW':
        return 'Low Confidence'
      case 'PENDING':
        return 'Processing'
      case 'ERROR':
        return 'Error'
      case 'UNAVAILABLE':
        return 'Unavailable'
      case 'DISABLED':
        return 'Disabled'
      default:
        return 'Unknown'
    }
  }

  return (
    <div className="confidence-card">
      <div className="card-header">
        <div className="card-icon">
          {icon}
        </div>
        <div className="card-titles">
          <h3 className="card-title">{title}</h3>
          <p className="card-subtitle">{subtitle}</p>
        </div>
      </div>

      <div className={`card-status ${getStatusColor(status)}`}>
        {getStatusLabel(status)}
      </div>

      {confidence !== null && (
        <div className="card-confidence">
          <div className="confidence-value">{confidence}%</div>
          <div className="confidence-bar">
            <div
              className={`confidence-fill ${getStatusColor(status)}`}
              style={{ width: `${confidence}%` }}
            />
          </div>
        </div>
      )}

      <p className="card-message">{message}</p>

      {details.length > 0 && (
        <div className="card-details">
          {details.map((detail, idx) => (
            <div key={idx} className="detail-item">
              <span className="detail-label">{detail.label}:</span>
              <span className="detail-value">{detail.value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
