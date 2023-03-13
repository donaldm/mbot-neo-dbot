#!/usr/bin/env python3

import os
import sys
import time
import yaml

import asyncio
import aiokafka.errors
from aiokafka import AIOKafkaConsumer
from text_to_speech_service import TextToSpeechService
from messages.DBotTTSRequest_pb2 import DBotTTSRequest
from fastapi import FastAPI
from fastapi.responses import FileResponse

SCRIPT_ROOT = os.path.dirname(os.path.realpath(__file__))

app = FastAPI()
loop = asyncio.get_event_loop()

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
        consumer = AIOKafkaConsumer(bootstrap_servers=[kafka_server_url], loop=loop)
        consumer.subscribe(['tts'])
        connected = True
    except aiokafka.errors.NoBrokersAvailable as error:
        print('Waiting on Kafka to connect')
        time.sleep(1)


async def consume():
    await consumer.start()
    try:
        async for message in consumer:
            if message.topic == 'tts':
                dbot_tts_request = DBotTTSRequest()
                dbot_tts_request.ParseFromString(message.value)
                request = dbot_tts_request.request
                if request != '':
                    request = request.replace('ChatGPT', 'Chat G P T')
                    request = request.replace('OpenAI', 'Open A I')
                    text_to_speech_service.speak(request, dbot_tts_request.skip_playing)
                elif dbot_tts_request.stop_talking:
                    text_to_speech_service.stop()
                elif dbot_tts_request.start_talking:
                    text_to_speech_service.start()

    finally:
        await consumer.stop()


@app.on_event('startup')
async def startup_event():
    loop.create_task(consume())


@app.on_event('shutdown')
async def shutdown_event():
    await consumer.stop()


@app.get('/download-tts-audio')
def download_tts_audio():
    audio_file_name = 'speak.wav'
    audio_file_path = os.path.join(SCRIPT_ROOT, audio_file_name)
    return FileResponse(audio_file_path, media_type='application/octet-stream', filename=audio_file_name)
