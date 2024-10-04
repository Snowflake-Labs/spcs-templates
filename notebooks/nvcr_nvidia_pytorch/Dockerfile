FROM nvcr.io/nvidia/pytorch:23.08-py3

RUN pip install --upgrade pip
COPY requirements.txt ./
RUN pip install -r ./requirements.txt

COPY entrypoint.sh ./
RUN chmod +x ./entrypoint.sh

ENTRYPOINT [ "./entrypoint.sh" ]