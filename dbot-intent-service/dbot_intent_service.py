import os
import sys

from dbot_intent_service import DBotIntentParser
from messages.DBotIntent_pb2 import DBotIntent

SCRIPT_ROOT = os.path.dirname(os.path.realpath(__file__))


def main():
    dbot_intents_file_path = os.path.join(SCRIPT_ROOT, 'dbot_intents.yaml')
    dbot_intent_parser = DBotIntentParser(dbot_intents_file_path, SCRIPT_ROOT)

    print(dbot_intent_parser.calc_intent('Hello dbot'))
    print(dbot_intent_parser.calc_intent('move forwards'))

    dbot_intent_message = DBotIntent()
    dbot_intent_message.name = 'test'


if __name__ == '__main__':
    main()
