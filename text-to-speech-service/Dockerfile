FROM python:3.9.16-alpine3.17

ENV TEXT_TO_SPEECH_SERVICE_WORKDIR=/dbot/text_to_speech_service
RUN apk add python3-dev

WORKDIR ${TEXT_TO_SPEECH_SERVICE_WORKDIR}
COPY requirements.txt ${TEXT_TO_SPEECH_SERVICE_WORKDIR}
RUN pip3 install -r requirements.txt

COPY text_to_speech_service.py ${TEXT_TO_SPEECH_SERVICE_WORKDIR}
COPY text_to_speech_service ${TEXT_TO_SPEECH_SERVICE_WORKDIR}/text_to_speech_service
COPY tests ${TEXT_TO_SPEECH_SERVICE_WORKDIR}/tests

COPY messages ${TEXT_TO_SPEECH_SERVICE_WORKDIR}/messages

ENTRYPOINT ["python", "text_to_speech_service.py"]
