import argparse
import io
import os
import json
import queue
import random
import re
import threading
from datetime import datetime, timedelta
from queue import Queue
from tempfile import NamedTemporaryFile
from time import sleep
import pygame
import cyberpi
import fuzzy
import speech_recognition as sr
import whisper
from adapt.engine import IntentDeterminationEngine
from adapt.intent import IntentBuilder
from number_parser import parse

from makeblock.modules.cyberpi.api_cyberpi_api import module_auto
from makeblock.modules.cyberpi.api_cyberpi_api import autoconnect
from makeblock.protocols.PackData import HalocodePackData

# set SDL to use the dummy NULL video driver,
#   so it doesn't need a windowing system.
os.environ["SDL_VIDEODRIVER"] = "dummy"

pygame.init()

# Set up the drawing window
screen = pygame.display.set_mode([640, 480])

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

engine.register_intent_parser(move_intent)
engine.register_intent_parser(turn_intent)
engine.register_intent_parser(stop_intent)
engine.register_intent_parser(accelerate_intent)
engine.register_intent_parser(decelerate_intent)
engine.register_intent_parser(greeting_intent)


def set_transfer_mode():
    autoconnect()
    repl_mode = HalocodePackData.repl_mode()
    repl_mode.mode = HalocodePackData.TYPE_RUN_WITHOUT_RESPONSE
    repl_mode.on_response = module_auto.common_request_response_cb
    module_auto.send_script(repl_mode)
    module_auto._board.repl('import communication')
    module_auto._board.repl('communication.bind_passthrough_channels("uart0", "uart1")')


def send_repl(command):
    autoconnect()
    REQUEST_DELAY_TIME = 0.001
    module_auto.delay_sync(REQUEST_DELAY_TIME)
    module_auto._board.repl(command)


def send_command(command):
    autoconnect()
    REQUEST_DELAY_TIME = 0.001
    module_auto.delay_sync(REQUEST_DELAY_TIME)
    pack = HalocodePackData()
    pack.type = HalocodePackData.TYPE_SCRIPT
    pack.script = command
    pack.on_response = module_auto.common_request_response_cb
    pack.mode = HalocodePackData.TYPE_RUN_WITHOUT_RESPONSE
    module_auto.send_script(pack)
    #module_auto._board.repl(command)


class CyberPiSprite(object):
    def __init__(self, variable_name, file_path):
        self.variable_name = variable_name
        self.image = pygame.image.load(file_path)


class _CyberPiExtrasBackground(object):
    @staticmethod
    def fill(r, g, b):
        send_command('cyberpi.background.fill({r},{g},{b})'.format(r=r, g=g, b=b))


class _CyberPiExtrasScreen(object):
    @staticmethod
    def render():
        send_command('cyberpi.screen.render()')


class _CyberPiExtrasUtils(object):
    @staticmethod
    def send_image_to_cyberpi(image):
        image_width = image.get_width()
        image_height = image.get_height()


        #set_transfer_mode()
        # send_command('cyberpi.screen.disable_autorender()')
        send_repl("dog1 = cyberpi.sprite()")
        send_command("dog1.draw_QR('www.google.com')\r\ndog1.move_to(64,64)\r\ndog1.show()\r\ncyberpi.screen.render()")

        image_array = []
        for j in range(0, image_height):
            for i in range(0, image_width):
                color = image.get_at((i, j))
                red = color.r
                green = color.g
                blue = color.b
                hex_value = f'{red:02x}{green:02x}{blue:02x}'
                hex_value = '0x' + hex_value.upper()

                image_array.append(hex_value)



class CyberPiExtras(object):
    background = _CyberPiExtrasBackground
    screen = _CyberPiExtrasScreen
    utils = _CyberPiExtrasUtils


class DBot(object):
    def __init__(self):
        self.commands = []
        self.speed = 0
        self.direction = ""
        self.dmetaphone = fuzzy.DMetaphone()

        self.fallback_commands = [
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
            "slower"
        ]

        self.fallback_command_map = {}

        for fallback_command in self.fallback_commands:
            metaphone = self.dmetaphone(fallback_command)[0]
            self.fallback_command_map[metaphone] = fallback_command

    def move_forward(self, speed=10):
        print("DBot move forward {speed}".format(speed=speed))
        cyberpi.mbot2.forward(speed)
        self.speed = speed
        self.direction = "forward"

    def move_backward(self, speed=10):
        print("DBot move backward {speed}".format(speed=speed))
        cyberpi.mbot2.backward(speed)
        self.speed = speed
        self.direction = "backward"

    def move_in_direction(self, speed):
        if self.direction == "forward":
            self.move_forward(speed)
        elif self.direction == "backward":
            self.move_backward(speed)

    def turn_left(self):
        cyberpi.mbot2.turn_left(self.speed)

    def turn_right(self):
        cyberpi.mbot2.turn_right(self.speed)

    def accelerate(self):
        self.speed = min(self.speed + self.speed * 0.25, 100)
        self.move_in_direction(self.speed)

    def decelerate(self):
        self.speed = max(self.speed - self.speed * 0.25, 0)
        self.move_in_direction(self.speed)

    def stop(self):
        print("Dbot stop")
        cyberpi.mbot2.forward(0)
        cyberpi.mbot2.backward(0)
        self.speed = 0

    def play_greeting(self):
        greeting = random.choice(['hi', 'hello'])
        cyberpi.audio.play(greeting)
        self.play_ultrasonic_emotion('happy')

    def play_ultrasonic_emotion(self, emotion):
        cyberpi.ultrasonic2.play(emotion)

    def process_move_intent(self, move_intent_json):
        move_type = move_intent_json["MoveType"]
        speed = 10
        if 'Speed' in move_intent_json:
            speed_matches = re.findall(r'\d+', move_intent_json['Speed'])
            if len(speed_matches) > 0:
                speed = int(speed_matches[0])
                print(speed)

        if "forward" in move_type:
            self.move_forward(speed)
        elif "backward" in move_type:
            self.move_backward(speed)

    def process_turn_intent(self, turn_intent_json):
        turn_direction = turn_intent_json["TurnDirection"]
        if "left" in turn_direction:
            self.turn_left()
        elif "right" in turn_direction:
            self.turn_right()

    def process_stop_intent(self, stop_intent_json):
        self.stop()

    def process_accelerate_intent(self, accelerate_intent_json):
        self.accelerate()

    def process_decelerate_intent(self, decelerate_intent_json):
        self.decelerate()

    def process_greeting_intent(self, greeting_intent_json):
        self.play_greeting()

    def push_command(self, command):
        self.commands.append(command)

    def obstacle_avoidance(self):
        if cyberpi.ultrasonic2.get() < 16:
            cyberpi.mbot2.backward(self.speed, 1)
            cyberpi.mbot2.turn_right(self.speed, 2)
            cyberpi.mbot2.forward(self.speed)

    def clear_screen(self, r, g, b):
        smile = pygame.image.load(os.path.join('images', 'smiley.png'))
        CyberPiExtras.utils.send_image_to_cyberpi(smile)

    def update(self, current_command=""):
        if current_command == "":
            current_command = self.commands.pop()

        print('Processing command: ' + current_command)
        handled_intent = False
        for intent in engine.determine_intent(current_command):
            if intent and intent.get('confidence') > 0:
                print(json.dumps(intent, indent=4))
                intent_type = intent['intent_type']
                if intent_type == "MoveIntent":
                    print("We received a move intent!")
                    self.process_move_intent(intent)
                    handled_intent = True
                elif intent_type == "TurnIntent":
                    print("We received a turn intent!")
                    self.process_turn_intent(intent)
                    handled_intent = True
                elif intent_type == "StopIntent":
                    print("We received a stop intent!")
                    self.process_stop_intent(intent)
                    handled_intent = True
                elif intent_type == "AccelerateIntent":
                    print("we received an accelerate intent!")
                    self.process_accelerate_intent(intent)
                    handled_intent = True
                elif intent_type == "DecelerateIntent":
                    print("We received a decelerate intent!")
                    self.process_decelerate_intent(intent)
                    handled_intent = True
                elif intent_type == "GreetingIntent":
                    self.process_greeting_intent(intent)
                    handled_intent = True

        if not handled_intent:
            metaphone = self.dmetaphone(current_command)[0]
            if metaphone in self.fallback_command_map:
                matching_command = self.fallback_command_map[metaphone]
                print('Call update again with ' + matching_command)
                self.update(matching_command)


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
    data_queue = Queue()

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


def consume_commands(command_buffer):
    dbot = DBot()

    while True:
        if not command_buffer.empty():
            command = command_buffer.get()
            print(command)
            dbot.push_command(command)
            dbot.update()
        dbot.obstacle_avoidance()
        sleep(0.25)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="medium", help="Model to use",
                        choices=["tiny", "base", "small", "medium", "large"])
    parser.add_argument("--non_english", action='store_true',
                        help="Don't use the english model.")
    parser.add_argument("--energy_threshold", default=300,
                        help="Energy level for mic to detect.", type=int)
    parser.add_argument("--record_timeout", default=1,
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


# def main():
    """
    sleep(1)
    cyberpi.audio.play('angry')
    sleep(1)
    cyberpi.mbot2.forward(1)

    for x in range(0, 40):
        cyberpi.led.on(255, 0, 0)
        cyberpi.audio.play_tone(988, 0.25)
        sleep(0.25)
        cyberpi.led.on(0, 0, 255)
        cyberpi.audio.play_tone(1397, 0.25)
        sleep(0.25)

    cyberpi.mbot2.forward(0)
    sleep(1)
    print('done')
    """
    """
    # obtain audio from the microphone
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Say something!")
        audio = r.listen(source)

    # recognize speech using whisper
    try:
        print("Whisper thinks you said " + r.recognize_whisper(audio, language="english"))
    except sr.UnknownValueError:
        print("Whisper could not understand audio")
    except sr.RequestError as e:
        print("Could not request results from Whisper")
    """


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
