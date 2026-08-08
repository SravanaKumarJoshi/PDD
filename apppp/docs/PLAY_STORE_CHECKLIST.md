# Google Play Store Readiness Checklist

## App Content
- [x] App disclaimer visible on onboarding (not medical advice)
- [x] Material 3 design with dark mode support
- [x] Accessibility labels on interactive elements
- [x] Loading, empty, and error states handled
- [x] Minimum touch target 48dp

## Permissions
- [x] `INTERNET` — for backend sync and auth
- [x] `ACCESS_NETWORK_STATE` — for offline/online detection
- [ ] No sensitive permissions required

## Privacy & Data
- [x] Privacy Policy URL (to be hosted)
- [x] Data export available in Settings
- [x] Data deletion available in Settings
- [x] Analytics toggle (opt-in)
- [x] No personal health data collected
- [x] Firebase Auth data disclosed

## App Signing
- [ ] Generate upload keystore
- [ ] Enroll in Google Play App Signing
- [ ] Build signed `.aab` bundle

## Store Listing
- [ ] App icon (512x512 high-res)
- [ ] Feature graphic (1024x500)
- [ ] Screenshots (phone + tablet)
- [ ] Short description (80 chars max)
- [ ] Full description (4000 chars max)
- [ ] Category: Education or Productivity
- [ ] Content rating questionnaire completed

## Technical
- [x] Target SDK = API 35
- [x] Min SDK = API 26
- [x] ProGuard/R8 enabled for release
- [x] No hardcoded secrets in client code
- [x] Version code auto-incrementable

## Testing
- [ ] Unit tests passing
- [ ] UI tests for key flows
- [ ] Tested on phone + tablet form factors
- [ ] Tested on API 26, 31, 35

## Release Track
1. Internal Testing → validate core flows
2. Closed Testing → limited beta testers
3. Open Testing → broader feedback
4. Production → public release
