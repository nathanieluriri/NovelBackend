FROM python:3.9

RUN useradd -m -u 1000 user

WORKDIR /app

COPY ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY . /app

USER user
ENV PATH="/home/user/.local/bin:$PATH"

CMD ["gunicorn", "-w", "10", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:7860", "--timeout", "120", "--graceful-timeout", "30", "main:app"]
