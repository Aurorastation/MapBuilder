# Dockerfile - this is a comment. Delete me if you want.
FROM python:3.8
COPY . /app
WORKDIR /app

RUN wget https://github.com/SpaceManiac/SpacemanDMM/releases/download/suite-1.9/dmm-tools.exe && \
    wget https://github.com/SpaceManiac/SpacemanDMM/releases/download/suite-1.9/dmm-tools && \
    chmod u+x dmm-tools.exe && \
    chmod u+x dmm-tools && \
    mkdir mapImages

RUN pip install -r requirements.txt

ENV GITHUB_SECRET DEFAULT
EXPOSE 5000
ENTRYPOINT ["python"]
CMD ["mapServer.py"]
