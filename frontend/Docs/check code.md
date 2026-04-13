**Backend (Python) — checks you already use:**

```bash
# Type checking
mypy .

# Linting
ruff check .

# Auto-fix linting issues
ruff check . --fix

# Formatting check
black --check .

# Auto-format
black .

# Run all at once
ruff check . --fix && black . && mypy .
```

**Additional backend checks worth adding:**

```bash
# Security vulnerabilities in dependencies
pip install bandit
bandit -r app/

# Dependency vulnerability scan
pip install safety
safety check

# Import sorting
ruff check . --select I --fix

# Dead code detection
#pip install vulture
#vulture app/

# Test coverage
pytest --cov=app --cov-report=term-missing
```

---

**Frontend (TypeScript/Next.js) — checks available:**

```bash
# Type checking
pnpm tsc --noEmit

# Linting
pnpm eslint . 

# Auto-fix lint
pnpm eslint . --fix

# Formatting check
pnpm prettier --check .

# Auto-format
pnpm prettier --write .

# Run all at once
pnpm tsc --noEmit && pnpm eslint . && pnpm prettier --check .

python3 -m pip install --user --break-system-packages pytest-xdist pytest-cov && pytest -n 12 --cov=app --cov-report=term-missing
```

**Additional frontend checks worth adding:**

```bash
# Unused dependencies
npx depcheck

# Bundle size analysis
pnpm build && npx @next/bundle-analyzer

# Accessibility audit
npx axe-cli http://localhost:1030

# Dead code / unused exports
npx ts-prune
```

---

**Best practice — add a single script to run everything:**

In `package.json` add:
```json
"scripts": {
  "check": "tsc --noEmit && eslint . && prettier --check ."
}
```

In `pyproject.toml` add:
```toml
[tool.taskipy.tasks]
check = "ruff check . && black --check . && mypy ."
```

Then just run `pnpm check` or `task check` before every Docker build to catch all issues before deployment.








 docker compose -f backend/docker-compose.yml build frontend && docker compose -f backend/docker-compose.yml up -d frontend