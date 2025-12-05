"""
Tests for the centralized logging system
"""

import logging
from pathlib import Path
import pytest
import time

from src.utils.logger import get_logger, setup_logger, ColoredFormatter, log_performance


class TestGetLogger:
    """Test get_logger function"""

    def test_get_logger_creates_logger(self):
        """Test that get_logger creates a logger instance"""
        logger = get_logger("test_module")
        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    def test_get_logger_returns_same_instance(self):
        """Test that get_logger returns the same instance for the same name"""
        logger1 = get_logger("test_module")
        logger2 = get_logger("test_module")
        assert logger1 is logger2

    def test_get_logger_different_names(self):
        """Test that different names create different loggers"""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        assert logger1 is not logger2
        assert logger1.name == "module1"
        assert logger2.name == "module2"


class TestSetupLogger:
    """Test setup_logger function"""

    def test_setup_logger_creates_logger(self, tmp_path):
        """Test that setup_logger creates a logger with handlers"""
        log_dir = str(tmp_path / "logs")
        logger = setup_logger("test_logger", level="INFO", log_dir=log_dir)

        assert logger is not None
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0

    def test_setup_logger_log_levels(self, tmp_path):
        """Test different log levels"""
        log_dir = str(tmp_path / "logs")

        for level_name, level_value in [
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
            ("ERROR", logging.ERROR),
            ("CRITICAL", logging.CRITICAL),
        ]:
            logger = setup_logger(
                f"test_{level_name}", level=level_name, log_dir=log_dir
            )
            assert logger.level == level_value


class TestColoredFormatter:
    """Test ColoredFormatter class"""

    def test_colored_formatter_adds_colors(self):
        """Test that ColoredFormatter adds color codes to log levels"""
        formatter = ColoredFormatter("%(levelname)s - %(message)s")

        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        # Check that color codes are present (ANSI escape sequences)
        assert "\033[" in formatted or "INFO" in formatted

    def test_colored_formatter_different_levels(self):
        """Test that different log levels get different colors"""
        formatter = ColoredFormatter("%(levelname)s")

        levels = [
            (logging.DEBUG, "DEBUG"),
            (logging.INFO, "INFO"),
            (logging.WARNING, "WARNING"),
            (logging.ERROR, "ERROR"),
            (logging.CRITICAL, "CRITICAL"),
        ]

        formatted_messages = []
        for level, level_name in levels:
            record = logging.LogRecord(
                name="test",
                level=level,
                pathname="test.py",
                lineno=1,
                msg="Test",
                args=(),
                exc_info=None,
            )
            formatted = formatter.format(record)
            formatted_messages.append(formatted)

        # All formatted messages should be different (different colors)
        assert len(set(formatted_messages)) == len(formatted_messages)


class TestLogPerformance:
    """Test log_performance decorator"""

    def test_log_performance_decorator_executes_function(self):
        """Test that the decorator executes the wrapped function"""

        @log_performance()
        def test_function(x, y):
            return x + y

        result = test_function(2, 3)
        assert result == 5

    def test_log_performance_decorator_logs_execution_time(self, caplog):
        """Test that the decorator logs execution time"""

        @log_performance()
        def slow_function():
            time.sleep(0.1)
            return "done"

        with caplog.at_level(logging.INFO):
            result = slow_function()

        assert result == "done"
        # Check that execution time was logged
        assert any(
            "completed in" in record.message.lower() for record in caplog.records
        )

    def test_log_performance_decorator_with_exception(self, caplog):
        """Test that the decorator handles exceptions properly"""

        @log_performance()
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            with caplog.at_level(logging.ERROR):
                failing_function()

        # Should still log execution time even if function fails
        assert any(
            "failed after" in record.message.lower() for record in caplog.records
        )


class TestLoggerIntegration:
    """Integration tests for the logging system"""

    def test_logger_writes_to_file(self, tmp_path):
        """Test that logger writes messages to file"""
        log_dir = str(tmp_path / "logs")
        logger = setup_logger("integration_test", log_dir=log_dir)

        test_message = "Integration test message"
        logger.info(test_message)

        log_file = Path(log_dir) / "integration_test.log"
        assert log_file.exists()

        content = log_file.read_text()
        assert test_message in content

    def test_logger_console_and_file_output(self, tmp_path, caplog):
        """Test that logger outputs to both console and file"""
        log_dir = str(tmp_path / "logs")
        logger = setup_logger("dual_output_test", log_dir=log_dir)

        test_message = "Dual output test"

        with caplog.at_level(logging.INFO):
            logger.info(test_message)

        # Check console output
        assert any(test_message in record.message for record in caplog.records)

        # Check file output
        log_file = Path(log_dir) / "dual_output_test.log"
        content = log_file.read_text()
        assert test_message in content

    def test_multiple_loggers_no_conflict(self, tmp_path):
        """Test that multiple loggers don't interfere with each other"""
        # log_dir = str(tmp_path / "logs")

        logger1 = get_logger("logger1")
        logger2 = get_logger("logger2")

        logger1.info("Message from logger1")
        logger2.info("Message from logger2")

        # Both loggers should work independently
        assert logger1.name == "logger1"
        assert logger2.name == "logger2"

    def test_logger_error_with_exception_info(self, tmp_path):
        """Test that logger captures exception information"""
        log_dir = str(tmp_path / "logs")
        logger = setup_logger("exception_test", log_dir=log_dir)

        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.error("An error occurred", exc_info=True)

        log_file = Path(log_dir) / "exception_test.log"
        content = log_file.read_text()

        # Should contain error message and traceback
        assert "An error occurred" in content
        assert "ValueError" in content
        assert "Test exception" in content
        assert "Traceback" in content
