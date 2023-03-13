FROM python:3.9.16-buster

ENV TEXT_TO_SPEECH_SERVICE_WORKDIR=/dbot/text_to_speech_service
RUN apt-get update
RUN apt-get install python3-dev alsa-utils pulseaudio -y
RUN apt-get install espeak-ng -y

WORKDIR ${TEXT_TO_SPEECH_SERVICE_WORKDIR}
COPY requirements.txt ${TEXT_TO_SPEECH_SERVICE_WORKDIR}
RUN pip3 install -r requirements.txt

COPY main.py ${TEXT_TO_SPEECH_SERVICE_WORKDIR}
COPY config.yaml ${TEXT_TO_SPEECH_SERVICE_WORKDIR}
COPY text_to_speech_service ${TEXT_TO_SPEECH_SERVICE_WORKDIR}/text_to_speech_service
COPY tests ${TEXT_TO_SPEECH_SERVICE_WORKDIR}/tests

COPY messages ${TEXT_TO_SPEECH_SERVICE_WORKDIR}/messages

ENTRYPOINT ["uvicorn", "main:app", "--proxy-headers", "--host", "0.0.0.0", "--port", "8000"]
