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

@pytest.mark.move_commands
@pytest.mark.parametrize('move_command', ['go', 'move'])
@pytest.mark.parametrize('move_direction', ['forwards', 'backwards'])
def test_move(dbot_intent_parser_fixture, move_command, move_direction):
    intent = dbot_intent_parser_fixture.calc_intent(f'{move_command} {move_direction}'.format(move_command=move_command,
                                                                                              move_direction=move_direction))
    assert intent.name == 'move'
    assert intent.get('move_direction') == move_direction
    assert intent.conf > 0.5
