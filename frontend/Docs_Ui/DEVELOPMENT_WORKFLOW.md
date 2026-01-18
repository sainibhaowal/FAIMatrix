# Development Workflow

This document outlines the standard procedures for developing, building, and testing the FAIM UI.

## Environment Setup

### Required Env Vars (.env.local)

```bash
NEXT_PUBLIC_FAIM_API_BASE_URL=http://localhost:8000
NEXTAUTH_SECRET=your-random-signing-secret
RE_KEY=your-resend-api-key
```

## Available Commands

### Development

Starts the dev server with Hot Module Replacement (HMR).

```bash
npm run dev
```

### Production Build

Generates an optimized production bundle.

```bash
npm run build
```

### Type Checking

Runs TypeScript validation across the entire project.

```bash
npm run typecheck
```

### Testing (Playwright)

Runs end-to-end user flow tests.

```bash
npx playwright test
```

## Code Standards

- **Component Pattern**: Function-based components with custom hooks for logic separation.
- **Styling**: All local styling must use design tokens from `lib/tokens.ts` (e.g., `var(--color-cyan-500)`).
- **Hardened Auth**: Never log sensitive data or return plain-text OTPs in API responses.

## Security Controls

For all new backend integrations:

1.  **Always** hard-scope queries by `tenant_id`.
2.  **Implicit filtering**: The backend `get_tenant_id` dependency is mandatory for all non-public routes.
3.  **Audit**: Any change to `lib/auth.ts` or `api/routers/auth.py` requires a security audit (10/10 rating maintained).
