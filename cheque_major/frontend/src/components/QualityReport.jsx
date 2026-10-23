import React from 'react'
import { AlertCircle, CheckCircle, AlertTriangle } from 'lucide-react'
import MetricBar from './MetricBar'
import RecommendationAlert from './RecommendationAlert'
import './QualityReport.css'

export default function QualityReport({ quality, loading }) {
  if (!quality) return null

  const { overall_score, quality_band, metrics, recommendations } = quality

  const getScoreColor = (score) => {
    if (score >= 80) return 'green'
    if (score >= 60) return 'yellow'
    return 'red'
  }

  return (
    <div className="quality-report">
      <h2 className="report-title">Image Quality Analysis</h2>

      {/* Overall score gauge */}
      <div className="score-gauge-container">
        <div className={`score-gauge gauge-${getScoreColor(overall_score)}`}>
          <div className="gauge-circle">
            <div className="gauge-value">{overall_score}</div>
            <div className="gauge-label">Score</div>
          </div>
        </div>
        <div className="score-info">
          <div className={`quality-band band-${quality_band.level}`}>
            {quality_band.label}
          </div>
          <div className="band-description">
            {quality_band.level === 'GOOD' && 'Image quality is excellent. Ready for processing.'}
            {quality_band.level === 'ACCEPTABLE' && 'Image quality is acceptable but may require manual review.'}
            {quality_band.level === 'POOR' && 'Image quality is poor. Consider recapturing with better conditions.'}
          </div>
        </div>
      </div>

      {/* Metrics breakdown */}
      <div className="metrics-section">
        <h3 className="metrics-title">Quality Metrics</h3>
        <div className="metrics-grid">
          {metrics && Object.entries(metrics).map(([name, metric]) => (
            <div key={name} className="metric-card">
              <div className="metric-header">
                <span className="metric-name">{formatMetricName(name)}</span>
                <span className={`metric-status status-${metric.status.toLowerCase()}`}>
                  {metric.status}
                </span>
              </div>
              <MetricBar
                score={metric.score}
                label={metric.message}
              />
              {metric.details && (
                <div className="metric-details">
                  {Object.entries(metric.details).map(([key, value]) => (
                    <div key={key} className="detail-row">
                      <span className="detail-key">{key}:</span>
                      <span className="detail-value">{formatValue(value)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Recommendations */}
      {recommendations && recommendations.length > 0 && (
        <div className="recommendations-section">
          <h3 className="recommendations-title">Recommendations</h3>
          <div className="recommendations-list">
            {recommendations.map((rec, idx) => (
              <RecommendationAlert
                key={idx}
                type={rec.type}
                severity={rec.severity}
                message={rec.message}
              />
            ))}
          </div>
        </div>
      )}

      {loading && (
        <div className="loading-overlay">
          <div className="spinner-small"></div>
        </div>
      )}
    </div>
  )
}

function formatMetricName(name) {
  return name
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

function formatValue(value) {
  if (typeof value === 'number') {
    return value.toFixed(2)
  }
  return String(value)
}
