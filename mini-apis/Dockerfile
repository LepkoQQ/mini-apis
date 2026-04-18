FROM python:3.14-slim

RUN useradd -m mini-apis

EXPOSE 5000

ENV PORT=5000 \
  PYTHONUNBUFFERED=1 \
  DEBIAN_FRONTEND=noninteractive \
  PIP_ROOT_USER_ACTION=ignore

COPY requirements.txt /
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app
RUN chown mini-apis:mini-apis /app

COPY --chown=mini-apis:mini-apis api api
COPY --chown=mini-apis:mini-apis app.py .

USER mini-apis

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
