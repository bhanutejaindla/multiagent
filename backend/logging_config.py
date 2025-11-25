import logging
import sys
import structlog

def configure_logging():
    """
    Configures structured logging for the application.
    """
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if sys.stderr.isatty():
        # Pretty printing for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(),
        ]
    else:
        # JSON output for production/observability
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Redirect standard logging to structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    
    # Intercept standard library logging
    def _structlog_handler(logger, name, event_dict):
        return event_dict

    # This is a simplified setup; for full stdlib redirection, 
    # one might use structlog.stdlib.LoggerFactory and structlog.stdlib.ProcessorFormatter
    # But for this agent, we'll primarily use structlog directly where possible
    # and let uvicorn handle its own logs, or configure uvicorn to use structlog if needed.
    # For now, we just ensure our app logs are structured.

logger = structlog.get_logger()
