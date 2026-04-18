import pika
from django.conf import settings
import threading
import logging
import atexit

logger = logging.getLogger(__name__)


class RabbitMQConnection:
    """Singleton wrapper for a persistent RabbitMQ connection."""

    _instance = None
    _lock = threading.Lock()
    _connection = None

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def get_connection(self):
        """Get or create the singleton connection."""
        with self._lock:
            if self._connection is None or self._connection.is_closed:
                try:
                    self._connection = self._create_connection()
                    logger.info("RabbitMQ connection established")
                except Exception as e:
                    logger.error(
                        "Failed to establish RabbitMQ connection",
                        extra={
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                        },
                    )
                    raise
            return self._connection

    def _create_connection(self):
        """Create a new BlockingConnection with configured parameters."""
        creds = pika.PlainCredentials(
            settings.RABBITMQ_USER,
            settings.RABBITMQ_PASSWORD,
        )
        return pika.BlockingConnection(
            pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                virtual_host=settings.RABBITMQ_VHOST,
                credentials=creds,
                socket_timeout=5.0,
                connection_attempts=3,
                retry_delay=2,
            )
        )

    def close(self):
        """Close the singleton connection."""
        with self._lock:
            if self._connection is not None and not self._connection.is_closed:
                try:
                    self._connection.close()
                    logger.info("RabbitMQ connection closed")
                except Exception as e:
                    logger.error(
                        "Error closing RabbitMQ connection",
                        extra={
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                        },
                    )
                finally:
                    self._connection = None


def _publish(exchange: str, routing_key: str, message: str):
    """Publish a message to RabbitMQ using the singleton connection."""
    ch = None
    try:
        conn = RabbitMQConnection().get_connection()
        ch = conn.channel()

        # Validate exchange exists before publishing
        ch.exchange_declare(exchange=exchange, passive=True)

        ch.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=message,
            properties=pika.BasicProperties(delivery_mode=2),
        )
        logger.info(
            "Message published successfully",
            extra={
                "exchange": exchange,
                "routing_key": routing_key,
                "message_length": len(message),
            },
        )
    except pika.exceptions.AMQPConnectionError as e:
        logger.error(
            "Connection error during publish",
            extra={
                "exchange": exchange,
                "routing_key": routing_key,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
    except pika.exceptions.ChannelError as e:
        logger.error(
            "Channel error (exchange may not exist)",
            extra={
                "exchange": exchange,
                "routing_key": routing_key,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
    except Exception as e:
        logger.error(
            "Unexpected error during message publish",
            extra={
                "exchange": exchange,
                "routing_key": routing_key,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
    finally:
        if ch is not None:
            try:
                ch.close()
            except Exception as close_error:
                logger.warning(
                    "Error closing channel",
                    extra={"error_message": str(close_error)},
                )


def publish(exchange: str, routing_key: str, message: str):
    """Publish a message asynchronously in a daemon thread."""
    thread = threading.Thread(
        target=_publish,
        args=(exchange, routing_key, message),
        daemon=True,
    )
    thread.start()


def register_shutdown_hook():
    """
    Register the RabbitMQ connection cleanup on process exit.

    Call this once during app startup to ensure graceful shutdown.

    Example:
        from your_library import publisher
        publisher.register_shutdown_hook()
    """

    def cleanup():
        try:
            RabbitMQConnection().close()
            logger.info("RabbitMQ connection closed cleanly on shutdown")
        except Exception as e:
            logger.error(
                "Error closing RabbitMQ connection on shutdown",
                extra={"error_type": type(e).__name__, "error_message": str(e)},
            )

    atexit.register(cleanup)
