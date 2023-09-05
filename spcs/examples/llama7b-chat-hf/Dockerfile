FROM nvcr.io/nvidia/pytorch:23.06-py3

COPY requirements.txt ./

RUN pip install -r requirements.txt

ADD exec ./exec

CMD ["./exec/controller.sh"]
