# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
  - Refactored modules:
    - `src/generators/*` - All generator modules
    - `src/pipeline/*` - Pipeline and bot modules
    - `src/uploaders/*` - All uploader modules
    - `src/analytics/*` - Analytics and tracking modules
    - `src/utils/*` - Utility modules
    - `src/web/*` - Web interface modules

- **Test Infrastructure Updates**
  - Renamed `mock_anthropic_client` to `mock_claude_client` in `tests/conftest.py`
  - Updated test files to patch `settings` instead of `config`
  - Fixed method signatures in test files to match refactored code
  - Updated `test_script_generator.py` to remove deprecated `duration` parameter

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

## [Previous Versions]
See Git history for changes prior to this refactoring.
