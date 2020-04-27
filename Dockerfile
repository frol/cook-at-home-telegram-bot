FROM frolvlad/alpine-python3

WORKDIR /opt
COPY ./requirements.txt ./
RUN pip install -r requirements.txt
COPY ./ ./

CMD ["python3", "manage.py"]
