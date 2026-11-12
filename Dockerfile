FROM python:3.13-slim

WORKDIR /app

# Standard library only: nothing to install.
COPY ver2_mail.py .

# The configuration (with SMTP credentials) is mounted at run time, never baked
# into the image. See "Run with Docker" in the README.
CMD ["python", "ver2_mail.py"]
