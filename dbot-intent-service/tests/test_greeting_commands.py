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

@pytest.mark.greeting_commands
@pytest.mark.parametrize('greeting', ['hello', 'hi'])
@pytest.mark.parametrize('subject', ['', 'dbot', 'friend', 'buddy'])
def test_turn(dbot_intent_parser_fixture, greeting, subject):
    intent = dbot_intent_parser_fixture.calc_intent(f'{greeting} {subject}'.format(greeting=greeting,
                                                                                   subject=subject))
    assert intent.name == 'greeting'
    assert intent.conf > 0.5
