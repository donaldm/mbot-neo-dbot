import os
import multiprocessing
import tempfile
import pygame

from mycroft_plugin_tts_mimic3 import Mimic3TTSPlugin


class TextToSpeechService(object):
    def __init__(self, lang, tts_config):
        self.lang = lang
        self.tts_config = tts_config
        self.phrases_queue = multiprocessing.Queue()
        self.tts_process = multiprocessing.Process(target=self._speak_process, args=(self.lang, self.tts_config, self.phrases_queue,))
        self.tts_process.start()

    def start(self):
        self.tts_process.start()

    def stop(self):
        with self.phrases_queue.queue.mutex:
            self.phrases_queue.queue.clear()
        self.tts_process.terminate()

    def speak(self, phrase):
        self.phrases_queue.put(phrase)

    @staticmethod
    def _speak_process(lang, tts_config, phrases_buffer):
        pygame.mixer.init()
        mimic = Mimic3TTSPlugin(lang=lang, config=tts_config)
        # We want to continue speaking until the stop_event is set
        while True:
            if not phrases_buffer.empty():
                phrase = phrases_buffer.get()
                mimic.get_tts(phrase, 'speak.wav')
                pygame.mixer.music.load('speak.wav')
                pygame.mixer.music.play()
