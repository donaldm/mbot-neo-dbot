from kafka import KafkaConsumer
from messages.DBotCommand_pb2 import DBotCommand
import os
import json
import queue
import random
import re
import threading
from time import sleep
import pygame
import cyberpi


from makeblock.modules.cyberpi.api_cyberpi_api import module_auto
from makeblock.modules.cyberpi.api_cyberpi_api import autoconnect
from makeblock.protocols.PackData import HalocodePackData

# set SDL to use the dummy NULL video driver,
#   so it doesn't need a windowing system.
os.environ["SDL_VIDEODRIVER"] = "dummy"

pygame.init()

# Set up the drawing window
screen = pygame.display.set_mode([640, 480])


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
        self.intents = []
        self.speed = 0
        self.direction = ""

    def is_ready(self):
        cyberpi.audio.play("hello")

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

    def open_gripper(self):
        cyberpi.mbot2.servo_set(90, 's3')

    def close_gripper(self):
        cyberpi.mbot2.servo_set(140, 's3')

    def clap(self):
        self.open_gripper()
        self.close_gripper()
        cyberpi.audio.play("iron")
        self.open_gripper()
        self.close_gripper()
        cyberpi.audio.play("iron")
        cyberpi.audio.play("laugh")
        self.open_gripper()
        self.close_gripper()
        self.open_gripper()
        self.close_gripper()

    def shake(self):
        cyberpi.mbot2.turn_right(50, 0.1)
        cyberpi.mbot2.turn_left(50, 0.1)
        cyberpi.mbot2.turn_right(50, 0.1)
        cyberpi.mbot2.turn_left(50, 0.1)
        cyberpi.mbot2.turn_right(50, 0.1)
        cyberpi.mbot2.turn_left(50, 0.1)
        cyberpi.mbot2.turn_right(50, 0.1)
        cyberpi.mbot2.turn_left(50, 0.1)

    def raise_arm(self, angle):
        print(angle)
        cyberpi.mbot2.servo_set(angle, 's4')

    def lower_arm(self):
        cyberpi.mbot2.servo_release('s4')

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

    def process_open_gripper_intent(self, open_gripper_intent_json):
        self.open_gripper()

    def process_close_gripper_intent(self, close_gripper_intent_json):
        self.close_gripper()

    def process_raise_arm_intent(self, raise_arm_intent_json):
        angle = 180
        if 'Angle' in raise_arm_intent_json:
            angle_matches = re.findall(r'\d+', raise_arm_intent_json['Angle'])
            if len(angle_matches) > 0:
                angle = int(angle_matches[0])
                print(angle)

        self.raise_arm(angle)

    def process_lower_arm_intent(self, raise_arm_intent_json):
        self.lower_arm()

    def process_clap_intent(self):
        self.clap()

    def process_shake_intent(self):
        self.shake()

    def push_intent(self, intent):
        self.intents.append(intent)

    def obstacle_avoidance(self):
        if cyberpi.ultrasonic2.get() < 16:
            cyberpi.mbot2.backward(self.speed, 1)
            cyberpi.mbot2.turn_right(self.speed, 2)
            cyberpi.mbot2.forward(self.speed)

    def clear_screen(self, r, g, b):
        smile = pygame.image.load(os.path.join('images', 'smiley.png'))
        CyberPiExtras.utils.send_image_to_cyberpi(smile)

    def update(self):
        intent = self.intents.pop()

        intent_type = intent.get('intent_type')
        confidence = intent.get('confidence')

        if intent_type == "MoveIntent":
            print("We received a move intent!")
            self.process_move_intent(intent)
        elif intent_type == "TurnIntent":
            print("We received a turn intent!")
            self.process_turn_intent(intent)
        elif intent_type == "StopIntent":
            print("We received a stop intent!")
            self.process_stop_intent(intent)
        elif intent_type == "AccelerateIntent":
            print("we received an accelerate intent!")
            self.process_accelerate_intent(intent)
        elif intent_type == "DecelerateIntent":
            print("We received a decelerate intent!")
            self.process_decelerate_intent(intent)
        elif intent_type == "GreetingIntent":
            self.process_greeting_intent(intent)
        elif intent_type == "OpenGripperIntent":
            self.process_open_gripper_intent(intent)
        elif intent_type == "CloseGripperIntent":
            self.process_close_gripper_intent(intent)
        elif intent_type == "RaiseArmIntent":
            self.process_raise_arm_intent(intent)
        elif intent_type == "LowerArmIntent":
            self.process_lower_arm_intent(intent)
        elif intent_type == "ClapIntent":
            self.process_clap_intent()
        elif intent_type == "ShakeIntent":
            self.process_shake_intent()


def consume_intents(intents_buffer):
    dbot = DBot()
    dbot.is_ready()

    while True:
        if not intents_buffer.empty():
            intent = intents_buffer.get()
            print(intent)
            dbot.push_intent(intent)
            dbot.update()
        # dbot.obstacle_avoidance()
        sleep(0.25)



def main():
    intents_buffer = queue.Queue()

    consumer_thread = threading.Thread(target=consume_intents, args=(intents_buffer,))
    consumer_thread.start()

    dbot_command = DBotCommand()
    consumer = KafkaConsumer('dbot', bootstrap_servers='localhost:29092')
    for message in consumer:
        dbot_command.ParseFromString(message.value)
        intent_data = json.loads(dbot_command.intent_data)
        intents_buffer.put(intent_data)



if __name__ == '__main__':
    main()
