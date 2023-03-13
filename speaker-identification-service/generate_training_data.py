#!/usr/bin/env python3

import argparse
import tarfile
import random
import os
from typing import List, Dict


class TrainingDataProcessor(object):
    def __init__(self, training_data_path: str):
        self.training_data_path = training_data_path
        self.speaker_data_ids = set()
        self.speakers = {}
        self.male_speakers = {}
        self.female_speakers = {}
        self.chapters = {}

    @staticmethod
    def _process_csv_data(csv_lines, id_column_idx: int, column_names: List) -> Dict:
        csv_dict = {}
        for data_line in csv_lines:
            data_line = data_line.decode('utf-8')
            data_line = data_line.replace('\n', '')
            if not data_line.startswith(';'):
                column_data = data_line.split('|', len(column_names) - 1)
                key = column_data[id_column_idx].strip()
                csv_dict.setdefault(key, {})
                for column_idx, column_name in enumerate(column_names):
                    if column_idx != id_column_idx:
                        csv_dict[key][column_name] = column_data[column_idx].strip()
        return csv_dict

    def _process_speaker_data(self, tf):
        speaker_data = tf.extractfile('LibriSpeech/SPEAKERS.TXT').readlines()
        speaker_data_columns = ['id', 'sex', 'subset', 'minutes', 'name']
        self.speakers = self._process_csv_data(speaker_data, 0, speaker_data_columns)

    def _process_chapter_data(self, tf):
        chapter_data = tf.extractfile('LibriSpeech/CHAPTERS.TXT').readlines()
        chapter_data_columns = ['id', 'reader', 'minutes', 'subset', 'project', 'book_id',
                                'chapter_title', 'project_tile']
        self.chapters = self._process_csv_data(chapter_data, 0, chapter_data_columns)

    def correlate_chapters_to_speakers(self):
        for chapter_id in self.chapters:
            chapter_dict = self.chapters[chapter_id]
            speaker_id = chapter_dict['reader']
            if speaker_id in self.speakers.keys():
                self.speakers[speaker_id].setdefault('chapters', {})
                self.speakers[speaker_id]['chapters'][chapter_id] = chapter_dict

    def process_members(self, tf):
        for member in tf.getmembers():
            if member.isdir() and not member.issym():
                path_components = member.path.split('/')
                if len(path_components) > 2:
                    speaker_id = path_components[2]
                    self.speaker_data_ids.add(speaker_id)

    def prune_speaker_data(self) -> Dict:
        new_speakers = {}
        for speaker_id in self.speakers:
            if speaker_id in self.speaker_data_ids:
                speaker_dict = self.speakers[speaker_id]
                new_speakers[speaker_id] = speaker_dict
        return new_speakers

    def seperate_speakers(self):
        for speaker_id in self.speakers:
            speaker_dict = self.speakers[speaker_id]
            sex = speaker_dict['sex']
            if sex == 'M':
                self.male_speakers[speaker_id] = speaker_dict
            elif sex == 'F':
                self.female_speakers[speaker_id] = speaker_dict

    def get_speaker_transcripts(self, tf, speaker_dict: Dict, speaker_id: int) -> List:
        speaker_data = speaker_dict[speaker_id]
        chapters = speaker_data['chapters']
        transcripts = []
        for chapter_id in chapters:
            transcript_path = f'LibriSpeech/train-clean-100/{speaker_id}/{chapter_id}/{speaker_id}-{chapter_id}.trans.txt'
            transcript = tf.extractfile(transcript_path).readlines()
            for line in transcript:
                line = line.decode('utf-8')
                transcript_id, transcript_line = line.split(' ', 1)
                transcript_line = transcript_line.strip()
                transcripts.append((speaker_id, chapter_id, transcript_id, transcript_line))
        return transcripts


    def extract_training_data(self, tf, transcripts):
        for transcript in transcripts:
            speaker_id, chapter_id, transcript_id, transcript_text = transcript
            print(transcript_id)

    def generate_training_data(self, tf, speaker_count: int):
        if not os.path.exists('training_data'):
            os.mkdir('training_data')

        male_speaker_ids = random.sample(list(self.male_speakers.keys()), speaker_count)
        female_speaker_id = random.sample(list(self.female_speakers.keys()), speaker_count)

        for speaker_id in male_speaker_ids:
            transcripts = self.get_speaker_transcripts(tf, self.male_speakers, speaker_id)
            self.extract_training_data(tf, transcripts)

        for speaker_id in female_speaker_id:
            transcripts = self.get_speaker_transcripts(tf, self.female_speakers, speaker_id)
            self.extract_training_data(tf, transcripts)

    def process_data(self, speaker_count: int):
        with tarfile.open(self.training_data_path, 'r') as tf:
            self._process_speaker_data(tf)
            self._process_chapter_data(tf)
            self.correlate_chapters_to_speakers()
            self.process_members(tf)
            self.speakers = self.prune_speaker_data()
            self.seperate_speakers()
            self.generate_training_data(tf, speaker_count)



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--training_data', default='', help='The path to the training data')

    args = parser.parse_args()

    print(args.training_data)

    training_data_processor = TrainingDataProcessor(args.training_data)
    training_data_processor.process_data(5)

    # Choose a random selection of speakers (both Male and Female)



if __name__ == '__main__':
    main()
