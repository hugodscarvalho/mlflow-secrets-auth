# CHANGELOG

All notable changes to the `mlflow-secrets-auth` package will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/) and follows changelog conventions inspired by [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [v0.2.0] – 2025-08-20

### Added
- Centralized **constants** (`constants.py`) and **messages** (`messages.py`) for configuration, errors, and CLI output.  
- **Docker Compose demo** with MLflow + Nginx + Vault for end-to-end testing.  

### Changed
- Refactored all `src/` modules to remove hardcoded strings in favor of centralized constants/messages.  
- Improved CLI output consistency with headers, emojis, and standardized diagnostics.  

## [v0.1.0] – 2025-08-19

### Added

- **Initial placeholder release** of `mlflow-secrets-auth` on PyPI.
- Included a minimal `MLflowClient` wrapper module.

### Notes

- This version was intentionally published with limited functionality to reserve the `mlflow-secrets-auth` package name on [PyPI](https://pypi.org/project/mlflow-secrets-auth/).