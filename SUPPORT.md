# Support

Start with the [README](README.md), [API documentation](faim_native/Docs/02-api/01-api-documentation.md), [architecture overview](faim_native/Docs/01-architecture/01-end-to-end-architecture.md), and [operations documentation](faim_native/Docs/10-operations/01-deployment.md).

## Before opening an issue

1. Search existing issues and the documentation index.
2. Confirm the behavior on the current branch or release.
3. Reproduce it with synthetic data and the smallest possible configuration.
4. Remove secrets, access tokens, personal data, raw documents, and tenant identifiers from logs.
5. Include the command, endpoint, expected result, actual result, environment, and relevant commit.

## Issue types

- **Bug:** include a minimal reproduction and logs with sensitive data removed.
- **Feature:** explain the use case, affected layer, contract, and operational trade-offs.
- **Documentation:** link to the unclear or incorrect section and propose a correction.
- **Performance:** include dataset shape, profile, hardware, dependencies, baseline, and measurement method.
- **Security:** follow [`SECURITY.md`](SECURITY.md); do not publish exploit details.

Community support is provided on a best-effort basis via [GitHub Issues](https://github.com/sainibhaowal/FAIMatrix/issues). When reporting behavior across environments, include exact release versions or commit SHAs, Compose profiles, and sanitized logs so results can be reproduced consistently. For additional architecture and operations guides, see the [canonical documentation index](faim_native/Docs/00-readme.md).
