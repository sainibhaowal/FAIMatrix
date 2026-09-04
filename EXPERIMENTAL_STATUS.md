# Experimental status and safe use

FAIM-Native is a research and engineering prototype under substantial active development. It is a serious end-to-end implementation, but it is not a stable product or a promise of production readiness.

## Who should use it

The current audience is:

- developers evaluating memory-system architectures in isolated environments;
- researchers investigating provenance, graph evolution, retrieval, and agent memory;
- systems engineers reviewing the implementation and proposing improvements; and
- collaborators who can validate behavior against a pinned checkout and representative test data.

## Who should not use it yet

Do not use FAIM-Native as the sole system of record for:

- personal knowledge, productivity, or irreplaceable files;
- production or business-critical workloads;
- safety-critical, regulated, privacy-sensitive, or compliance-bound workflows; or
- data whose loss, corruption, disclosure, or incorrect retrieval would cause material harm.

The repository may be run for evaluation, but evaluation is not an endorsement that a deployment is safe for a particular use case.

## What “under development” means

The following can change between commits or releases:

- API, storage, migration, event, and graph contracts;
- retrieval and scoring behavior, native representations, and provider adapters;
- ingestion, OCR, multimodal extraction, background jobs, and evolution policies;
- authentication, deployment defaults, observability, and operational procedures; and
- frontend workflows, documentation, benchmarks, and supported environments.

Implemented does not mean stable. Tested does not mean production-ready. A benchmark result is meaningful only with its dataset, configuration, baseline, hardware, and failure cases; it is not a universal comparison claim.

## Safe evaluation procedure

Before evaluating a checkout:

1. Pin the exact commit and record the runtime, dependency, container, and configuration versions.
2. Use synthetic, redacted, or safely backed-up data in an isolated environment.
3. Read the security, deployment, backup/restore, and benchmark documentation for the feature under review.
4. Run readiness checks, relevant tests, and backup/restore exercises before loading meaningful data.
5. Observe logs, worker queues, database migrations, storage growth, and tenant boundaries during the test.
6. Treat results as experimental evidence and record configuration, limitations, and failed cases.

## Stability gates

A future stable release should not be inferred from a passing test suite alone. The project needs, at minimum, reproducible benchmarks, versioned API and storage contracts, migration and rollback procedures, tested backup/restore, dependency and container security review, documented performance limits, supported deployment guidance, and a maintained incident/reporting process.

## Reporting problems

Report security-sensitive issues privately using [`SECURITY.md`](SECURITY.md). For reproducible bugs, incomplete features, and research questions, include the commit, environment, configuration class, reproduction steps, expected behavior, observed behavior, and relevant logs without submitting secrets or private user data. See [`SUPPORT.md`](SUPPORT.md).
