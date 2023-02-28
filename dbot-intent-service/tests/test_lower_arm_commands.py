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

@pytest.mark.raise_arm_commands
@pytest.mark.parametrize('phrase', ['lower arm'])
def test_lower_arm_commands(dbot_intent_parser_fixture, phrase):
    intent = dbot_intent_parser_fixture.calc_intent(f'{phrase}'.format(phrase=phrase))
    assert intent.name == 'lower_arm'
    assert intent.conf > 0.5
