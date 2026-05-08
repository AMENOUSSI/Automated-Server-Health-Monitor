# Use a lightweight Python image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file (if you have one)
# If you only use standard libraries, you can skip the pip install line
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true

# Copy the script and the example config
COPY ver2_mail.py .
COPY df_h_mail.json.example ./df_h_mail.json

# Command to run the script
CMD ["python", "ver2_mail.py"]
