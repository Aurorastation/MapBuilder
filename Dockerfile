# Dockerfile - this is a comment. Delete me if you want.
FROM python:3.8
COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt


ENV GITHUB_SECRET DEFAULT
EXPOSE 5000
ENTRYPOINT ["python"]
CMD ["mapServer.py"]
