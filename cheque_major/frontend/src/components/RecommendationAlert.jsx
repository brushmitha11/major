import React from 'react'
import { AlertCircle, AlertTriangle, CheckCircle, Info } from 'lucide-react'
import './RecommendationAlert.css'

export default function RecommendationAlert({ type, severity, message }) {
  const getIcon = () => {
    switch (type) {
      case 'OK':
        return <CheckCircle size={20} />
      case 'RESOLUTION':
      case 'SHARPNESS':
      case 'BRIGHTNESS':
        return <AlertCircle size={20} />
      case 'CONTRAST':
      case 'SKEW':
        return <AlertTriangle size={20} />
      default:
        return <Info size={20} />
    }
  }

  const getSeverityClass = () => {
    switch (severity?.toUpperCase()) {
      case 'HIGH':
        return 'severity-high'
      case 'MEDIUM':
        return 'severity-medium'
      case 'LOW':
        return 'severity-low'
      case 'INFO':
        return 'severity-info'
      default:
        return 'severity-info'
    }
  }

  return (
    <div className={`recommendation-alert ${getSeverityClass()}`}>
      <div className="alert-icon">
        {getIcon()}
      </div>
      <div className="alert-content">
        <p className="alert-message">{message}</p>
      </div>
    </div>
  )
}
