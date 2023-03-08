import os
import multiprocessing
import pygame
import time
from mycroft_plugin_tts_mimic3 import Mimic3TTSPlugin


class TextToSpeechService(object):
    def __init__(self, lang, tts_config):
        self.lang = lang
        self.tts_config = tts_config
        self.phrases_queue = multiprocessing.Queue()
        self.stop_event = multiprocessing.Event()
        self.tts_process = None
        self.start(True)

    def start(self, initialize=False):
        print('Start talking')
        if initialize or self.stop_event.is_set():
            self.stop_event.clear()
            self.tts_process = multiprocessing.Process(target=self._speak_process, args=(self.lang, self.tts_config, self.phrases_queue, self.stop_event, ))
            self.tts_process.start()

    def stop(self):
        self.stop_event.set()
        while not self.phrases_queue.empty():
            self.phrases_queue.get()
        self.tts_process.join()

    def speak(self, phrase):
        self.phrases_queue.put(phrase)

    @staticmethod
    def _speak_process(lang, tts_config, phrases_buffer, stop_event):
        pygame.mixer.init()
        mimic = Mimic3TTSPlugin(lang=lang, config=tts_config)
        # We want to continue speaking until the stop_event is set
        while not stop_event.is_set():
            if not phrases_buffer.empty():
                phrase = phrases_buffer.get()
                sound_filename = 'speak.wav'
                mimic.get_tts(phrase, sound_filename)
                pygame.mixer.music.load(sound_filename)
                pygame.mixer.music.play()
                # Block until finished
                while pygame.mixer.music.get_busy():
                    if stop_event.is_set():
                        pygame.mixer.stop()
                        break
                    time.sleep(0.1)
