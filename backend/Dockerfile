FROM python:3.8.5
WORKDIR /app
COPY ./app
RUN pip3 install -r /app/requirements.txt --no-cache-dir
CMD ["gunicorn", "foodgram.wsgi:application", "--bind", "0:8000"]