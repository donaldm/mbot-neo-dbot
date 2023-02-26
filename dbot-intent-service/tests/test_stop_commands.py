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


@pytest.mark.parametrize('stop_command', ['stop'])
@pytest.mark.parametrize('stop_target', ['', 'dbot', 'movement', 'talking'])
def test_stop(dbot_intent_parser_fixture, stop_command, stop_target):
    intent = dbot_intent_parser_fixture.calc_intent(f'{stop_command} {stop_target}'.format(stop_command=stop_command,
                                                                                           stop_target=stop_target))
    assert intent.name == 'stop'
    assert intent.get('stop_target', '') == stop_target
    assert intent.conf > 0.5
