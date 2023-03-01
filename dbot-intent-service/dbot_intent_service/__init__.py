import yaml
from padatious import IntentContainer
import os
import glob
from pathlib import Path
import json


class PadatiousIntentGenerator(object):
    def __init__(self, dbot_intent_file_path):
        self.dbot_intent_file_path = dbot_intent_file_path
        with open(self.dbot_intent_file_path, 'r') as dbot_intent_file:
            self.dbot_intent_yaml = yaml.safe_load(dbot_intent_file)

    def generate_intent_files(self, output_directory):
        for entity in self.dbot_intent_yaml.get('entities', []):
            entity_name = entity.get('name')
            entity_file_name = os.path.join(output_directory, entity_name + '.entity')
            entity_choices = entity.get('choices')
            with open(entity_file_name, 'w') as entity_file:
                for entity_choice in entity_choices:
                    entity_file.write(entity_choice + '\n')

        for intent in self.dbot_intent_yaml.get('intents', []):
            intent_name = intent.get('name')
            intent_file_name = os.path.join(output_directory, intent_name + '.intent')
            example_sentences = intent.get('example_sentences')
            with open(intent_file_name, 'w') as intent_file:
                for example_sentence in example_sentences:
                    intent_file.write(example_sentence + '\n')


class DBotIntentParser(object):
    def __init__(self, dbot_intents_file_path, output_directory):
        self.output_directory = output_directory
        self.padatious_intent_generator = PadatiousIntentGenerator(dbot_intents_file_path)
        self.padatious_intent_generator.generate_intent_files(output_directory)
        self.container = IntentContainer('intent_cache')

        for entity_file_path in glob.glob('*.entity'):
            entity_name = Path(entity_file_path).stem
            self.container.load_entity(entity_name, entity_file_path)

        for intent_file_path in glob.glob('*.intent'):
            intent_name = Path(intent_file_path).stem
            self.container.load_intent(intent_name, intent_file_path)

        self.container.train()

    def calc_intent(self, input_text):
        intent = self.container.calc_intent(input_text)
        return intent
