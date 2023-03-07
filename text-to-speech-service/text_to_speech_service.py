#!/usr/bin/env python3

import os
import sys
import time

import kafka.errors
from kafka import KafkaConsumer, KafkaProducer
from text_to_speech_service import TextToSpeechService
from messages.DBotTTSRequest_pb2 import DBotTTSRequest

SCRIPT_ROOT = os.path.dirname(os.path.realpath(__file__))


def main():
    voice = 'en_US/hifi-tts_low'
    lang = voice.split('/')[0]
    config = {'voice': voice,
              'speaker': '92',
              'voices_download_dir': SCRIPT_ROOT}

    text_to_speech_service = TextToSpeechService(lang, config)

    kafka_bootstrap_host = os.environ.get('KAFKA_BOOTSTRAP_HOST', '')
    kafka_bootstrap_port = os.environ.get('KAFKA_BOOTSTRAP_PORT', '')

    if kafka_bootstrap_host == '':
        print('Please set KAFKA_BOOTSTRAP_HOST environmental variable.')
        sys.exit(-1)

    if kafka_bootstrap_port == '':
        print('Please set KAFKA_BOOTSTRAP_PORT environmental variable.')
        sys.exit(-1)

    kafka_server_url = f'{kafka_bootstrap_host}:{kafka_bootstrap_port}'

    print(f'Connecting to {kafka_server_url}...')
    connected = False
    while not connected:
        try:
            consumer = KafkaConsumer(bootstrap_servers=[kafka_server_url])
            consumer.subscribe(['tts'])
            connected = True
        except kafka.errors.NoBrokersAvailable as error:
            print('Waiting on Kafka to connect')
            time.sleep(1)

    for message in consumer:
        if message.topic == 'tts':
            dbot_tts_request = DBotTTSRequest()
            dbot_tts_request.ParseFromString(message.value)
            print(dbot_tts_request.request)
            text_to_speech_service.speak(dbot_tts_request.request)


if __name__ == '__main__':
    main()
