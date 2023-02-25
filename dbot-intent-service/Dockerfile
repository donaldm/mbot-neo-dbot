FROM python:3.9.16-alpine3.17

ENV INTENT_SERVICE_WORKDIR=/dbot/intent_service
RUN apk add python3-dev swig fann-dev py3-fann2-dev gcc g++

WORKDIR ${INTENT_SERVICE_WORKDIR}
COPY requirements.txt ${INTENT_SERVICE_WORKDIR}
RUN pip3 install -r requirements.txt

COPY dbot_intent_service.py ${INTENT_SERVICE_WORKDIR}
COPY dbot_intents.yaml ${INTENT_SERVICE_WORKDIR}
COPY dbot_intent_service ${INTENT_SERVICE_WORKDIR}/dbot_intent_service

ENTRYPOINT ["python", "dbot_intent_service.py"]
