import React from 'react'
import './MetricBar.css'

export default function MetricBar({ score, label, min = 0, max = 100 }) {
  const percentage = ((score - min) / (max - min)) * 100
  const clampedPercentage = Math.max(0, Math.min(100, percentage))

  const getColor = (value) => {
    if (value >= 80) return 'green'
    if (value >= 60) return 'yellow'
    return 'red'
  }

  const color = getColor(score)

  return (
    <div className="metric-bar-container">
      <div className="metric-bar-track">
        <div
          className={`metric-bar-fill color-${color}`}
          style={{ width: `${clampedPercentage}%` }}
        />
      </div>
      {label && <p className="metric-bar-label">{label}</p>}
    </div>
  )
}
