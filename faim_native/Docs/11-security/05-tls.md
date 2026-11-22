# TLS deployment guidance

Expose FAIM through a reverse proxy or ingress that terminates HTTPS. Keep the
API bound to a private network or localhost where the deployment topology
allows it.

## Minimum edge controls

- Valid certificate chain and automated renewal.
- TLS 1.2 or newer, with modern cipher configuration.
- HSTS only after HTTPS is confirmed for every intended host.
- Explicit security headers and an origin allowlist.
- No plaintext API keys in URLs or proxy logs.
- Correct forwarding of WebSocket/SSE connections when those routes are used.

The repository root Compose file does not itself provision a public
certificate or a domain. TLS readiness must therefore be verified in the
chosen deployment environment rather than claimed from local Compose startup.
