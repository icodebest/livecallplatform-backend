import logging


def setup_logging() -> None:
    """Configure a simple readable log format for local and server output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


logger = logging.getLogger("maya-health-voice")
