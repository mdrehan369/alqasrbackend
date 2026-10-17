# Use a lightweight, official Python base image
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

# Install dependencies without saving the pip cache to keep the image small
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the rest of your application code into the container
COPY ./app /code/app

EXPOSE 8000

CMD ["fastapi", "run", "app/main.py", "--port", "8000"]

