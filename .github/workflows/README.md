# GitHub Actions Workflows

This directory contains CI/CD workflows for the Vietnamese Environmental Law RAG project.

## Workflows

### `ci.yml` - Continuous Integration
Runs on every push and pull request to ensure code quality.

**Jobs:**
- **backend-lint**: Checks Python code formatting (Black), import sorting (isort), and linting (flake8)
- **backend-test**: Runs backend tests with PostgreSQL and Redis services, generates coverage reports
- **frontend-lint**: Checks TypeScript/React code with ESLint and type checking
- **frontend-build**: Builds frontend production bundle
- **docker-build**: Tests Docker image builds for both backend and frontend

**Triggers:**
- Push to `main` or `phase-*` branches
- Pull requests targeting `main`

### `auto-pr.yml` - Automatic Pull Request Creation
Automatically creates pull requests when pushing to feature branches.

**Jobs:**
- **create-pr**: Creates a new PR or comments on existing PR with latest commit info

**Triggers:**
- Push to `phase-*`, `feature/*`, or `fix/*` branches

**Features:**
- Auto-generates PR title from branch name
- Uses latest commit message as PR description
- Adds checklist template
- Comments on existing PRs with new commit info

## Setup Required

1. **GitHub Permissions**: Ensure the repository has Actions enabled with read/write permissions for:
   - Contents
   - Pull requests
   - Issues

2. **Branch Protection** (recommended for `main`):
   - Require PR before merging
   - Require status checks to pass (ci.yml jobs)
   - Require code review

3. **Secrets** (optional):
   - `CODECOV_TOKEN`: For uploading coverage reports (if using Codecov)

## Usage

### Creating a Feature Branch
```bash
# Create and switch to new feature branch
git checkout -b phase-6-testing

# Make changes and commit
git add .
git commit -m "feat: Add comprehensive testing suite"

# Push branch (will trigger auto-pr.yml)
git push origin phase-6-testing
```

A pull request will be automatically created!

### Viewing CI Results
1. Go to the "Actions" tab in GitHub
2. Click on the workflow run
3. Review job results and logs

### Merging PRs
Once CI passes and the PR is reviewed:
```bash
# Option 1: Merge via GitHub UI (recommended)
# - Click "Squash and merge" or "Merge pull request"

# Option 2: Merge locally
git checkout main
git merge --no-ff phase-6-testing
git push origin main
```

## Local Development

Run linting and tests locally before pushing:

```bash
# Backend
cd backend
black . && isort . && flake8 app/
pytest tests/ -v

# Frontend
cd frontend
npm run lint
npm run build
```

## Troubleshooting

**CI failing on backend-lint?**
- Run `black .` and `isort .` in backend directory
- Fix any flake8 warnings

**CI failing on frontend-build?**
- Check TypeScript errors: `npx tsc --noEmit`
- Ensure all dependencies are in package.json

**PR not created automatically?**
- Check Actions tab for workflow errors
- Ensure repository has PR creation permissions
- Verify branch name matches trigger patterns

## Future Improvements

- [ ] Add E2E tests with Playwright
- [ ] Deploy preview environments for PRs
- [ ] Automated security scanning
- [ ] Performance benchmarking
- [ ] Automated dependency updates (Dependabot)
