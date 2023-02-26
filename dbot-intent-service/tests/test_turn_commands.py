import os
import sys
import pytest

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from dbot_intent_service import DBotIntentParser

@pytest.fixture
def dbot_intent_parser_fixture():
    dbot_intents_file_path = os.path.join(parent, 'dbot_intents.yaml')
    dbot_intent_parser = DBotIntentParser(dbot_intents_file_path, parent)
    return dbot_intent_parser

@pytest.mark.stop_commands
@pytest.mark.parametrize('turn_command', ['turn'])
@pytest.mark.parametrize('turn_direction', ['left', 'right'])
def test_turn(dbot_intent_parser_fixture, turn_command, turn_direction):
    intent = dbot_intent_parser_fixture.calc_intent(f'{turn_command} {turn_direction}'.format(turn_command=turn_command,
                                                                                              turn_direction=turn_direction))
    assert intent.name == 'turn'
    assert intent.get('turn_direction', '') == turn_direction
    assert intent.conf > 0.5
