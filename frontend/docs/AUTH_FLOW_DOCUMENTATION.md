# Auth Flow — Complete Documentation

> This document covers the entire authentication flow: login, signup, password reset,
> email verification, route protection, token management, and state management. It is
> designed so that Claude Code can debug issues and implement new features by reading
> this doc instead of source files — only read the specific file being edited.

---

## Table of Contents

1. [Navigation & Routing](#1-navigation--routing)
2. [Middleware — Route Protection](#2-middleware--route-protection)
3. [Login Page](#3-login-page)
4. [Signup Page](#4-signup-page)
5. [Forgot Password Page](#5-forgot-password-page)
6. [Reset Password Page](#6-reset-password-page)
7. [Check Email Page](#7-check-email-page)
8. [Email Verification Page](#8-email-verification-page)
9. [Shared Container Component](#9-shared-container-component)
10. [Auth Service Layer](#10-auth-service-layer)
11. [Validation Schemas (Zod)](#11-validation-schemas-zod)
12. [Atoms (Global State)](#12-atoms-global-state)
13. [Shared UI Components Used in Auth](#13-shared-ui-components-used-in-auth)
14. [Utilities](#14-utilities)
15. [Constants](#15-constants)
16. [Cookies & Token Management](#16-cookies--token-management)
17. [Key Concepts & Patterns](#17-key-concepts--patterns)
18. [Debugging Guide](#18-debugging-guide)
19. [How to Extend (Common Scenarios)](#19-how-to-extend-common-scenarios)
20. [File Index](#20-file-index)

---

## 1. Navigation & Routing

### Route Map

| Route | Page File | Component | Auth Required | Suspense Wrapper |
|-------|-----------|-----------|---------------|------------------|
| `/auth/login` | `src/app/auth/login/page.tsx` | `LoginPage.tsx` | No | Yes (separate file) |
| `/auth/signup` | `src/app/auth/signup/page.tsx` | `SignupClient.tsx` | No | Yes (separate file) |
| `/auth/forgotpassword` | `src/app/auth/forgotpassword/page.tsx` | Inline (`'use client'`) | No | No |
| `/auth/reset-password` | `src/app/auth/reset-password/page.tsx` | Inline with inner component | No | Yes (inline `Suspense`) |
| `/auth/check-email` | `src/app/auth/check-email/page.tsx` | Inline with inner component | No | Yes (inline `Suspense`) |
| `/auth/verify_signup` | `src/app/auth/verify_signup/page.tsx` | Inline with inner component | No | Yes (inline `Suspense`) |

### Navigation Flow Diagram

```
                                  ┌─────────────────┐
                                  │   /auth/login    │
                                  └─────┬───────┬────┘
                         success ───────┘       │
                         (res truthy)      links │
                              ▼                 │
                         /home             ┌────┴──────────────┐
                                           │                   │
                                   /auth/signup      /auth/forgotpassword
                                       │                    │
                             ┌─────────┴──────┐       email sent (res truthy)
                    standard │      firebase  │             ▼
                    (no uid) │   (uid in URL) │   showToast.success
                             ▼                ▼   ('Email Sent', 'Password reset
              /auth/check-email          /home     instructions sent to your email')
              ?email={email}                │
                             │              │
                    email link clicked      │
                             ▼              │
              /auth/verify_signup           │
              ?email=&code=&user_id=        │
                             │              │
                    ┌────────┤              │
                    │        │              │
           invite_redirect   │   /auth/reset-password
           in localStorage?  │   ?email={email}&token={token}
                    │        │              │
               Yes  │  No   │    success + 2s delay
                    ▼        ▼              │
              redirect   /auth/login  ◄─────┘
              URL
```

### Page Wrapper Patterns

**Two-file pattern** (login, signup):
- `page.tsx` — Default export, renders `<Suspense fallback={null}>` wrapping the client component
- `LoginPage.tsx` / `SignupClient.tsx` — `'use client'` with all form logic

**Single-file with inline Suspense** (reset-password, check-email, verify_signup):
- `page.tsx` — Has both the inner `'use client'` component AND a wrapper default export with `<Suspense fallback={null}>`
- Inner components use `useSearchParams()` which requires Suspense boundary

**Single-file, no Suspense** (forgotpassword):
- `page.tsx` — Direct `'use client'`, no `useSearchParams`, no Suspense needed

---

## 2. Middleware — Route Protection

**File:** `src/middleware.ts` (~1.2KB)

### Public Paths Array

```typescript
const PUBLIC_PATHS = [
  '/auth/login',
  '/auth/signup',
  '/auth/forgotpassword',
  '/auth/check-email',
  '/auth/emailverification',
  '/auth/verify_signup',
  '/auth/reset-password',
  '/auth/onboard',
  '/verify/user_to_workspace',
  '/auth/forgotpasswordverification',
];
```

### Logic (step by step)

1. Extract `pathname` from `request.nextUrl`
2. Skip if path starts with `/_next`, `/favicon`, or contains `.` (static assets)
3. Call `isPublicPath(pathname)`:
   - Checks exact match OR `pathname.startsWith(path + '/')`
   - Returns `NextResponse.next()` if match found
4. Read cookie: `request.cookies.get('tone_access_token')?.value`
5. If **no token**:
   - Build redirect URL: `/auth/login`
   - Set query param: `loginUrl.searchParams.set('redirect', pathname)`
   - Return `NextResponse.redirect(loginUrl)`
6. If **token exists**: Return `NextResponse.next()`

### Matcher Config

```typescript
export const config = {
  matcher: ['/((?!_next/static|_next/image|_next/webpack-hmr).*)'],
};
```

**Gotcha:** The matcher excludes `_next/webpack-hmr` — if adding new static asset paths, add them here too.

---

## 3. Login Page

**File:** `src/app/auth/login/LoginPage.tsx` (~3.3KB)

### Imports

| Import | Source | Purpose |
|--------|--------|---------|
| `useRouter` | `next/navigation` | Navigate on success |
| `useState` | `react` | Loader state |
| `useForm` | `react-hook-form` | Form state + validation |
| `zodResolver` | `@hookform/resolvers/zod` | Schema validation |
| `Container` | `@/app/auth/shared/ContainerComponent` | Layout wrapper |
| `GoogleIcon` | `@/components/icons/google` | Google button icon |
| `CheckboxField, CustomButton, CustomLink, TextInput` | `@/components/shared` | UI components |
| `LoginFormData, loginSchema` | `@/schemas/auth` | Zod schema + type |
| `login` | `@/services/auth/helper` | Login API call |
| `handleApiError` | `@/utils/helpers` | Error toast |
| `showToast` | `@/utils/toast` | Success toast |

### State

| Variable | Type | Initial | Purpose |
|----------|------|---------|---------|
| `loader` | `boolean` | `false` | Disables submit button + shows spinner |

### Form Setup

```typescript
const { control, handleSubmit } = useForm<LoginFormData>({
  resolver: zodResolver(loginSchema),
  defaultValues: { email: '', password: '' },
});
```

### Handler: `onSubmit(values: LoginFormData)` — Step by Step

```
1. Set loader = true
2. const res = await login(values.email, values.password)
3. IF res is truthy:
   → showToast.success('Login Successful', 'Welcome back!', 3)
   → router.push('/home')
4. ELSE:
   → showToast.error('Login Failed', 'Please enter email and password', 3)
5. CATCH (error):
   → handleApiError(error)
6. FINALLY:
   → Set loader = false
```

### JSX Structure (exact text content)

```
<Container>
  <div className="w-full max-w-[400px] animate-page">
    <h2>"Welcome back"</h2>
    <p>"Enter your credentials to access your account"</p>

    <form onSubmit={handleSubmit(onSubmit)} autoComplete="off" className="space-y-5">
      <TextInput
        name="email" control={control} type="email"
        label="Email" placeholder="Enter your email" isRequired
      />
      <TextInput
        name="password" control={control} type="password"
        label="Password" placeholder="Enter your password" isRequired
      />

      <div className="flex items-center justify-between">
        <CheckboxField id="remember" label="Remember me" defaultChecked />
        <CustomLink href="/auth/forgotpassword">Forgot password?</CustomLink>
      </div>

      <CustomButton loading={loader} type="primary" htmlType="submit" fullWidth>
        Continue
      </CustomButton>

      <!-- divider: "or" -->

      <CustomButton type="default" fullWidth icon={<GoogleIcon className="size-4" />}>
        Continue with Google
      </CustomButton>

      <span>"Don't have an account?"</span>
      <CustomLink href="/auth/signup">Sign up</CustomLink>
    </form>
  </div>
</Container>
```

### Known Issues / Gotchas

- **"Remember me" checkbox** is rendered but `defaultChecked` is true and not wired to any logic — value is never read
- **Google sign-in button** is UI only — no `onClick` handler; Firebase Google auth is triggered via a different mechanism
- **`res` falsy path**: If `login()` returns a falsy value (unlikely given Axios), shows "Login Failed" toast — this path may be dead code since Axios throws on non-2xx

---

## 4. Signup Page

**File:** `src/app/auth/signup/SignupClient.tsx` (~5.6KB)

### Imports

| Import | Source | Purpose |
|--------|--------|---------|
| `useCallback, useEffect, useRef, useState` | `react` | State + effects |
| `useForm` | `react-hook-form` | Form state |
| `zodResolver` | `@hookform/resolvers/zod` | Validation |
| `debounce` | `lodash` | Org name check debounce |
| `useRouter, useSearchParams` | `next/navigation` | Navigation + URL params |
| `GoogleIcon` | `@/components/icons/google` | Google button icon |
| `CustomButton, CustomLink, TextInput` | `@/components/shared` | UI |
| `SignupFormData, signupSchema` | `@/schemas/auth` | Schema + type |
| `signup` | `@/services/auth/helper` | Signup API call |
| `axios` | `@/utils/axios` | Direct axios for org check |
| `handleApiError` | `@/utils/helpers` | Error toast |
| `showToast` | `@/utils/toast` | Success/warning toast |
| `Container` | `../shared/ContainerComponent` | Layout |

### Types

```typescript
interface ExistingOrg {
  id: number;
  name: string;
  slug: string;
  allow_access_requests: boolean;
}
```

### State

| Variable | Type | Initial | Purpose |
|----------|------|---------|---------|
| `_isLoading` | `boolean` | `true` | Initial page loading indicator (2s delay) |
| `loadingTimeoutRef` | `useRef<ReturnType<typeof setTimeout>>` | — | Cleanup for loading timeout |
| `loader` | `boolean` | `false` | Form submission spinner |
| `active` | `number` | `0` | Step indicator (0 = form, 1 = success) |
| `existingOrg` | `ExistingOrg \| null` | `null` | Org data if name already taken |
| `_checkingOrg` | `boolean` | `false` | Whether org check API is in flight |

### Form Setup

```typescript
const { control, handleSubmit } = useForm<SignupFormData>({
  resolver: zodResolver(signupSchema),
  defaultValues: { email: '', password: '', org_name: '' },
});
```

### useEffect #1 — Firebase detection

```
Deps: [params]
Logic:
  if params.get('firebase_signup') === 'true' → set active = 1
```

### useEffect #2 — Loading timeout

```
Deps: [] (mount only)
Logic:
  loadingTimeoutRef.current = setTimeout(() => set _isLoading = false, 2000)
Cleanup:
  clearTimeout(loadingTimeoutRef.current)
```

### Callback: `checkOrgExists` — Debounced org name check

```
Type: useCallback wrapping lodash.debounce (500ms)
Param: orgName: string

Step by step:
1. IF !orgName OR orgName.trim().length < 2 → set existingOrg = null, return
2. Set _checkingOrg = true
3. GET /auth/check_organization_exists?name=${encodeURIComponent(orgName.trim())}
4. IF res.data.exists === true → set existingOrg = res.data.organization
5. ELSE → set existingOrg = null
6. CATCH → set existingOrg = null
7. FINALLY → set _checkingOrg = false
```

**Triggered by:** `onValueChange` prop on the org_name `TextInput`:
```typescript
<TextInput onValueChange={(value) => checkOrgExists(value)} />
```

### Handler: `onSubmit(values: SignupFormData)` — Step by Step

```
1. IF existingOrg is not null:
   → showToast.warning('Organization Exists',
       'An organization with this name already exists. Please choose a different name or request access.', 5)
   → return (abort submission)
2. Set loader = true
3. const res = await signup(
     values.email,
     values.password,
     {},                          // profile (empty object)
     params.get('firebase_uid'),  // firebase_token (null if not in URL)
     values.org_name              // org_name (may be empty string)
   )
4. showToast.success('Account Created', 'Please check your email for verification', 4)
5. IF params.get('firebase_signup') === 'true':
   → router.push('/home')
6. ELSE:
   a. const redirect = params.get('redirect')
   b. IF redirect exists → localStorage.setItem('invite_redirect', redirect)
   c. router.push('/auth/check-email?email=' + encodeURIComponent(values.email))
7. IF res.status === 200:
   → Set loader = false
   → Set active = active + 1
8. CATCH (error):
   → handleApiError(error)
   → Set loader = false
```

### JSX Structure (exact text content)

```
<Container>
  <div className="w-full max-w-[400px] animate-page">
    <h2>"Create your account"</h2>
    <p>"Get started with AI Voice Agents in minutes"</p>

    <form onSubmit={handleSubmit(onSubmit)} autoComplete="off" className="space-y-5">
      <TextInput
        name="email" control={control} type="email"
        label="Email" placeholder="Enter your email" isRequired
      />
      <TextInput
        name="password" control={control} type="password"
        label="Password" placeholder="Create a password" isRequired
      />
      <TextInput
        name="org_name" control={control} type="text"
        label="Organisation name (optional)"
        placeholder="Enter your organisation name"
        onValueChange={(value) => checkOrgExists(value)}
      />

      <CustomButton loading={loader} type="primary" htmlType="submit" fullWidth>
        Create account
      </CustomButton>

      <!-- divider: "or" -->

      <CustomButton type="default" fullWidth icon={<GoogleIcon className="size-4" />}>
        Sign up with Google
      </CustomButton>

      <span>"Already have an account?"</span>
      <CustomLink href="/auth/login">Log in</CustomLink>
    </form>
  </div>
</Container>
```

### Known Issues / Gotchas

- **`_isLoading` state** is set but never read in JSX — appears to be dead code or intended for a loading skeleton that was removed
- **`active` state** is incremented but never checked in JSX — no multi-step UI implemented
- **`_checkingOrg` state** is tracked but not shown to user (no "checking..." indicator)
- **Org check endpoint** uses `axios` directly (not through a service function) — breaks the service layer pattern
- **`redirect` param handling**: Stored in localStorage before navigating to check-email, then read back after email verification in `verify_signup` page
- **Firebase flow**: Uses `params.get('firebase_uid')` as the token — this is a UID, not a Firebase ID token
- **Error in step 7**: `res.status === 200` check runs after navigation has already started — may cause state update on unmounted component

---

## 5. Forgot Password Page

**File:** `src/app/auth/forgotpassword/page.tsx` (~2.5KB)

**Note:** This is a single `'use client'` file — no Suspense wrapper (doesn't use `useSearchParams`).

### State

| Variable | Type | Initial | Purpose |
|----------|------|---------|---------|
| `loader` | `boolean` | `false` | Submit button loading |

### Form Setup

```typescript
const { control, handleSubmit } = useForm<ForgotPasswordFormData>({
  resolver: zodResolver(forgotPasswordSchema),
  defaultValues: { email: '' },
});
```

### Handler: `onSubmit(values: ForgotPasswordFormData)`

```
1. Set loader = true
2. const res = await forgotPassword(values.email)
3. IF res is truthy:
   → showToast.success('Email Sent', 'Password reset instructions sent to your email', 4)
   → Set loader = false
4. CATCH (error):
   → handleApiError(error)
   → Set loader = false
```

**Gotcha:** `loader = false` is set inside the `if` block and `catch` block separately — not in a `finally`. If `res` is falsy (unlikely), loader stays true forever.

### JSX Structure (exact text)

```
<Container>
  <h2>"Reset password"</h2>
  <p>"If there's an account associated with this email, we will send you a link to reset your password."</p>

  <form className="space-y-5">
    <TextInput name="email" label="Email" placeholder="Enter your email" isRequired />

    <CustomButton loading={loader} type="primary" htmlType="submit" fullWidth>
      Reset Password
    </CustomButton>
    <CustomButton type="default" fullWidth onClick={() => window.history.back()}>
      Cancel
    </CustomButton>

    <span>"Remember your password?"</span>
    <CustomLink href="/auth/login">Log in</CustomLink>
  </form>
</Container>
```

**Cancel button:** Uses `window.history.back()` — not `router.back()` or `router.push()`.

---

## 6. Reset Password Page

**File:** `src/app/auth/reset-password/page.tsx` (~2.7KB)

### Structure

- `ResetPasswordContent` — Inner `'use client'` component
- `ResetPasswordPage` — Default export wrapping in `<Suspense fallback={null}>`

### URL Parameters (from email reset link)

| Param | Purpose | Example |
|-------|---------|---------|
| `email` | User's email | `user@example.com` |
| `token` | Reset token from backend | `abc123...` |

### State

| Variable | Type | Initial | Purpose |
|----------|------|---------|---------|
| `loader` | `boolean` | `false` | Submit button loading |

### Form Setup

```typescript
const { control, handleSubmit } = useForm<ResetPasswordFormData>({
  resolver: zodResolver(resetPasswordSchema),
  defaultValues: { password: '', confirm_password: '' },
});
```

### Handler: `onSubmit(values: ResetPasswordFormData)`

```
1. Set loader = true
2. GET /auth/acceptForgotPassword?email=${params.get('email')}&password=${values.password.trim()}&token=${params.get('token')}
   ⚠️ NOTE: This is a GET request with password in query string
3. IF res is truthy:
   → showToast.success('Password Reset', 'Your password has been updated successfully', 4)
   → setTimeout(() => router.push('/auth/login'), 2000)  // 2 second delay before redirect
4. CATCH (error):
   → handleApiError(error)
5. FINALLY:
   → Set loader = false
```

**Security note:** Password is sent as a query parameter in a GET request — this means it appears in server logs and browser history. This is a potential security concern.

### JSX Structure (exact text)

```
<Container>
  <h2>"Reset password"</h2>
  <p>"Enter your new password below"</p>

  <form className="space-y-5">
    <TextInput name="password" label="New Password" placeholder="Enter new password" isRequired />
    <TextInput name="confirm_password" label="Confirm Password" placeholder="Confirm new password" isRequired />

    <CustomButton loading={loader} type="primary" htmlType="submit" fullWidth>
      Reset Password
    </CustomButton>
  </form>
</Container>
```

---

## 7. Check Email Page

**File:** `src/app/auth/check-email/page.tsx` (~1.6KB)

### Structure

- `CheckEmailContent` — Inner component
- `CheckEmailPage` — Default export with `<Suspense fallback={null}>`

### URL Parameters

| Param | Purpose | Fallback |
|-------|---------|----------|
| `email` | Display email in confirmation | `'your email'` |

### Logic

Purely presentational — **no API calls, no state, no handlers**.

### JSX Structure (exact text)

```
<Container>
  <div className="w-full max-w-[400px] animate-page text-center">
    <!-- Icon: Mail from lucide-react, inside rounded bg-primary/10 div -->
    <div className="mx-auto mb-6 flex size-16 items-center justify-center rounded-2xl bg-primary/10">
      <Mail className="size-8 text-primary" />
    </div>

    <h2>"Check your email"</h2>
    <p>"We've sent an email to"</p>
    <p className="font-semibold">{email}</p>
    <p>"Click the link in the email to verify your account."</p>

    <p>"Didn't receive the email? Check your spam folder or"
      <CustomLink href="/auth/login">try again</CustomLink>
    </p>
  </div>
</Container>
```

---

## 8. Email Verification Page

**File:** `src/app/auth/verify_signup/page.tsx` (~2.2KB)

### Structure

- `EmailVerificationContent` — Inner component
- `EmailVerification` — Default export (`React.FC`) with `<Suspense fallback={null}>`

### URL Parameters (from verification email link)

| Param | Purpose |
|-------|---------|
| `email` | User's email |
| `code` | Verification code |
| `user_id` | User ID |

### State

| Variable | Type | Initial | Purpose |
|----------|------|---------|---------|
| `loader` | `boolean` | `false` | Button loading |

### Handler: `handleSubmit()` — Step by Step

```
1. Set loader = true
2. GET /auth/verify_user_email?email=${params.get('email')}&code=${params.get('code')}&user_id=${params.get('user_id')}
3. Set loader = false
4. IF res is truthy:
   → showToast.success('Email Verified', 'Your email has been verified successfully', 4)
   → const inviteRedirect = localStorage.getItem('invite_redirect')
   → IF inviteRedirect:
       localStorage.removeItem('invite_redirect')
       router.push(inviteRedirect)
   → ELSE:
       router.push('/auth/login')
5. CATCH (error):
   → handleApiError(error)
6. FINALLY:
   → Set loader = false
```

**Note:** `loader = false` is set both in step 3 (before the truthy check) and in the `finally` block — redundant but harmless.

### JSX Structure (exact text)

```
<Container>
  <div className="w-full max-w-[400px] animate-page text-center">
    <!-- Icon: CheckCircle from lucide-react -->
    <div className="mx-auto mb-6 flex size-16 items-center justify-center rounded-2xl bg-primary/10">
      <CheckCircle className="size-8 text-primary" />
    </div>

    <h2>"Email Verification"</h2>
    <p>"To complete the verification process, please click the button below:"</p>

    <CustomButton loading={loader} type="primary" onClick={handleSubmit} fullWidth>
      Verify Email
    </CustomButton>
  </div>
</Container>
```

---

## 9. Shared Container Component

**File:** `src/app/auth/shared/ContainerComponent.tsx` (~6.9KB)

### Props

```typescript
interface ContainerProps {
  children: React.ReactNode;
}
```

Wrapped in `React.memo`. Display name set to `'Container'`.

### Constants

```typescript
const AUDIO_BAR_COUNT = 12;
const FEATURES = [
  { icon: Bot,    value: '50+',    label: 'Voice Models' },
  { icon: Zap,    value: '<500ms', label: 'Latency' },
  { icon: Shield, value: '99.9%',  label: 'Uptime' },
];
```

### JSX Structure (detailed)

```
<div className="flex min-h-screen">

  <!-- LEFT SIDE: Form area -->
  <div className="relative flex flex-1 flex-col bg-background">

    <header className="absolute left-6 top-6 z-10 ...">
      <Logo className="h-12" showTagline />
      <ThemeToggle />
    </header>

    <div className="flex flex-1 items-center justify-center px-6">
      {children}   <!-- Auth form content injected here -->
    </div>
  </div>

  <!-- RIGHT SIDE: Branding (hidden on mobile: className="hidden md:flex") -->
  <div style={{ background: 'linear-gradient(145deg, #0e0e0f 0%, #1a1035 30%, #2d1b69 60%, #4c1d95 100%)' }}>

    <!-- Dot grid overlay (32x32 grid, 4% opacity white dots) -->

    <!-- 3 Floating orbs (CSS animations, no JS) -->
    Orb 1: -left-24 -top-24, 400px, purple, animation: auth-float-1 18s
    Orb 2: -bottom-32 -right-24, 500px, cyan, animation: auth-float-2 22s
    Orb 3: left-30% top-20%, 300px, pink, animation: auth-float-3 15s

    <!-- Centered content -->
    <div className="relative z-10 flex flex-1 flex-col items-center justify-center p-12">

      <!-- Neural network visual: BrainCircuit center + 3 satellites (Mic, Sparkles, Bot) -->
      <!-- Satellites pulse with: animation: pulse-ring 3s ease-in-out infinite (staggered 0, 0.5s, 1s) -->

      <!-- Voice waveform: 12 bars, 3px wide, animation: audio-bar 1.4s (staggered 0.1s each) -->

      <h1>"Build AI Agents\nThat Sound Human"</h1>
      <p>"Create, deploy, and manage intelligent voice agents with configurable LLM, STT, and TTS pipelines."</p>

      <!-- Feature stats: 3 glassmorphism cards from FEATURES array -->
      <!-- Each: icon + value + label, bg rgba(255,255,255,0.04), backdrop-blur 16px -->
    </div>

    <!-- Trust indicators (bottom pinned) -->
    <div>"Trusted by 1,000+ teams · SOC 2 Compliant · 99.9% Uptime"</div>
  </div>
</div>
```

### CSS Animations Required

The component references these keyframe animations (must be defined in global CSS):
- `auth-float-1` — 18s infinite float for orb 1
- `auth-float-2` — 22s infinite float for orb 2
- `auth-float-3` — 15s infinite float for orb 3
- `pulse-ring` — 3s pulsing for neural network satellites
- `audio-bar` — 1.4s waveform bar animation

---

## 10. Auth Service Layer

**File:** `src/services/auth/helper.tsx` (~2.4KB)

### `setToken(LogInData: any)` — Cookie Writer

```
Step by step:
1. const decoded = decodeJWT(LogInData['access_token'])
2. const expires = new Date(decoded.exp * 1000)   // JWT exp is in seconds → convert to ms
3. Cookies.set('tone_access_token', LogInData['access_token'], { expires })
4. Cookies.set('user_id', LogInData?.['user_id'], { expires })
5. Cookies.set('login_data', JSON.stringify(LogInData), { expires })
6. Cookies.set('org_tenant_id',
     LogInData['organizations']?.length
       ? LogInData['organizations']?.[0]?.['id']   // First org ID
       : '',                                        // Empty string if no orgs
     { expires }
   )
7. return LogInData
```

### `login(email: string, password: string)`

```
1. POST /auth/login  with { email, password }
2. const LogInData = res.data
3. setToken(LogInData)
4. return LogInData
```

### `signup(email, password, profile = {}, firebase_token = null, org_name = null)`

**Two distinct code paths:**

**Path A — Firebase** (when `firebase_token !== null`):
```
1. POST /auth/signup_with_firebase
   Headers: { Authorization: `Bearer ${firebase_token}` }
   Payload: { email, profile }
2. setToken(res.data)     // User is logged in immediately
3. return (from Axios promise)
CATCH: handleApiError(err)
```

**Path B — Standard** (when `firebase_token === null`):
```
1. POST /auth/signup
   Payload: { email, password, profile, org_name }
2. return axios response   // No setToken call — user must verify email first
```

**Critical difference:** Firebase path calls `setToken()` (immediate login), standard path does NOT (requires email verification → separate login).

### `forgotPassword(email: string)`

```
1. GET /auth/forget-password  with params: { email }
2. return res.data
```

### `getOrganization()`

```
1. GET /org/get_associated_tenants
2. return res
```

### `createOrganization(data: any)`

```
1. POST /org/create_tenants?name=${data.name}
2. return res
```

### `createteam(data: string)` — Legacy alias

```
1. POST /org/create_tenants?name=${data}
2. return res
```

### API Endpoints Summary

| Function | Method | Endpoint | Auth Header | Payload |
|----------|--------|----------|-------------|---------|
| `login` | POST | `/auth/login` | Auto (interceptor) | `{ email, password }` |
| `signup` (standard) | POST | `/auth/signup` | Auto (interceptor) | `{ email, password, profile, org_name }` |
| `signup` (Firebase) | POST | `/auth/signup_with_firebase` | `Bearer {firebase_token}` | `{ email, profile }` |
| `forgotPassword` | GET | `/auth/forget-password` | Auto (interceptor) | Query: `{ email }` |
| `getOrganization` | GET | `/org/get_associated_tenants` | Auto (interceptor) | — |
| `createOrganization` | POST | `/org/create_tenants` | Auto (interceptor) | Query: `?name={name}` |

---

## 11. Validation Schemas (Zod)

**File:** `src/schemas/auth.ts` (~1.3KB)

### loginSchema

| Field | Type | Rules | Error Messages |
|-------|------|-------|----------------|
| `email` | `string` | Required, valid email | `'Email is required'`, `'Please enter a valid email'` |
| `password` | `string` | Min 6 chars | `'Password must be at least 6 characters'` |

**Inferred type:** `LoginFormData = z.infer<typeof loginSchema>`

### signupSchema

| Field | Type | Rules | Error Messages |
|-------|------|-------|----------------|
| `email` | `string` | Required, valid email | `'Email is required'`, `'Please enter a valid email'` |
| `password` | `string` | Min 8 chars | `'Password must be at least 8 characters'` |
| `org_name` | `string?` | Optional; if provided, min 2 chars (after trim) | `'Organisation name must be at least 2 characters'` |

**Note:** Password min length differs from login (8 vs 6).

**`org_name` validation logic:**
```typescript
z.string().optional().refine((val) => !val || val.trim().length >= 2, {
  message: 'Organisation name must be at least 2 characters',
})
```
Allows: `undefined`, `''`, or any string with 2+ non-whitespace chars.

### forgotPasswordSchema

| Field | Type | Rules | Error Messages |
|-------|------|-------|----------------|
| `email` | `string` | Required, valid email | `'Email is required'`, `'Please enter a valid email'` |

### resetPasswordSchema

| Field | Type | Rules | Error Messages |
|-------|------|-------|----------------|
| `password` | `string` | Min 8 chars | `'Password must be at least 8 characters'` |
| `confirm_password` | `string` | Required, must match `password` | `'Please confirm your password'`, `'Passwords do not match'` |

**Cross-field validation:**
```typescript
.refine((data) => data.password === data.confirm_password, {
  message: 'Passwords do not match',
  path: ['confirm_password'],  // Error shows on confirm field
})
```

---

## 12. Atoms (Global State)

**File:** `src/atoms/AuthAtom.tsx` (~2.5KB)

### Type Definitions

```typescript
interface User {
  id: string;
  email: string;
  username?: string;
  first_name?: string;
  last_name?: string;
  role?: 'owner' | 'admin' | 'member' | 'viewer';
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}
```

### authAtom

- **Type:** `atom<AuthState>`
- **Default:** `{ user: null, isAuthenticated: false, isLoading: false }`

### logoutAtom (write-only) — Step by Step

```
1. set(authAtom, { ...get(authAtom), isLoading: true })
2. TRY:
   a. Cookies.remove('tone_access_token')
   b. Cookies.remove('org_tenant_id')
   c. Cookies.remove('user_id')
   d. Cookies.remove('login_data')
   e. localStorage.removeItem('auth')
   f. localStorage.removeItem('user')
   g. sessionStorage.clear()
   h. set(authAtom, { user: null, isAuthenticated: false, isLoading: false })
   i. window.location.href = '/auth/login'
3. CATCH:
   a. Still remove all 4 cookies (same as above)
   b. set(authAtom, { user: null, isAuthenticated: false, isLoading: false })
   c. window.location.href = '/auth/login'
```

**Note:** Uses `window.location.href` (full page reload), not `router.push` — this ensures all client-side state is cleared.

### getCurrentUserAtom (write-only) — Step by Step

```
1. set(authAtom, { ...get(authAtom), isLoading: true })
2. TRY:
   a. const loginDataCookie = Cookies.get('login_data')
   b. IF !loginDataCookie → set authAtom with user: null, return
   c. const parsedData = JSON.parse(loginDataCookie)
   d. const tenantId = Cookies.get('org_tenant_id')
   e. const currentOrgId = tenantId ? parseInt(tenantId, 10) : null
   f. let currentOrg:
      - IF currentOrgId exists → find in parsedData.organizations where org.id === currentOrgId
      - ELSE → parsedData.organizations?.[0]
   g. Build user object:
      {
        id: parsedData.user_id,
        email: parsedData.email,
        username: parsedData.username,
        first_name: parsedData.first_name,
        last_name: parsedData.last_name,
        role: currentOrg?.role
      }
   h. set(authAtom, { user, isAuthenticated: true, isLoading: false })
3. CATCH:
   → set(authAtom, { user: null, isAuthenticated: false, isLoading: false })
```

**Gotcha:** `parseInt(tenantId, 10)` converts string to integer for comparison with `org.id` — if `org.id` is stored differently (e.g., string), the match will fail and fall back to first org.

---

## 13. Shared UI Components Used in Auth

### TextInput — `src/components/shared/TextInput.tsx`

**Two modes:**
- **Plain** (no `control` prop) — Standalone input
- **Form** (with `control` prop) — Wrapped in RHF `Controller`

**Key props for auth forms:**

| Prop | Type | Default | Auth Usage |
|------|------|---------|------------|
| `name` | `string` | — | Form field name |
| `control` | `Control` | — | RHF form control |
| `type` | `string` | `'text'` | `'email'`, `'password'`, `'text'` |
| `label` | `string?` | — | Field label above input |
| `placeholder` | `string?` | — | Input placeholder text |
| `isRequired` | `boolean` | `false` | Adds required indicator |
| `onValueChange` | `(value: string) => void` | — | Callback on value change (used for org check) |

**Password visibility toggle:**
- When `type="password"`, renders Eye/EyeOff toggle button at right side
- Toggle state: `showPassword` (local useState)
- Input type switches between `'text'` and `'password'`
- Toggle button: `tabIndex={-1}`, `onMouseDown={e.preventDefault()}` (prevents blur)

**Form integration behavior:**
```typescript
<Controller
  render={({ field, fieldState }) => (
    <PlainTextInput
      value={field.value ?? ''}
      onChange={(e) => {
        field.onChange(e.target.value);
        onValueChange?.(e.target.value);  // Called AFTER RHF update
      }}
      onBlur={field.onBlur}
      error={error ?? !!fieldState.error}
      helperText={helperText ?? fieldState.error?.message}
    />
  )}
/>
```

**Loading skeleton:** Renders `<Skeleton>` elements instead of actual input when `loading={true}`.

### CustomButton — `src/components/shared/CustomButton.tsx`

**Type-to-variant mapping:**

| `type` prop | shadcn `variant` | Visual |
|-------------|------------------|--------|
| `'primary'` | `'default'` | Solid primary color |
| `'default'` | `'outline'` | Border only |
| `'text'` | `'ghost'` | No background |
| `'link'` | `'link'` | Underlined text |
| `'danger'` | `'destructive'` | Red/destructive |

**Key props:**

| Prop | Type | Default | Purpose |
|------|------|---------|---------|
| `loading` | `boolean` | `false` | Shows Loader2 spinner, disables button |
| `type` | `string` | `'default'` | Visual variant |
| `htmlType` | `string` | `'button'` | HTML type attribute (`'submit'` for forms) |
| `fullWidth` | `boolean` | `false` | Adds `w-full` class |
| `icon` | `ReactNode` | — | Icon before text |
| `disabled` | `boolean` | `false` | Disables button |

**Click prevention:** When `loading` or `disabled` is true, `handleClick` returns early + `e.stopPropagation()`.

**Loading rendering:**
```typescript
{loading ? <Loader2 className="h-4 w-4 animate-spin" /> : icon && <span>{icon}</span>}
{children}
```
The `children` text still renders during loading — only the icon is replaced with spinner.

### CustomLink — `src/components/shared/CustomLink.tsx`

Wraps Next.js `<Link>`. Default styling: `text-sm font-medium text-primary underline-offset-2 hover:underline cursor-pointer`.

### CheckboxField — `src/components/shared/CheckboxField.tsx`

Two modes (same as TextInput): Plain or Form (with `control` prop). Uses shadcn `Checkbox` component internally.

### Logo — `src/components/shared/Logo.tsx`

SVG logo with gradient colors. Props: `className`, `showTagline`, `inverted`, `iconOnly`. Text reads "Tone".

### ThemeToggle — `src/components/shared/ThemeToggle.tsx`

Uses `next-themes` `useTheme()`. Shows Sun (dark mode) or Moon (light mode). Click toggles between `'light'` and `'dark'`.

**Hydration safety:** Renders a static button until `mounted === true` (useEffect sets it on mount).

---

## 14. Utilities

### JWT Decoder — `src/utils/jwt.tsx`

```typescript
export function decodeJWT(token: any) {
  if (token) {
    const tokenDecodablePart = token.split('.')[1];
    const decoded = Buffer.from(tokenDecodablePart, 'base64').toString();
    return JSON.parse(decoded);
  }
  // Returns undefined if no token
}
```

**Decoded payload fields used:** `exp` (expiration timestamp in seconds)

### Error Handler — `src/utils/helpers.ts`

```typescript
export function handleApiError(error: unknown) {
  let message = 'Something went wrong. Please try again.';
  if (typeof error === 'object' && error !== null) {
    const detail = (error as any).response?.data?.detail;
    if (typeof detail === 'string' && detail) {
      message = detail;
    }
  }
  showToast.error(message);
}
```

**Note:** Calls `showToast.error(message)` with a single argument — no title. The title defaults to the message itself in the toast.

### Toast — `src/utils/toast.tsx`

```typescript
export const showToast = {
  success: (title, description?, duration?) =>
    toast.success(title, { description, duration: duration ? duration * 1000 : 3000 }),
  error: (title, description?, duration?) =>
    toast.error(title, { description, duration: duration ? duration * 1000 : 5000 }),
  warning: (title, description?, duration?) =>
    toast.warning(title, { description, duration: duration ? duration * 1000 : 4000 }),
  info: (title, description?, duration?) =>
    toast.info(title, { description, duration: duration ? duration * 1000 : 3000 }),
};
```

**Duration:** Input is in **seconds** (multiplied by 1000 internally). Default varies by type.

**DOM selector for tests:** `page.locator('[data-sonner-toast]')`

### Axios Instance — `src/utils/axios.ts`

```typescript
const axiosInstance = axios.create({ baseURL: BACKEND_URL });

// Request interceptor
axiosInstance.interceptors.request.use((config) => {
  const tenant_id = Cookies.get('org_tenant_id');
  const accessToken = Cookies.get('tone_access_token');
  if (tenant_id) config.headers['tenant_id'] = tenant_id;
  if (accessToken) config.headers['Authorization'] = `Bearer ${accessToken}`;
  return config;
});

// Response interceptor
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) { /* empty */ }
    return Promise.reject(error);
  },
);
```

**401 handling:** Currently empty — no auto-logout or token refresh on 401.

---

## 15. Constants

**File:** `src/constants/index.ts`

| Constant | Value | Used In |
|----------|-------|---------|
| `ACCESS_TOKEN` | `'tone_access_token'` | Cookie key — middleware, axios, setToken, logout |
| `REFRESH_TOKEN` | `'tone_refresh_token'` | Defined but **never used** in auth flows |
| `TENANT_ID` | `'org_tenant_id'` | Cookie key — axios interceptor, setToken, getCurrentUserAtom |
| `USER_PROFILE` | `'profile'` | Defined but rarely used |
| `SIGNUP` | `'/auth/signup'` | API endpoint path |
| `FORGOT_PASSWORD` | `'/auth/forgot-password'` | API endpoint path |
| `FIREBASE_SIGNUP` | `'/auth/signup_with_firebase'` | API endpoint path |
| `BACKEND_URL` | `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1` | Axios base URL |

---

## 16. Cookies & Token Management

### Cookie Reference

| Cookie Name | Content | Set By | Read By | Expiration |
|-------------|---------|--------|---------|------------|
| `tone_access_token` | JWT token string | `setToken()` | Middleware, Axios interceptor | `new Date(JWT.exp * 1000)` |
| `org_tenant_id` | Org ID (string of integer) | `setToken()` | Axios interceptor, `getCurrentUserAtom` | Same as above |
| `user_id` | User ID string | `setToken()` | Not read in frontend | Same as above |
| `login_data` | JSON string of full login response | `setToken()` | `getCurrentUserAtom` | Same as above |

### `login_data` Cookie Structure

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user_id": "uuid-string",
  "email": "user@example.com",
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "organizations": [
    {
      "id": 1,
      "name": "My Org",
      "role": "owner"
    },
    {
      "id": 2,
      "name": "Other Org",
      "role": "member"
    }
  ]
}
```

### Token Lifecycle

```
Created    → login() or Firebase signup() → setToken() writes 4 cookies
Read       → Every request (Axios interceptor) + every page load (middleware)
Refreshed  → NOT IMPLEMENTED (no refresh token flow)
Destroyed  → logoutAtom removes all 4 cookies
             OR browser auto-removes on JWT expiration
```

### Organization Resolution Flow (in getCurrentUserAtom)

```
1. Read org_tenant_id cookie → "2" (string)
2. parseInt("2", 10) → 2 (number)
3. Find in organizations array: org.id === 2
4. IF found → use that org (role = org.role)
5. IF not found → fallback to organizations[0]
6. IF no organizations → role = undefined
```

---

## 17. Key Concepts & Patterns

### Authentication Flow Summary

| Flow | Trigger | API Call | Tokens Set? | Redirect |
|------|---------|----------|-------------|----------|
| Standard Login | Submit email+password | `POST /auth/login` | Yes (`setToken`) | `/home` |
| Standard Signup | Submit form | `POST /auth/signup` | **No** | `/auth/check-email?email=...` |
| Firebase Signup | URL has `firebase_signup=true` | `POST /auth/signup_with_firebase` | Yes (`setToken`) | `/home` |
| Forgot Password | Submit email | `GET /auth/forget-password` | No | Stay on page (toast only) |
| Reset Password | Submit new password | `GET /auth/acceptForgotPassword` | No | `/auth/login` (2s delay) |
| Verify Email | Click "Verify Email" button | `GET /auth/verify_user_email` | No | `/auth/login` or `invite_redirect` |
| Logout | Click logout in ProfileMenu | None | Removes all | `/auth/login` (full reload) |

### Form Pattern (all auth forms follow this)

```typescript
// 1. Schema
const { control, handleSubmit } = useForm<SchemaType>({
  resolver: zodResolver(schema),
  defaultValues: { field1: '', field2: '' },
});

// 2. State
const [loader, setLoader] = useState(false);

// 3. Handler
const onSubmit = async (values: SchemaType) => {
  setLoader(true);
  try {
    const res = await apiCall(values);
    showToast.success('Title', 'Description', duration);
    router.push('/destination');
  } catch (error) {
    handleApiError(error);
  } finally {
    setLoader(false);
  }
};

// 4. JSX
<Container>
  <form onSubmit={handleSubmit(onSubmit)} autoComplete="off" className="space-y-5">
    <TextInput name="field" control={control} ... />
    <CustomButton loading={loader} type="primary" htmlType="submit" fullWidth>
      Submit
    </CustomButton>
  </form>
</Container>
```

### Invite Redirect Pattern

```
1. User receives invitation email with link to /auth/signup?redirect=/verify/user_to_workspace?...
2. SignupClient reads params.get('redirect')
3. Stores in localStorage: invite_redirect = redirect URL
4. User completes signup → /auth/check-email
5. User clicks verification link → /auth/verify_signup
6. verify_signup reads localStorage.getItem('invite_redirect')
7. If present: removes from storage, redirects there
8. If absent: redirects to /auth/login
```

### Multi-Tenancy

- Users belong to 1+ organizations (stored in `login_data` cookie)
- `org_tenant_id` cookie = active organization (integer ID as string)
- Axios interceptor sends `tenant_id` header on every request
- `getCurrentUserAtom` resolves user role from active org
- On first login, auto-selects `organizations[0].id` as default

### Toast Messages Reference

| Page | Event | Method | Title | Description | Duration |
|------|-------|--------|-------|-------------|----------|
| Login | Success | `success` | `'Login Successful'` | `'Welcome back!'` | 3s |
| Login | API error | `error` | (from API detail) | — | 5s |
| Login | Falsy response | `error` | `'Login Failed'` | `'Please enter email and password'` | 3s |
| Signup | Success | `success` | `'Account Created'` | `'Please check your email for verification'` | 4s |
| Signup | Org exists | `warning` | `'Organization Exists'` | `'An organization with this name...'` | 5s |
| Forgot | Success | `success` | `'Email Sent'` | `'Password reset instructions sent to your email'` | 4s |
| Reset | Success | `success` | `'Password Reset'` | `'Your password has been updated successfully'` | 4s |
| Verify | Success | `success` | `'Email Verified'` | `'Your email has been verified successfully'` | 4s |

---

## 18. Debugging Guide

### Common Bug Scenarios

#### "User can't log in" — Login returns success but stays on login page

**Check:**
1. Is `login()` in `helper.tsx` returning data? → Add console.log before `setToken()`
2. Is `setToken()` decoding JWT correctly? → Check `decodeJWT()` — the token must have 3 dot-separated segments
3. Is the cookie being set? → Check browser DevTools → Application → Cookies for `tone_access_token`
4. Is `router.push('/home')` executing? → The `res` truthy check might be failing

**Files to read:** `src/services/auth/helper.tsx` (lines for `login` and `setToken`)

#### "User logged out unexpectedly"

**Check:**
1. Cookie expiration — `setToken()` uses `new Date(decoded.exp * 1000)`. If server sends short-lived JWTs, cookies expire quickly
2. No refresh token flow exists — when JWT expires, user must re-login
3. 401 response interceptor is empty — no auto-redirect on expired token
4. Check if `logoutAtom` is being called unintentionally

**Files to read:** `src/utils/axios.ts` (response interceptor), `src/atoms/AuthAtom.tsx` (logoutAtom)

#### "Wrong organization/tenant after login"

**Check:**
1. `setToken()` always picks `organizations[0].id` as `org_tenant_id` — if user expects a different org, it won't be selected
2. `getCurrentUserAtom` uses `parseInt(tenantId, 10)` to compare — type mismatch between string and number IDs will cause fallback to first org
3. Cookie `org_tenant_id` stores the value as a string

**Files to read:** `src/services/auth/helper.tsx` (setToken org logic), `src/atoms/AuthAtom.tsx` (getCurrentUserAtom)

#### "Signup fails silently"

**Check:**
1. Standard signup does NOT call `setToken()` — user must verify email first
2. If `existingOrg` is set, submission is blocked with a warning toast (not error)
3. The `catch` block calls `handleApiError()` which only shows generic toast
4. Check if org check endpoint `/auth/check_organization_exists` is returning unexpected data

**Files to read:** `src/app/auth/signup/SignupClient.tsx` (onSubmit), `src/services/auth/helper.tsx` (signup)

#### "Password reset link doesn't work"

**Check:**
1. Reset page reads `email` and `token` from URL search params — if either is missing, the API call fails
2. The API call is a **GET** with password in query string — URL encoding issues with special characters in password
3. After success, there's a 2-second `setTimeout` before redirect — user might click away

**Files to read:** `src/app/auth/reset-password/page.tsx` (onSubmit)

#### "Email verification redirect goes wrong"

**Check:**
1. `invite_redirect` in localStorage — if set from a previous signup flow, it may redirect to an unexpected URL
2. The verification page reads `email`, `code`, `user_id` from URL params — all must be present
3. The API call is a GET to `/auth/verify_user_email`

**Files to read:** `src/app/auth/verify_signup/page.tsx` (handleSubmit)

#### "Toast not showing"

**Check:**
1. Duration is in seconds (converted to ms internally) — `showToast.success('Title', 'Desc', 3)` = 3000ms
2. `handleApiError` calls `showToast.error(message)` with a single arg — the message becomes the title
3. Sonner component must be mounted in the app layout — check for `<Toaster />` in root layout
4. Test selector: `[data-sonner-toast]`

#### "Auth headers missing on API calls"

**Check:**
1. Axios interceptor reads cookies on every request — if cookies aren't set yet, headers will be missing
2. `tenant_id` header (not `Authorization`) is only set if `org_tenant_id` cookie exists
3. Firebase signup uses custom Authorization header (overrides interceptor) — check for conflicts
4. The interceptor uses `Cookies.get()` from `js-cookie` — ensure the cookie isn't HttpOnly

**Files to read:** `src/utils/axios.ts`

### State Flow Diagram

```
Login Success:
  login() → setToken() → cookies written → router.push('/home')
  → Dashboard mounts → ProfileMenu → getCurrentUserAtom → reads cookies → hydrates authAtom

Page Refresh:
  Browser sends tone_access_token cookie → middleware allows → page loads
  → ProfileMenu component → getCurrentUserAtom → parses login_data cookie → hydrates user

Logout:
  ProfileMenu → logoutAtom → removes 4 cookies + localStorage + sessionStorage
  → window.location.href = '/auth/login' (full page reload)
  → middleware sees no cookie → login page loads
```

---

## 19. How to Extend (Common Scenarios)

### Add a New Auth Page (e.g., `/auth/onboard`)

**Files to create/modify:**

1. **Create** `src/app/auth/onboard/page.tsx`:
   ```typescript
   import { Suspense } from 'react';
   import OnboardClient from './OnboardClient';
   export default function OnboardPage() {
     return <Suspense fallback={null}><OnboardClient /></Suspense>;
   }
   ```

2. **Create** `src/app/auth/onboard/OnboardClient.tsx`:
   - Add `'use client'` directive
   - Import `Container` from `'@/app/auth/shared/ContainerComponent'`
   - Follow the form pattern from Section 17
   - Add Zod schema if form validation needed (step 3)

3. **If form validation needed** — Update `src/schemas/auth.ts`:
   ```typescript
   export const onboardSchema = z.object({ ... });
   export type OnboardFormData = z.infer<typeof onboardSchema>;
   ```

4. **Verify middleware** — `/auth/onboard` is already in `PUBLIC_PATHS` array. If your route is different, add it to `src/middleware.ts`.

5. **Update this doc** — Add route to Section 1 table and navigation diagram.

### Add a New Form Field to Signup

**Files to modify (in order):**

1. `src/schemas/auth.ts` — Add field to `signupSchema`:
   ```typescript
   phone: z.string().optional(),
   ```
   Type `SignupFormData` updates automatically via Zod inference.

2. `src/app/auth/signup/SignupClient.tsx` — Add TextInput:
   ```typescript
   <TextInput name="phone" control={control} label="Phone" placeholder="..." />
   ```

3. `src/services/auth/helper.tsx` — Update `signup()` to include in payload:
   ```typescript
   // Add to the POST body
   { email, password, profile, org_name, phone: values.phone }
   ```

4. **Update this doc** — Add field to Section 4 and Section 11.

### Add OAuth Provider (e.g., GitHub)

**Files to modify:**

1. `src/app/auth/login/LoginPage.tsx` — Add provider button:
   ```typescript
   <CustomButton type="default" fullWidth icon={<GithubIcon />} onClick={handleGithubLogin}>
     Continue with GitHub
   </CustomButton>
   ```

2. `src/app/auth/signup/SignupClient.tsx` — Add matching button.

3. **Create GitHub icon** in `src/components/icons/github.tsx`.

4. `src/services/auth/helper.tsx` — Either:
   - Reuse Firebase path with different token type
   - Or add new endpoint function for GitHub OAuth

5. Ensure `setToken()` is called with the response (same cookie structure).

### Add Role-Based Redirect After Login

**Files to modify:**

1. `src/app/auth/login/LoginPage.tsx` — Modify `onSubmit`:
   ```typescript
   const res = await login(values.email, values.password);
   const role = res.organizations?.[0]?.role;
   if (role === 'admin') router.push('/settings');
   else router.push('/home');
   ```

### Implement Token Refresh

**Files to modify:**

1. `src/utils/axios.ts` — Add 401 handling in response interceptor:
   ```typescript
   if (error?.response?.status === 401) {
     const refreshToken = Cookies.get('tone_refresh_token');
     // Call refresh endpoint, update cookies, retry request
   }
   ```

2. `src/services/auth/helper.tsx` — Add `refreshToken()` function.

3. `src/constants/index.ts` — `REFRESH_TOKEN` constant already exists.

### Implement "Remember Me" Functionality

**Files to modify:**

1. `src/app/auth/login/LoginPage.tsx` — Read checkbox value:
   ```typescript
   const { control, handleSubmit, getValues } = useForm(...);
   // In onSubmit: pass getValues('remember') to login()
   ```

2. `src/services/auth/helper.tsx` — Modify `login()` and `setToken()`:
   ```typescript
   export async function login(email, password, rememberMe = false) {
     // ... pass rememberMe to setToken
   }
   export function setToken(data, rememberMe = false) {
     const expires = rememberMe
       ? new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)  // 30 days
       : new Date(decoded.exp * 1000);                       // JWT expiry
   }
   ```

### Add Email/Password Change (Authenticated User)

**Files to create/modify:**

1. **Create** service function in `src/services/auth/helper.tsx`:
   ```typescript
   export async function changePassword(currentPassword, newPassword) {
     return axiosInstance.post('/auth/change_password', { currentPassword, newPassword });
   }
   ```

2. **Create** Zod schema in `src/schemas/auth.ts`:
   ```typescript
   export const changePasswordSchema = z.object({
     current_password: z.string().min(1, 'Required'),
     new_password: z.string().min(8, 'Min 8 characters'),
     confirm_password: z.string(),
   }).refine(data => data.new_password === data.confirm_password, {
     message: 'Passwords do not match', path: ['confirm_password'],
   });
   ```

3. **Add UI** in settings page or profile page (not in auth flow).

---

## 20. File Index

### Pages

| File | Size | Lines | Purpose |
|------|------|-------|---------|
| `src/app/auth/login/page.tsx` | ~0.2KB | ~8 | Suspense wrapper |
| `src/app/auth/login/LoginPage.tsx` | ~3.3KB | ~95 | Login form |
| `src/app/auth/signup/page.tsx` | ~0.2KB | ~8 | Suspense wrapper |
| `src/app/auth/signup/SignupClient.tsx` | ~5.6KB | ~160 | Signup form + org check |
| `src/app/auth/forgotpassword/page.tsx` | ~2.5KB | ~70 | Forgot password form |
| `src/app/auth/reset-password/page.tsx` | ~2.7KB | ~85 | Reset password form |
| `src/app/auth/check-email/page.tsx` | ~1.6KB | ~45 | Email confirmation (static) |
| `src/app/auth/verify_signup/page.tsx` | ~2.2KB | ~65 | Email verification handler |

### Shared Auth Components

| File | Size | Purpose |
|------|------|---------|
| `src/app/auth/shared/ContainerComponent.tsx` | ~6.9KB | Auth page layout with branding |

### Services

| File | Size | Purpose |
|------|------|---------|
| `src/services/auth/helper.tsx` | ~2.4KB | Auth API calls + cookie management |

### State & Validation

| File | Size | Purpose |
|------|------|---------|
| `src/atoms/AuthAtom.tsx` | ~2.5KB | Auth state atoms (auth, logout, getCurrentUser) |
| `src/schemas/auth.ts` | ~1.3KB | 4 Zod schemas + inferred types |

### Shared UI Components

| File | Size | Purpose |
|------|------|---------|
| `src/components/shared/TextInput.tsx` | ~4KB | Text/password input with RHF integration |
| `src/components/shared/CustomButton.tsx` | ~3KB | Button with loading/variant/icon support |
| `src/components/shared/CustomLink.tsx` | ~1KB | Next.js Link wrapper |
| `src/components/shared/CheckboxField.tsx` | ~2KB | Checkbox with RHF integration |
| `src/components/shared/Logo.tsx` | ~2KB | SVG logo with gradient |
| `src/components/shared/ThemeToggle.tsx` | ~1.5KB | Light/dark theme switcher |

### Utilities & Config

| File | Size | Purpose |
|------|------|---------|
| `src/middleware.ts` | ~1.2KB | Route protection (public paths + token check) |
| `src/utils/axios.ts` | ~0.7KB | Axios instance with auth interceptors |
| `src/utils/jwt.tsx` | ~0.3KB | JWT payload decoder |
| `src/utils/helpers.ts` | ~0.7KB | `handleApiError` + `generateUUID` |
| `src/utils/toast.tsx` | ~0.5KB | Sonner toast wrapper with duration conversion |
| `src/constants/index.ts` | ~0.4KB | Cookie keys + API URL constants |

### Total Source Size

~34KB across 15 core files + ~13KB in shared UI components = **~47KB total**

---

*Generated by Claude Code — ~47KB source documented in ~30KB doc. For most auth bugs and features, read this doc + edit one file.*
