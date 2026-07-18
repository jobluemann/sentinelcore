import React, { useState } from 'react'
import {
  signInWithPopup,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
} from 'firebase/auth'
import { auth, googleProvider, facebookProvider } from '../firebase.js'

// Same environment-aware logic as api/client.js — relative path works via Vite's
// dev proxy locally, but production builds need the full Render URL (see .env.production).
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

async function establishSession(firebaseUser) {
  const idToken = await firebaseUser.getIdToken()
  const res = await fetch(`${API_BASE}/auth/session`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${idToken}`,
    },
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`Backend session call failed (${res.status}): ${text}`)
  }
  return res.json()
}

export default function Login({ onLoggedIn }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [mode, setMode] = useState('signin') // 'signin' | 'signup'
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleProviderLogin(provider) {
    setError(null)
    setLoading(true)
    try {
      const result = await signInWithPopup(auth, provider)
      const sessionData = await establishSession(result.user)
      onLoggedIn(sessionData)
    } catch (err) {
      console.error(err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleEmailSubmit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const credential =
        mode === 'signup'
          ? await createUserWithEmailAndPassword(auth, email, password)
          : await signInWithEmailAndPassword(auth, email, password)
      const sessionData = await establishSession(credential.user)
      onLoggedIn(sessionData)
    } catch (err) {
      console.error(err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <h1>Sentinel Core</h1>
        <p className="muted">Sign in to start your $10,000 demo account</p>

        <button className="provider-btn google" onClick={() => handleProviderLogin(googleProvider)} disabled={loading}>
          Continue with Google
        </button>
        <button className="provider-btn facebook" onClick={() => handleProviderLogin(facebookProvider)} disabled={loading}>
          Continue with Facebook
        </button>

        <div className="divider"><span>or</span></div>

        <form onSubmit={handleEmailSubmit}>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
          />
          <button type="submit" className="provider-btn email" disabled={loading}>
            {mode === 'signup' ? 'Create account' : 'Sign in'}
          </button>
        </form>

        <button className="link-btn" onClick={() => setMode(mode === 'signup' ? 'signin' : 'signup')}>
          {mode === 'signup' ? 'Already have an account? Sign in' : "Don't have an account? Sign up"}
        </button>

        {error && <p className="error-text">{error}</p>}
        {loading && <p className="muted">Working...</p>}
      </div>
    </div>
  )
}
