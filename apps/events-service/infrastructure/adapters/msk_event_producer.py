# Assumptions:
# - Using confluent-kafka for Kafka operations
# - Events are JSON serialized
# - Producer configuration provided externally

import json

from confluent_kafka import Producer


class MskProducer:
    """MSK/Kafka event producer"""

    def __init__(self, conf):
        self.p = Producer(conf)

    def publish(self, topic: str, key: str, value: dict):
        """Publish event to Kafka topic"""
        self.p.produce(topic, key=key, value=json.dumps(value).encode("utf-8"))
        self.p.flush(1)
