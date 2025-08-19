# Releasing Guidelines

This project uses a GitHub Actions workflow to **validate, deploy to PyPI, tag releases**, and **publish GitHub releases** when changes are pushed to the `main` branch.

## Workflow Trigger

The workflow runs **only on pushes to the `main` branch**.

---

## Requirements for Deployment

To successfully trigger a deployment and tagging operation, the following conditions must be met:

### 1. Version bump in `pyproject.toml`

* The version defined in `pyproject.toml` (via `poetry version`) must follow [semantic versioning](https://semver.org/) (e.g., `1.2.3`).
* The version must be **different from the previous commit** (`git show ${GITHUB_SHA}^:pyproject.toml`).

### 2. `CHANGELOG.md` Entry

* A matching version entry (`vX.Y.Z`) must exist in `CHANGELOG.md`.
* Example required entry format:

```md
## [v1.0.0] - 2025-05-07

### Added
- Support for automatic tagging after PyPI deployment.
- Semantic version validation in the deployment workflow.

### Changed
- Updated CI to use Python 3.12.
- Switched to `poetry install --no-root`.

### Fixed
- Issue where tags were pushed before successful PyPI publish.

### Removed
- Legacy support for Python 3.7 and 3.8.

### Deprecated
- Old environment setup script using `requirements.txt`.

### Security
- Improved handling of PyPI tokens in workflow.
```

### 3. Tag does not already exist

* The Git tag `vX.Y.Z` must **not already exist** in the repository.

---

## Release Workflow

To ensure a smooth release process, follow these steps:

1. **Prepare Changes**:
   - Add all the necessary changes for the release to the `main` branch via pull requests.

2. **Create a Release Branch**:
   - Once the `main` branch contains all the changes for the release, create a release branch named `release/vX.Y.Z` (e.g., `release/v1.0.0`).

3. **Version Bump**:
   - Use `poetry version patch|minor|major` to bump the version in `pyproject.toml`.

4. **Update the Changelog**:
   - Add an entry for the new version (`vX.Y.Z`) to `CHANGELOG.md` following the required format.

5. **Open a Pull Request**:
   - Open a pull request from the release branch (`release/vX.Y.Z`) to `main`.

6. **Merge the Pull Request**:
   - Once the pull request is reviewed and approved, merge it into `main`.

7. **Trigger the Workflow**:
   - The GitHub Actions workflow will automatically validate the release, deploy it to PyPI, tag the commit, extract release notes, and publish the GitHub release.

### Explanation of Each Step

- **Prepare Changes**:  
  Ensures that all necessary updates (features, fixes, etc.) are merged into `main` before starting the release process.

- **Create a Release Branch**:  
  Isolates the release process from ongoing development, ensuring a clean and focused release.

- **Version Bump**:  
  Updates the version in `pyproject.toml` using poetry, following semantic versioning.

- **Update the Changelog**:  
  Documents the changes introduced in the release, ensuring transparency and proper version tracking.

- **Open a Pull Request**:  
  Allows for review and validation of the release branch before merging into `main`.

- **Merge the Pull Request**:  
  Combines the release branch into `main`, triggering the workflow.

- **Trigger the Workflow**:  
  Automates the deployment, tagging, release notes extraction, and GitHub Release creation process.

---

## Required Secrets

To publish to PyPI and create a GitHub release, the workflow uses the following secrets:

| Secret Name      | Description                   |
| ---------------- | ----------------------------- |
| `PYPI_API_TOKEN` | PyPI API token for publishing |
| `GITHUB_TOKEN`   | GitHub token (automatically provided) |

---

## What the Workflow Does

If the above conditions are met, the workflow will:

1. **Install dependencies using Poetry**
2. **Validate the version format**
3. **Check if the version was bumped**
4. **Ensure the version exists in `CHANGELOG.md`**
5. **Build the package**
6. **Publish it to PyPI**
7. **Tag the commit with `vX.Y.Z` and push the tag**
8. **Extract release notes for `vX.Y.Z` from `CHANGELOG.md`**
9. **Create a GitHub Release with the extracted notes**

---

## What Causes the Workflow to Skip Deployment

* No version bump was detected.
* The version format is invalid.
* The tag already exists.
* `CHANGELOG.md` does not contain a matching version entry.

---

## Best Practices

* Use `poetry version patch|minor|major` to update the version.
* Always update `CHANGELOG.md` with the new version before merging.
* Push only one release-related change per commit to avoid ambiguity.
* Use a release branch with the naming convention `release/vX.Y.Z` to isolate and manage the release process clearly and consistently.