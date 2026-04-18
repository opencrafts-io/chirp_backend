import pika
from django.conf import settings
import threading


def _get_connection():
    creds = pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD)
    return pika.BlockingConnection(
        pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            virtual_host=settings.RABBITMQ_VHOST,
            credentials=creds,
        )
    )


def _publish(exchange: str, routing_key: str, message: str):
    conn = _get_connection()
    ch = conn.channel()
    ch.basic_publish(
        exchange=exchange,
        routing_key=routing_key,
        body=message,
        properties=pika.BasicProperties(delivery_mode=2),
    )
    conn.close()


def publish(exchange: str, routing_key: str, message: str):
    thread = threading.Thread(
        target=_publish,
        args=(exchange, routing_key, message),
        daemon=True,  # thread won't block Django shutdown
    )
    thread.start()
