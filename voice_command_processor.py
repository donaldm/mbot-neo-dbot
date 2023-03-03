import argparse
import io
import threading
import queue
from tempfile import NamedTemporaryFile
import fuzzy
import speech_recognition as sr
import whisper
from adapt.engine import IntentDeterminationEngine
from adapt.intent import IntentBuilder
from number_parser import parse
from datetime import datetime, timedelta
from time import sleep
from kafka import KafkaProducer
from messages.DBotCommand_pb2 import DBotCommand
from messages.DBotStatus_pb2 import DBotStatus
from messages.DBotUtterance_pb2 import DBotUtterance
import json

engine = IntentDeterminationEngine()

move_keywords = [
    "move",
    "go"
]

for move_keyword in move_keywords:
    engine.register_entity(move_keyword, "MoveKeyword")

move_types = [
    "forward",
    "forwards",
    "backward",
    "backwards"
]

for move_type in move_types:
    engine.register_entity(move_type, "MoveType")

turn_keywords = [
    "turn"
]

for turn_keyword in turn_keywords:
    engine.register_entity(turn_keyword, "TurnKeyword")

turn_directions = [
    "left",
    "right"
]

for turn_direction in turn_directions:
    engine.register_entity(turn_direction, "TurnDirection")

stop_keywords = [
    "stop",
    "pause",
    "halt"
]

for stop_keyword in stop_keywords:
    engine.register_entity(stop_keyword, "StopKeyword")

engine.register_regex_entity("(?P<Speed>.*)")
engine.register_regex_entity("(?P<Angle>.*)")
engine.register_regex_entity("(?P<Question>.*)")

accelerate_keywords = [
    "faster"
]

for accelerate_keyword in accelerate_keywords:
    engine.register_entity(accelerate_keyword, "AccelerateKeyword")

decelerate_keywords = [
    "slower"
]

for decelerate_keyword in decelerate_keywords:
    engine.register_entity(decelerate_keyword, "DecelerateKeyword")

greeting_keywords = [
    "hello"
]

for greeting_keyword in greeting_keywords:
    engine.register_entity(greeting_keyword, "GreetingKeyword")

dbot_keywords = [
    "dbot",
    "DBOT",
    "buddy",
    "friend"
]

for dbot_keyword in dbot_keywords:
    engine.register_entity(dbot_keyword, "DBotKeyword")

open_keywords = [
    "open"
]

for open_keyword in open_keywords:
    engine.register_entity(open_keyword, "OpenKeyword")

close_keywords = [
    "close"
]

for close_keyword in close_keywords:
    engine.register_entity(close_keyword, "CloseKeyword")

gripper_keywords = [
    "gripper"
]

for gripper_keyword in gripper_keywords:
    engine.register_entity(gripper_keyword, "GripperKeyword")

raise_keywords = [
    "raise"
]

for raise_keyword in raise_keywords:
    engine.register_entity(raise_keyword, "RaiseKeyword")

lower_keywords = [
    "lower"
]

for lower_keyword in lower_keywords:
    engine.register_entity(lower_keyword, "LowerKeyword")

arm_keywords = [
    "arm"
]

for arm_keyword in arm_keywords:
    engine.register_entity(arm_keyword, "ArmKeyword")

clap_keywords = [
    "clap"
]

for clap_keyword in clap_keywords:
    engine.register_entity(clap_keyword, "ClapKeyword")

shake_keywords = [
    "shake"
]

for shake_keyword in shake_keywords:
    engine.register_entity(shake_keyword, "ShakeKeyword")

move_intent = IntentBuilder("MoveIntent")\
    .require("MoveKeyword")\
    .require("MoveType")\
    .optionally("Speed")\
    .build()

turn_intent = IntentBuilder("TurnIntent")\
    .require("TurnKeyword")\
    .require("TurnDirection")\
    .build()

stop_intent = IntentBuilder("StopIntent")\
    .require("StopKeyword")\
    .build()

accelerate_intent = IntentBuilder("AccelerateIntent")\
    .require("AccelerateKeyword")\
    .build()

decelerate_intent = IntentBuilder("DecelerateIntent")\
    .require("DecelerateKeyword")\
    .build()

greeting_intent = IntentBuilder("GreetingIntent")\
    .require("GreetingKeyword")\
    .require("DBotKeyword")\
    .build()

open_gripper_intent = IntentBuilder("OpenGripperIntent")\
    .require("OpenKeyword")\
    .require("GripperKeyword")\
    .build()

close_gripper_intent = IntentBuilder("CloseGripperIntent")\
    .require("CloseKeyword")\
    .require("GripperKeyword")\
    .build()

raise_arm_intent = IntentBuilder("RaiseArmIntent")\
    .require("RaiseKeyword")\
    .require("ArmKeyword")\
    .optionally("Angle")\
    .build()

lower_arm_intent = IntentBuilder("LowerArmIntent")\
    .require("LowerKeyword")\
    .require("ArmKeyword")\
    .build()

clap_intent = IntentBuilder("ClapIntent")\
    .require("ClapKeyword")\
    .build()

shake_intent = IntentBuilder("ShakeIntent")\
    .require("ShakeKeyword")\
    .build()

engine.register_intent_parser(move_intent)
engine.register_intent_parser(turn_intent)
engine.register_intent_parser(stop_intent)
engine.register_intent_parser(accelerate_intent)
engine.register_intent_parser(decelerate_intent)
engine.register_intent_parser(greeting_intent)
engine.register_intent_parser(open_gripper_intent)
engine.register_intent_parser(close_gripper_intent)
engine.register_intent_parser(raise_arm_intent)
engine.register_intent_parser(lower_arm_intent)
engine.register_intent_parser(clap_intent)
engine.register_intent_parser(shake_intent)


fallback_commands = [
    "move forward",
    "move backward",
    "go forward",
    "go backward",
    "turn left",
    "turn right",
    "hello dbot",
    "hi dbot",
    "stop",
    "faster",
    "slower",
    "open gripper",
    "close gripper",
    "raise arm",
    "lower arm",
    "clap",
    "shake"
]

dmetaphone = fuzzy.DMetaphone()

fallback_command_map = {}

for fallback_command in fallback_commands:
    metaphone = dmetaphone(fallback_command)[0]
    fallback_command_map[metaphone] = fallback_command


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
                    print(command)
                    command_buffer.put(command)

                # Infinite loops are bad for processors, must sleep.
                sleep(0.25)
        except KeyboardInterrupt:
            break

phrases_to_ignore = [
    'thank you.',
    '',
    '.',
    '.....'
]


def handle_intent(producer, current_command):
    print('Processing command: ' + current_command)

    dbot_utterance = DBotUtterance()
    dbot_utterance.utterance = current_command
    producer.send('utterances', dbot_utterance.SerializeToString())

    handled_intent = False
    for intent in engine.determine_intent(current_command):
        if intent and intent.get('confidence') > 0:
            print(json.dumps(intent, indent=4))
            intent_type = intent.get('intent_type')
            dbot_command = DBotCommand()
            dbot_command.intent_type = intent_type
            dbot_command.intent_data = json.dumps(intent)
            dbot_command.confidence = intent.get('confidence')
            producer.send('commands', dbot_command.SerializeToString())
            handled_intent = True

    if not handled_intent:
        metaphone = dmetaphone(current_command)[0]
        if metaphone in fallback_command_map:
            matching_command = fallback_command_map[metaphone]
            print('Call update again with ' + matching_command)
            handle_intent(producer, matching_command)

    if not handled_intent:
        for phrase in phrases_to_ignore:
            if current_command.strip() == phrase:
                return

        intent_data = {'intent_type': 'ChatGPTIntent',
                       'prompt': current_command}

        dbot_command = DBotCommand()
        dbot_command.intent_type = 'ChatGPTIntent'
        dbot_command.intent_data = json.dumps(intent_data)
        dbot_command.confidence = 1.0
        producer.send('commands', dbot_command.SerializeToString())


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
