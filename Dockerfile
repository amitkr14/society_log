# 1. Start with a lightweight Linux machine pre-installed with Python
FROM python:3.12-slim

# 2. Prevent Python from writing .pyc files and force output to terminal
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Create a folder inside the container called /app
WORKDIR /app

# 4. Copy your requirements file and install the packages
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy all your project files into the container
COPY . /app/