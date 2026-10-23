import React from 'react'
import { CheckCircle } from 'lucide-react'
import './Header.css'

export default function Header() {
  return (
    <header className="header">
      <div className="header-content">
        <div className="header-branding">
          <CheckCircle className="header-icon" />
          <div className="header-text">
            <h1 className="header-title">Cheque Verification</h1>
            <p className="header-subtitle">AI-Powered Image Quality Assessment & Verification</p>
          </div>
        </div>
      </div>
    </header>
  )
}
