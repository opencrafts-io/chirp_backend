import pika
from django.conf import settings


class BaseConsumer:
    queue_name = None
    exchange_name = None
    exchange_type = "topic"
    routing_key = "#"

    def handle_message(self, body: str, routing_key: str):
        """Override this in subclasses."""
        raise NotImplementedError

    def start(self):
        creds = pika.PlainCredentials(
            settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD
        )
        conn = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                virtual_host=settings.RABBITMQ_VHOST,
                credentials=creds,
            )
        )
        ch = conn.channel()

        # Declare exchange if specified
        if self.exchange_name:
            ch.exchange_declare(
                exchange=self.exchange_name,
                exchange_type=self.exchange_type,
                durable=True,
            )

        # Declare queue
        ch.queue_declare(queue=self.queue_name, durable=True)

        # Bind queue to exchange if exchange_name is set
        if self.exchange_name:
            ch.queue_bind(
                queue=self.queue_name,
                exchange=self.exchange_name,
                routing_key=self.routing_key,
            )

        def callback(ch, method, properties, body):
            self.handle_message(body.decode(), method.routing_key)

        ch.basic_consume(
            queue=self.queue_name,
            on_message_callback=callback,
            auto_ack=True,
        )

        print(
            f"[event_bus] Listening on queue '{self.queue_name}'"
            f"{' bound to exchange ' + self.exchange_name if self.exchange_name else ''}…"
        )
        ch.start_consuming()
