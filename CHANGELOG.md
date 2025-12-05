# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **CI/CD Pipeline** (`.github/workflows/ci.yml`)
  - Automated testing with `pytest` on every push/PR
  - Static type checking with `mypy`
  - Code linting and formatting detailed with `ruff` and `black`
  - Code coverage measurement
- 전체 코드 베이스 린트 에러 해결 (`F841`, `E402`, `E722` 등)
- **Code Quality Tools**
  - Added `black` and `ruff` to project dependencies
  - Applied consistent formatting across the entire codebase

### Fixed
- **Test Suite Complete Success**
  - Fixed `test_image_generator.py` mocking issues
  - Fixed `test_trend_collector.py` configuration patching
  - Achieved 100% test pass rate (133/133 tests)

### Added
- **Type Hinting System** (15+ files)
  - Comprehensive Python type hints (PEP 484) across all major modules
  - `mypy>=1.0.0` for static type checking
  - Type stubs: `types-requests>=2.31.0`, `types-python-dateutil>=2.8.0`
  - Lenient `mypy.ini` configuration for gradual typing
  - Type annotations in `src/utils`, `src/generators`, `src/analytics`, `src/uploaders`, `src/web`
  - **87% reduction** in mypy errors (291 → 38 errors)

- **Pydantic BaseSettings Configuration System** (`src/core/config.py`)
  - Type-safe configuration management using Pydantic v2
  - Automatic environment variable loading from `.env` file
  - Field validation for all configuration values
  - Singleton `settings` instance for global access
  - Custom validator for `DEFAULT_TAGS` supporting both JSON arrays and CSV strings

### Changed
- **Configuration Management Refactoring** (40+ files)
  - Migrated all modules from `import config` to `from src.core.config import settings`
  - Updated all configuration access patterns across the codebase
  - Refactored modules: `src/generators/*`, `src/pipeline/*`, `src/uploaders/*`, `src/analytics/*`, `src/utils/*`, `src/web/*`

- **Test Infrastructure Updates**
  - Renamed `mock_anthropic_client` to `mock_claude_client` in `tests/conftest.py`
  - Updated test files to patch `settings` instead of `config`
  - Fixed method signatures in test files to match refactored code
  - Updated `test_script_generator.py` to remove deprecated `duration` parameter

- **VideoCompositor Refactoring**
  - Created `VideoEditor` class for video composition and editing (285 lines)
  - Simplified `VideoCompositor` from 970 lines to 159 lines (84% reduction)
  - Modularized into `SubtitleRenderer`, `BackgroundVideoManager`, `VideoEditor`

### Fixed
- **Type Safety Improvements**
  - Added proper type hints to configuration fields
  - Fixed `DEFAULT_TAGS` parsing to handle multiple input formats
  - Improved error handling for configuration validation

- **Test Compatibility**
  - Fixed ScriptGenerator tests (4/10 now passing)
  - Fixed social upload tests
  - Fixed multi-platform uploader tests
  - Overall test improvement: 90 → 98 passing tests

### Technical Details
- **Backward Compatibility**: Old `config.py` temporarily retained for gradual migration
- **Validation**: All configuration values now validated at startup
- **Environment Variables**: Comprehensive `.env` support with type conversion
- **Performance**: No performance impact; configuration loaded once at startup

### Testing
- ✅ Test video generation successful (97.90 seconds)
- ✅ All refactored modules verified in production
- ✅ OpenAI API integration working
- ✅ Google Cloud TTS integration working
- ✅ Pexels API integration working
- ✅ DALL-E 3 thumbnail generation working

## [0.1.0] - 2025-12-03

### Added
- Initial release of YouTube Shorts automation bot
- AI-powered script generation (OpenAI GPT, Claude)
- Text-to-Speech integration (OpenAI TTS, Google Cloud TTS)
- Background video/image integration (Pexels, Unsplash, Pixabay)
- Automated YouTube upload with OAuth 2.0
- Subtitle rendering and synchronization
- Thumbnail generation with DALL-E 3
- Analytics and monetization tracking
- Web dashboard for statistics and monitoring
- Notification system (Email, Slack)
- Scheduled daily uploads
- Multi-language support (English, Korean)

### Changed
- N/A (initial release)

### Fixed
- N/A (initial release)

---

## Version History Summary

- **[Unreleased]**: Type hinting, Pydantic configuration, code refactoring
- **[0.1.0]**: Initial release with core automation features

For detailed development history, see [HISTORY.md](./HISTORY.md).
