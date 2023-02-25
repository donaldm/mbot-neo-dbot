import os
from dbot_intent_service import DBotIntentParser

SCRIPT_ROOT = os.path.dirname(os.path.realpath(__file__))


def main():
    dbot_intents_file_path = os.path.join(SCRIPT_ROOT, 'dbot_intents.yaml')
    dbot_intent_parser = DBotIntentParser(dbot_intents_file_path, SCRIPT_ROOT)

    os.system('ls -ltra')
    os.system('tail -n +1 *.entity')
    os.system('tail -n +1 *.intent')

    print(dbot_intent_parser.calc_intent('Hello dbot'))
    print(dbot_intent_parser.calc_intent('move forwards'))


if __name__ == '__main__':
    main()
