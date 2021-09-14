FROM python:3.9

ENV POSTAL_CODE=00000
ENV DISTANCE_MI=50
ENV API_KEY=XXXX-XXXX-XXXXX
ENV INFLUX_BUCKET=mybucket
ENV INFLUX_ORG=myorg
ENV INFLUX_TOKEN=mytoken
ENV INFLUX_URL=https://influx.local.lan


WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY get-aq.py .

CMD python ./get-aq.py ${POSTAL_CODE} ${DISTANCE_MI} "${API_KEY}" \
--bucket "${INFLUX_BUCKET}" --org "${INFLUX_ORG}" --token "${INFLUX_TOKEN}" \
--url "$INFLUX_URL"
