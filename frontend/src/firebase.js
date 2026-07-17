import { initializeApp } from 'firebase/app'
import { getAuth, GoogleAuthProvider, FacebookAuthProvider } from 'firebase/auth'

const firebaseConfig = {
  apiKey: "AIzaSyApDFWNXqK35nPS3BYn7xC4I9lPQJ28Xu4",
  authDomain: "sentinel-603fc.firebaseapp.com",
  projectId: "sentinel-603fc",
  storageBucket: "sentinel-603fc.firebasestorage.app",
  messagingSenderId: "158581394120",
  appId: "1:158581394120:web:c8c635d104bc50169cf3fd",
  measurementId: "G-W58QTKXCX7"
}

const app = initializeApp(firebaseConfig)
export const auth = getAuth(app)
export const googleProvider = new GoogleAuthProvider()
export const facebookProvider = new FacebookAuthProvider()
