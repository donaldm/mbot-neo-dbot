import argparse
import io
import threading
import queue
from tempfile import NamedTemporaryFile
import speech_recognition as sr
import whisper
from number_parser import parse
from datetime import datetime, timedelta
from time import sleep
from kafka import KafkaProducer
from messages.DBotStatus_pb2 import DBotStatus
from messages.DBotUtterance_pb2 import DBotUtterance
import json


def process_voice_events(args, audio_model, command_buffer):
    record_timeout = args.record_timeout
    phrase_timeout = args.phrase_timeout

    temp_file = NamedTemporaryFile().name
    transcription = ['']

    # The last time a recording was retreived from the queue.
    phrase_time = None
    # Current raw audio bytes.
    last_sample = bytes()
    # Thread safe Queue for passing data from the threaded recording callback.
    data_queue = queue.Queue()

    # We use SpeechRecognizer to record our audio because it has a nice feauture where it can detect when speech ends.
    recorder = sr.Recognizer()
    recorder.energy_threshold = args.energy_threshold
    # Definitely do this, dynamic energy compensation lowers the energy threshold dramtically to a point where the SpeechRecognizer never stops recording.
    recorder.dynamic_energy_threshold = False

    source = sr.Microphone(sample_rate=16000)
    with source:
        recorder.adjust_for_ambient_noise(source)

    def record_callback(_, audio:sr.AudioData) -> None:
        """
        Threaded callback function to recieve audio data when recordings finish.
        audio: An AudioData containing the recorded bytes.
        """
        # Grab the raw bytes and push it into the thread safe queue.
        data = audio.get_raw_data()
        data_queue.put(data)

    # Create a background thread that will pass us raw audio bytes.
    # We could do this manually but SpeechRecognizer provides a nice helper.
    recorder.listen_in_background(source, record_callback, phrase_time_limit=record_timeout)

    # Cue the user that we're ready to go.
    print("Model loaded.\n")
    dbot_status = DBotStatus()
    dbot_status.status = DBotStatus.STATUS_CODE.VOICE_MODEL_LOADED
    producer = KafkaProducer(bootstrap_servers=['localhost:29092'])
    producer.send('status', dbot_status.SerializeToString())

    while True:
        try:
            now = datetime.utcnow()
            # Pull raw recorded audio from the queue.
            if not data_queue.empty():
                phrase_complete = False
                # If enough time has passed between recordings, consider the phrase complete.
                # Clear the current working audio buffer to start over with the new data.
                if phrase_time and now - phrase_time > timedelta(seconds=phrase_timeout):
                    last_sample = bytes()
                    phrase_complete = True
                # This is the last time we received new audio data from the queue.
                phrase_time = now

                # Concatenate our current audio data with the latest audio data.
                while not data_queue.empty():
                    data = data_queue.get()
                    last_sample += data

                # Use AudioData to convert the raw data to wav data.
                audio_data = sr.AudioData(last_sample, source.SAMPLE_RATE, source.SAMPLE_WIDTH)
                wav_data = io.BytesIO(audio_data.get_wav_data())

                # Write wav data to the temporary file as bytes.
                with open(temp_file, 'w+b') as f:
                    f.write(wav_data.read())

                # Read the transcription.
                result = audio_model.transcribe(temp_file)
                print(result)
                no_speech_probability = 1
                if len(result['segments']) > 0:
                    no_speech_probability = result['segments'][0]['no_speech_prob']
                text = result['text'].strip()

                # If we detected a pause between recordings, add a new item to our transcripion.
                # Otherwise edit the existing one.
                if phrase_complete:
                    transcription.append(text)
                else:
                    if len(transcription) > 0:
                        transcription[-1] = text

                # Flush stdout.
                print('', end='', flush=True)

                if len(transcription) > 0:
                    command = parse(transcription.pop(0).lower())
                    # We only want to process likely commands and not noise
                    if no_speech_probability < 0.5:
                        print(command)
                        command_buffer.put(command)

                # Infinite loops are bad for processors, must sleep.
                sleep(0.25)
        except KeyboardInterrupt:
            break


def handle_intent(producer, current_command):
    print('Processing command: ' + current_command)

    dbot_utterance = DBotUtterance()
    dbot_utterance.utterance = current_command
    producer.send('utterances', dbot_utterance.SerializeToString())


def consume_commands(command_buffer):
    producer = KafkaProducer(bootstrap_servers=['localhost:29092'])
    while True:
        if not command_buffer.empty():
            command = command_buffer.get()
            handle_intent(producer, command)

        sleep(0.25)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="medium", help="Model to use",
                        choices=["tiny", "base", "small", "medium", "large"])
    parser.add_argument("--non_english", action='store_true',
                        help="Don't use the english model.")
    parser.add_argument("--energy_threshold", default=300,
                        help="Energy level for mic to detect.", type=int)
    parser.add_argument("--record_timeout", default=2,
                        help="How real time the recording is in seconds.", type=float)
    parser.add_argument("--phrase_timeout", default=2,
                        help="How much empty space between recordings before we "
                             "consider it a new line in the transcription.", type=float)
    args = parser.parse_args()

    model = args.model
    if args.model != "large" and not args.non_english:
        model = model + ".en"
    audio_model = whisper.load_model(model, device='cuda')

    buffer = queue.Queue()

    process_voice_thread = threading.Thread(target=process_voice_events, args=(args, audio_model, buffer,))
    process_voice_thread.start()

    consumer_thread = threading.Thread(target=consume_commands, args=(buffer,))
    consumer_thread.start()


if __name__ == '__main__':
    main()
