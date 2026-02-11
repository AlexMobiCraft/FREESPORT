# Walkthrough: Fix Auth Redirection Spec

Resolved the incorrect post-authentication redirection issue where users were sent to `/home` or dummy pages. Implemented consistent redirection to the root path `/` (which handles Active Theme redirection).

## Changes

### 1. `RegisterForm`
- **Updated**: Redirect logic modified to use `redirectUrl` prop or fallback to `/`.
- **Added**: `redirectUrl` prop to `RegisterFormProps`.
- **Link**: [RegisterForm.tsx](file:///c:/Users/tkachenko/DEV/FREESPORT/frontend/src/components/auth/RegisterForm.tsx)

### 2. `B2BRegisterForm`
- **Updated**: Changed hardcoded `/home` redirects to `/`.
- **Fixed**: Added `authService.refreshToken()` call after B2B registration to force session update for immediate verification check.
- **Link**: [B2BRegisterForm.tsx](file:///c:/Users/tkachenko/DEV/FREESPORT/frontend/src/components/auth/B2BRegisterForm.tsx)

### 3. Documentation
- **Updated**: `docs/stories/epic-28/28.1.core-auth.md` to reflect new redirect logic.

### 4. Tests
- **Updated**: `RegisterForm.test.tsx` to verify redirect to `/` and test `redirectUrl` support.
- **Updated**: `B2BRegisterForm.test.tsx` to verify redirect to `/` and cover `legal_address` validation.
- **Verified**: `LoginForm.test.tsx` passed existing checks.

## Verification Results

### Automated Tests
Ran unit tests for all auth forms:
```bash
npm test src/components/auth/__tests__/RegisterForm.test.tsx src/__tests__/components/B2BRegisterForm.test.tsx src/components/auth/__tests__/LoginForm.test.tsx
```

**Result**: All 44 tests PASSED.

### Manual Verification
1. **Login**: Redirects to `/` (Active Theme Home) or `redirectUrl` if provided.
2. **Register (B2C)**: Redirects to `/` after successful registration.
3. **Register (B2B)**: Redirects to `/` after successful registration (if auto-verified) or displays "Pending" status with a "To Main" button pointing to `/`.
