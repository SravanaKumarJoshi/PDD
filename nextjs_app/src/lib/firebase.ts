/**
 * Firebase Authentication REST client module for BioPolymer Web App.
 * Uses exact Firebase credentials matching the Android app (apppp-auth project).
 */

export const FIREBASE_CONFIG = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || 'AIzaSyDTBL6quWZuxDVj2k4QPBCKYvRSWN9GNIs',
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || 'apppp-auth.firebaseapp.com',
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || 'apppp-auth',
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || 'apppp-auth.firebasestorage.app',
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || '768172843468',
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || '1:768172843468:web:apppp-auth-web',
};

const REST_BASE = 'https://identitytoolkit.googleapis.com/v1/accounts';

export interface FirebaseAuthResult {
  idToken: string;
  email: string;
  localId: string;
  displayName?: string;
  refreshToken?: string;
  expiresIn?: string;
}

/** Map raw Firebase REST errors to user-friendly messages matching Android app */
function mapFirebaseError(message: string): string {
  const code = message || '';
  if (code.includes('INVALID_LOGIN_CREDENTIALS') || code.includes('INVALID_PASSWORD') || code.includes('wrong-password')) {
    return 'Incorrect email or password. Please check your credentials.';
  }
  if (code.includes('EMAIL_NOT_FOUND') || code.includes('USER_NOT_FOUND') || code.includes('user-not-found')) {
    return 'No account found with this email address.';
  }
  if (code.includes('EMAIL_EXISTS') || code.includes('email-already-in-use')) {
    return 'An account with this email address already exists. Try signing in instead.';
  }
  if (code.includes('TOO_MANY_ATTEMPTS') || code.includes('too-many-requests')) {
    return 'Too many failed login attempts. Account temporarily locked. Please try again later.';
  }
  if (code.includes('INVALID_EMAIL')) {
    return 'The email address is badly formatted.';
  }
  if (code.includes('WEAK_PASSWORD')) {
    return 'Password must be at least 6 characters long.';
  }
  return message || 'Firebase authentication failed. Please try again.';
}

export async function firebaseSignIn(email: string, pass: string): Promise<FirebaseAuthResult> {
  const response = await fetch(`${REST_BASE}:signInWithPassword?key=${FIREBASE_CONFIG.apiKey}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      password: pass,
      returnSecureToken: true,
    }),
  });

  const data = await response.json();
  if (!response.ok || data.error) {
    const rawMsg = data.error?.message || 'Sign in failed';
    throw new Error(mapFirebaseError(rawMsg));
  }

  return {
    idToken: data.idToken,
    email: data.email,
    localId: data.localId,
    displayName: data.displayName,
    refreshToken: data.refreshToken,
    expiresIn: data.expiresIn,
  };
}

export async function firebaseSignUp(
  email: string,
  pass: string,
  displayName?: string
): Promise<FirebaseAuthResult> {
  const response = await fetch(`${REST_BASE}:signUp?key=${FIREBASE_CONFIG.apiKey}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      password: pass,
      returnSecureToken: true,
    }),
  });

  const data = await response.json();
  if (!response.ok || data.error) {
    const rawMsg = data.error?.message || 'Registration failed';
    throw new Error(mapFirebaseError(rawMsg));
  }

  const result: FirebaseAuthResult = {
    idToken: data.idToken,
    email: data.email,
    localId: data.localId,
    displayName: displayName || data.displayName,
    refreshToken: data.refreshToken,
    expiresIn: data.expiresIn,
  };

  if (displayName) {
    try {
      await firebaseUpdateProfile(result.idToken, displayName);
      result.displayName = displayName;
    } catch (e) {
      console.warn('Failed to update display name on signup:', e);
    }
  }

  return result;
}

export async function firebaseUpdateProfile(
  idToken: string,
  displayName: string
): Promise<void> {
  const response = await fetch(`${REST_BASE}:update?key=${FIREBASE_CONFIG.apiKey}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      idToken,
      displayName,
      returnSecureToken: true,
    }),
  });

  const data = await response.json();
  if (!response.ok || data.error) {
    throw new Error(data.error?.message || 'Failed to update profile');
  }
}

export async function firebaseLookupToken(idToken: string): Promise<any> {
  const response = await fetch(`${REST_BASE}:lookup?key=${FIREBASE_CONFIG.apiKey}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      idToken,
    }),
  });

  const data = await response.json();
  if (!response.ok || data.error) {
    throw new Error(data.error?.message || 'Invalid Firebase session');
  }
  return data.users && data.users[0] ? data.users[0] : null;
}
