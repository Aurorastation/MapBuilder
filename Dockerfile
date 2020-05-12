# Dockerfile - this is a comment. Delete me if you want.
FROM python:3.8
COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt
RUN wget https://github.com/SpaceManiac/SpacemanDMM/releases/download/suite-1.4/dmm-tools.exe && \
    wget https://github.com/SpaceManiac/SpacemanDMM/releases/download/suite-1.4/dmm-tools && \
    chmod u+x dmm-tools.exe && \
    chmod u+x dmm-tools


ENV GITHUB_SECRET DEFAULT
EXPOSE 5000
ENTRYPOINT ["python"]
CMD ["mapServer.py"]
