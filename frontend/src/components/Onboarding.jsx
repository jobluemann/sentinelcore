import { useState } from 'react'
import { auth } from '../firebase.js'
import { saveOnboarding } from '../api/client.js'

const GENDER_OPTIONS = [
  { value: 'male', label: 'Male', icon: '♂️' },
  { value: 'female', label: 'Female', icon: '♀️' },
]

const AGE_OPTIONS = [
  { value: '18-24', label: '18–24', icon: '🎓' },
  { value: '25-34', label: '25–34', icon: '💼' },
  { value: '35-44', label: '35–44', icon: '🏠' },
  { value: '45-54', label: '45–54', icon: '📈' },
  { value: '55+', label: '55+', icon: '🌅' },
]

const COLOR_OPTIONS = [
  { value: 'red', label: 'Red', hex: '#ef4444' },
  { value: 'orange', label: 'Orange', hex: '#f5a623' },
  { value: 'green', label: 'Green', hex: '#22c55e' },
  { value: 'blue', label: 'Blue', hex: '#3b82f6' },
  { value: 'purple', label: 'Purple', hex: '#a855f7' },
  { value: 'black', label: 'Black', hex: '#1f2733' },
]

const PET_OPTIONS = [
  { value: 'cat', label: 'Cat', icon: '🐱' },
  { value: 'dog', label: 'Dog', icon: '🐶' },
  { value: 'horse', label: 'Horse', icon: '🐴' },
  { value: 'bird', label: 'Bird', icon: '🐦' },
]

const INTEREST_OPTIONS = [
  { value: 'books', label: 'Books', icon: '📚' },
  { value: 'food', label: 'Food', icon: '🍔' },
  { value: 'tech', label: 'Tech', icon: '💻' },
  { value: 'news', label: 'News', icon: '📰' },
]

const ASSET_OPTIONS = [
  { value: 'stock', label: 'Stocks', icon: '📈' },
  { value: 'crypto', label: 'Crypto', icon: '🪙' },
  { value: 'commodity', label: 'Commodities', icon: '🛢️' },
  { value: 'forex', label: 'Forex', icon: '💱' },
]

const STEPS = ['gender', 'age_range', 'favorite_color', 'favorite_pet', 'interests', 'asset_preferences']

export default function Onboarding({ onComplete }) {
  const [stepIndex, setStepIndex] = useState(0)
  const [answers, setAnswers] = useState({
    gender: null,
    age_range: null,
    favorite_color: null,
    favorite_pet: null,
    interests: [],
    asset_preferences: [],
  })
  const [saving, setSaving] = useState(false)

  const step = STEPS[stepIndex]

  function selectSingle(field, value) {
    setAnswers({ ...answers, [field]: value })
    // Auto-advance after a short pause so the click feels acknowledged
    setTimeout(() => goNext({ ...answers, [field]: value }), 200)
  }

  function toggleMulti(field, value) {
    const current = answers[field]
    const next = current.includes(value)
      ? current.filter((v) => v !== value)
      : [...current, value]
    setAnswers({ ...answers, [field]: next })
  }

  async function goNext(latestAnswers) {
    if (stepIndex < STEPS.length - 1) {
      setStepIndex(stepIndex + 1)
      return
    }
    // Last step — save and finish
    setSaving(true)
    try {
      const idToken = await auth.currentUser.getIdToken()
      await saveOnboarding(idToken, latestAnswers ?? answers)
    } catch (err) {
      console.warn('[onboarding] save failed, continuing anyway', err)
    } finally {
      setSaving(false)
      onComplete()
    }
  }

  function skip() {
    onComplete()
  }

  return (
    <div className="onboarding-screen">
      <div className="onboarding-card">
        <div className="onboarding-progress">
          {STEPS.map((s, i) => (
            <span key={s} className={`onboarding-dot ${i <= stepIndex ? 'filled' : ''}`} />
          ))}
        </div>

        {step === 'gender' && (
          <QuestionStep title="Are you male or female?">
            <div className="onboarding-options">
              {GENDER_OPTIONS.map((o) => (
                <button
                  key={o.value}
                  className={`onboarding-tile ${answers.gender === o.value ? 'selected' : ''}`}
                  onClick={() => selectSingle('gender', o.value)}
                >
                  <span className="onboarding-icon">{o.icon}</span>
                  <span>{o.label}</span>
                </button>
              ))}
            </div>
          </QuestionStep>
        )}

        {step === 'age_range' && (
          <QuestionStep title="What's your age range?">
            <div className="onboarding-options">
              {AGE_OPTIONS.map((o) => (
                <button
                  key={o.value}
                  className={`onboarding-tile ${answers.age_range === o.value ? 'selected' : ''}`}
                  onClick={() => selectSingle('age_range', o.value)}
                >
                  <span className="onboarding-icon">{o.icon}</span>
                  <span>{o.label}</span>
                </button>
              ))}
            </div>
          </QuestionStep>
        )}

        {step === 'favorite_color' && (
          <QuestionStep title="What's your favorite color?">
            <div className="onboarding-options">
              {COLOR_OPTIONS.map((o) => (
                <button
                  key={o.value}
                  className={`onboarding-tile ${answers.favorite_color === o.value ? 'selected' : ''}`}
                  onClick={() => selectSingle('favorite_color', o.value)}
                >
                  <span className="onboarding-swatch" style={{ background: o.hex }} />
                  <span>{o.label}</span>
                </button>
              ))}
            </div>
          </QuestionStep>
        )}

        {step === 'favorite_pet' && (
          <QuestionStep title="Which pet do you like?">
            <div className="onboarding-options">
              {PET_OPTIONS.map((o) => (
                <button
                  key={o.value}
                  className={`onboarding-tile ${answers.favorite_pet === o.value ? 'selected' : ''}`}
                  onClick={() => selectSingle('favorite_pet', o.value)}
                >
                  <span className="onboarding-icon">{o.icon}</span>
                  <span>{o.label}</span>
                </button>
              ))}
            </div>
          </QuestionStep>
        )}

        {step === 'interests' && (
          <QuestionStep title="What are you interested in?" subtitle="Pick as many as you like">
            <div className="onboarding-options">
              {INTEREST_OPTIONS.map((o) => (
                <button
                  key={o.value}
                  className={`onboarding-tile ${answers.interests.includes(o.value) ? 'selected' : ''}`}
                  onClick={() => toggleMulti('interests', o.value)}
                >
                  <span className="onboarding-icon">{o.icon}</span>
                  <span>{o.label}</span>
                </button>
              ))}
            </div>
            <button
              className="onboarding-continue"
              disabled={answers.interests.length === 0}
              onClick={() => goNext()}
            >
              Continue
            </button>
          </QuestionStep>
        )}

        {step === 'asset_preferences' && (
          <QuestionStep title="What do you like to play with?" subtitle="Pick as many as you like">
            <div className="onboarding-options">
              {ASSET_OPTIONS.map((o) => (
                <button
                  key={o.value}
                  className={`onboarding-tile ${answers.asset_preferences.includes(o.value) ? 'selected' : ''}`}
                  onClick={() => toggleMulti('asset_preferences', o.value)}
                >
                  <span className="onboarding-icon">{o.icon}</span>
                  <span>{o.label}</span>
                </button>
              ))}
            </div>
            <button
              className="onboarding-continue"
              disabled={answers.asset_preferences.length === 0 || saving}
              onClick={() => goNext()}
            >
              {saving ? 'Saving...' : 'Finish'}
            </button>
          </QuestionStep>
        )}

        <button className="onboarding-skip" onClick={skip}>Skip for now</button>
      </div>
    </div>
  )
}

function QuestionStep({ title, subtitle, children }) {
  return (
    <div className="onboarding-step">
      <h2>{title}</h2>
      {subtitle && <p className="muted">{subtitle}</p>}
      {children}
    </div>
  )
}
