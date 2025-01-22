import logging
from logging.handlers import RotatingFileHandler
from threading import Lock


class Logger:
    """
    A Singleton Logger class to manage logging across the application.
    """

    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        """
        Create or return the singleton instance.
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Logger, cls).__new__(cls)
                cls._instance._initialize(*args, **kwargs)
        return cls._instance

    def _initialize(self, log_file="app.log", log_level=logging.INFO):
        """
        Initialize the logger with the desired configuration.

        Args:
            log_file (str): Path to the log file.
            log_level (int): Logging level (e.g., logging.INFO, logging.DEBUG).
        """
        self.logger = logging.getLogger("ApplicationLogger")
        if not self.logger.hasHandlers():  # Prevent duplicate handlers
            self.logger.setLevel(log_level)

            # Create a formatter
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
            )

            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

            # File handler with rotation
            file_handler = RotatingFileHandler(
                log_file, maxBytes=5 * 1024 * 1024, backupCount=3
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    @classmethod
    def get_instance(cls, log_file="app.log", log_level=logging.INFO):
        """
        Get the singleton Logger instance.

        Args:
            log_file (str): Path to the log file.
            log_level (int): Logging level (e.g., logging.INFO, logging.DEBUG).

        Returns:
            Logger: The singleton Logger instance.
        """
        if cls._instance is None:
            cls._instance = cls(log_file=log_file, log_level=log_level)
        return cls._instance

    def get_logger(self):
        """
        Get the logger object.

        Returns:
            logging.Logger: The logger instance.
        """
        return self.logger

    def log_health(self):
        """
        Log basic health information for the application.
        """
        self.logger.info("Logger is operational and healthy.")
