# FAIM UI Documentation

Welcome to the official documentation for the **FAIM (Fractal AI Memory)** User Interface.

## Navigation

| Document                                          | Description                                   |
| ------------------------------------------------- | --------------------------------------------- |
| [Architecture](./UI_ARCHITECTURE.md)              | High-level system design and frontend stack.  |
| [Security Hardening](./SECURITY_DOCS.md)          | Details on the 10/10 security implementation. |
| [Component Guide](./COMPONENT_GUIDE.md)           | Key UI components and how to use them.        |
| [Development Workflow](./DEVELOPMENT_WORKFLOW.md) | commands, build process, and testing scripts. |

## Quick Start

1.  **Run Dev Server**: `npm run dev` in `frontend/`
2.  **Access Dashboard**: `http://localhost:3000/dashboard`
3.  **Authentication**: OTP-based login (passwordless).

## Philosophy

The FAIM UI is designed to provide **Visual Proof of Isolation**. Every pixel on the dashboard is hard-scoped to the authenticated user's `tenant_id`, ensuring a private and secure workspace for AI memory evolution.
