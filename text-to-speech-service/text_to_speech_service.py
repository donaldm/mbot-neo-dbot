#!/usr/bin/env python3

import os
import sys
import time
import yaml

import kafka.errors
from kafka import KafkaConsumer, KafkaProducer
from text_to_speech_service import TextToSpeechService
from messages.DBotTTSRequest_pb2 import DBotTTSRequest

SCRIPT_ROOT = os.path.dirname(os.path.realpath(__file__))


def main():
    config_path = os.path.join(SCRIPT_ROOT, 'config.yaml')
    with open(config_path, 'r') as config_file:
        config = yaml.safe_load(config_file)

    voice = config.get('voice')
    speaker = config.get('speaker')
    lang = voice.split('/')[0]
    config = {'voice': voice,
              'speaker': speaker,
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
            request = dbot_tts_request.request
            if request != '':
                request = request.replace('ChatGPT', 'Chat G P T')
                request = request.replace('OpenAI', 'Open A I')
                text_to_speech_service.speak(request)
            elif dbot_tts_request.stop_talking:
                text_to_speech_service.stop()
            elif dbot_tts_request.start_talking:
                text_to_speech_service.start()


if __name__ == '__main__':
    main()
