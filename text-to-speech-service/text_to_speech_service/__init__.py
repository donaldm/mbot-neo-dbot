import pyttsx3
import queue
import threading


class TextToSpeechService(object):
    def __init__(self):
        self.phrases_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.tts_thread = threading.Thread(target=self.speak, args=(self.phrases_queue,))
        self.tts_thread.start()

    def start(self):
        self.stop_event.clear()
        self.tts_thread.start()

    def stop(self):
        self.stop_event.set()
        with self.phrases_queue.queue.mutex:
            self.phrases_queue.queue.clear()

    @staticmethod
    def speak(phrases_buffer, stop_event):
        tts_engine = pyttsx3.init()
        # We will handle the text to speech loop ourself so we can
        # terminate the text to speech when we want
        tts_engine.startLoop(False)
        voices = tts_engine.getProperty('voices')
        tts_engine.setProperty('voice', voices[1].id)

        # We want to continue speaking until the stop_event is set
        while not stop_event.is_set():
            if not phrases_buffer.empty():
                phrase = phrases_buffer.get()
                tts_engine.say(phrase)
                tts_engine.runAndWait()

        tts_engine.endLoop()
        del tts_engine


