import { initializeApp, getApps, getApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: "AIzaSyAhKEHnEQ6G_k681Mb3d10iH9fV7TzIEJY",
  authDomain: "ai-policy-assistant-659f1.firebaseapp.com",
  projectId: "ai-policy-assistant-659f1",
  storageBucket: "ai-policy-assistant-659f1.firebasestorage.app",
  messagingSenderId: "721723592938",
  appId: "1:721723592938:web:4441ab1e29cc387ce1c793",
  measurementId: "G-Z2B4W80N8W"
};

// Initialize Firebase
const app = !getApps().length ? initializeApp(firebaseConfig) : getApp();
const auth = getAuth(app);
const db = getFirestore(app);
const googleProvider = new GoogleAuthProvider();

export { app, auth, db, googleProvider };
