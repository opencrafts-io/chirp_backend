import pika
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def _create_connection() -> pika.BlockingConnection:
    """
    Creates and returns a new RabbitMQ BlockingConnection.

    A new connection is created on every call rather than reusing a singleton,
    because Celery workers are forked processes and sharing a single connection
    across forks corrupts the underlying TCP socket.
    """
    return pika.BlockingConnection(
        pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            virtual_host=settings.RABBITMQ_VHOST_ENCODED,
            credentials=pika.PlainCredentials(
                settings.RABBITMQ_USER,
                settings.RABBITMQ_PASSWORD,
            ),
            socket_timeout=5.0,
            connection_attempts=3,
            retry_delay=2,
        )
    )


def publish(exchange: str, routing_key: str, message: str) -> None:
    """
    Publishes a message to RabbitMQ and raises on failure so that
    the Celery task caller can catch and retry.

    Args:
        exchange: The RabbitMQ exchange to publish to.
        routing_key: The routing key for message delivery.
        message: The serialized message body to publish.

    Raises:
        pika.exceptions.AMQPError: On any RabbitMQ connection or channel failure.
    """
    conn = None
    try:
        conn = _create_connection()
        ch = conn.channel()
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
    except Exception as e:
        logger.error(
            "Failed to publish message",
            extra={
                "exchange": exchange,
                "routing_key": routing_key,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        raise
    finally:
        if conn is not None and conn.is_open:
            conn.close()
