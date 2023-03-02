#!/usr/bin/env python3

import os
import sys
from kafka import KafkaConsumer, KafkaProducer
from dbot_intent_service import DBotIntentParser
from messages.DBotUtterance_pb2 import DBotUtterance
from messages.DBotIntent_pb2 import DBotIntent

SCRIPT_ROOT = os.path.dirname(os.path.realpath(__file__))


def main():
    dbot_intents_file_path = os.path.join(SCRIPT_ROOT, 'dbot_intents.yaml')
    dbot_intent_parser = DBotIntentParser(dbot_intents_file_path, SCRIPT_ROOT)

    kafka_bootstrap_host = os.environ.get('KAFKA_BOOTSTRAP_HOST', '')
    kafka_bootstrap_port = os.environ.get('KAFKA_BOOTSTRAP_PORT', '')

    if kafka_bootstrap_host == '':
        print('Please set KAFKA_BOOTSTRAP_HOST environmental variable.')
        sys.exit(-1)

    if kafka_bootstrap_port == '':
        print('Please set KAFKA_BOOTSTRAP_PORT environmental variable.')
        sys.exit(-1)

    kafka_server_url = f'{kafka_bootstrap_host}:{kafka_bootstrap_port}'

    producer = KafkaProducer(bootstrap_servers=[kafka_server_url])

    consumer = KafkaConsumer(bootstrap_servers=[kafka_server_url])
    consumer.subscribe(['utterances'])

    for message in consumer:
        if message.topic == 'utterances':
            dbot_intent = dbot_intent_parser.calc_intent(message.utterance)
            dbot_intent_message = DBotIntent()
            dbot_intent_message.name = dbot_intent.name
            dbot_intent_message.sent = dbot_intent.sent
            dbot_intent_message.matches = dbot_intent.matches
            dbot_intent_message.conf = dbot_intent.conf
            producer.send('intents', dbot_intent_message.SerializeToString())


if __name__ == '__main__':
    main()
