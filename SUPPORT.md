# Support

Start with the [README](README.md), [API documentation](<docs/2) BackEnd/API_Reference/FAIM_API_DOCUMENTATION.md>), [architecture overview](docs/architecture_overview.md), and [operations documentation](docs/Operations/deployment.md).

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

FAIM-Native is experimental. Community support is best-effort, and a passing historical report does not guarantee that the current checkout or a different deployment has the same behavior.
