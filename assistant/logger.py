import functools
import logging
from typing import Any, Callable, Optional, Type
import time
from datetime import datetime
from pathlib import Path
def get_assistant_logger(
    name: str = "assistant_logger",
    level: int = logging.INFO,
    fmt: str = "%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt: str = "%Y-%m-%d %H:%M:%S",
    handler: Optional[logging.Handler] = None,
    log_dir: str = "logs"
) -> logging.Logger:
    """
    Creates (or returns, if already existing) a logger named 'assistant_logger'.
    Also writes all INFO and DEBUG messages to a timestamped log file.

    :param name:    Name of the logger (default: "assistant_logger")
    :param level:   Logging level for console (default: INFO)
    :param fmt:     Format string for log messages
    :param datefmt: Date format for log timestamps
    :param handler: Optional custom console handler.
                    If None, a StreamHandler with the default formatter is created.
    :param log_dir: Directory where the log file will be created (default: current directory)
    :return:        Configured Logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # capture everything DEBUG and above

    if not logger.handlers:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        # 1) Console handler at specified level
        console_handler = handler or logging.StreamHandler()
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # 2) File handler capturing INFO and DEBUG with timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        logfile = f"{log_dir}/assistant_{timestamp}.log"
        file_handler = logging.FileHandler(logfile)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Prevent log messages from being propagated to the root logger
        logger.propagate = False

    return logger
def log_execution(
    level_success: int = logging.INFO,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator that wraps every function in a try/except block.
    
    - On successful execution, logs at `level_success`.
    - On exception, logs at `level_error` and re-raises the exception.
    
    :param level_success: Logging level for successful execution (default: INFO)
    :param level_error:   Logging level for exceptions (default: ERROR)
    :param logger:        Optional logger instance. If None, uses a logger named after the function’s module.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        log = get_assistant_logger() if logger is None else logger

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                _start = time.time()
                result = func(*args, **kwargs)
                log.log(
                    level_success,
                    "Function '%s' executed successfully. duration=%.2fms",
                    func.__name__,  (time.time() - _start) * 1000
                )
                return result
            except Exception as e:
                log.error("Function '%s' failed: %s",
                          func.__name__, e.__class__.__name__, exc_info=True)
                # Exception is re-raised to allow callers to handle it
                raise

        return wrapper

    return decorator
