# FAIM Future Work

This document tracks planned features for future implementation.

---

## 🔴 Critical (Must Have for Production)

| Feature                   | Description                                                       | Status          |
| ------------------------- | ----------------------------------------------------------------- | --------------- |
| Stripe Integration        | Real checkout & subscription management                           | ❌ Not wired    |
| Webhook Handler           | Handle Stripe events (payment success/fail, subscription changes) | ❌ Missing      |
| Plan Enforcement          | Actually limit features/tokens based on plan                      | ❌ Not enforced |
| Invoice History           | Show past invoices/receipts                                       | ❌ Missing      |
| Payment Method Management | Add/update cards                                                  | ❌ Missing      |

---

## 🟡 Important (Should Have)

| Feature                  | Description                        |
| ------------------------ | ---------------------------------- |
| Real-time Usage Tracking | Show actual token/storage usage    |
| Usage Alerts             | Email when near limit (80%, 100%)  |
| Upgrade/Downgrade Logic  | Proration, immediate vs next cycle |
| Refund Policy Display    | Clear cancellation terms           |
| Trial Period             | 7/14 day free trial for paid plans |

---

## 🟢 Nice to Have

| Feature            | Description                      |
| ------------------ | -------------------------------- |
| Annual Plans       | Discount for yearly payment      |
| Team Plans         | Multi-user pricing               |
| Usage Charts       | Visual graphs of usage over time |
| Export Invoices    | PDF download                     |
| Coupon/Promo Codes | Discount codes                   |

---

My recommendation for immediate implementation:

✅ Stripe Checkout Integration - Real payments
✅ Webhook Handler - Handle subscription lifecycle
✅ Usage Tracking - Show actual token usage
✅ Plan Enforcement - Block actions when ove

## 🔸 Profile Enhancements

| Feature                  | Description                           |
| ------------------------ | ------------------------------------- |
| Two-Factor Auth (2FA)    | TOTP setup with QR code               |
| Session Management       | View/revoke active sessions           |
| Export My Data           | GDPR-compliant data export (JSON/ZIP) |
| Notification Preferences | Email notifications on/off            |
| Theme Preference         | Dark/Light mode toggle                |
