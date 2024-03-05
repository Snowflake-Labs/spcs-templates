FROM nvidia/cuda:11.8.0-devel-ubuntu22.04

RUN apt-get update -y
RUN apt-get install -y python3-pip git

COPY ray_requirements.txt ./

RUN pip3 install -r ray_requirements.txt

COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
