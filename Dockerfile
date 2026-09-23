# 1. Use the official lightweight Python image
FROM python:3.11-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy only the requirements file first (this caches dependencies to speed up builds)
COPY requirements.txt .

# 4. Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your application code into the container
COPY . .

# 6. Expose the port your app runs on
EXPOSE 8080

# 7. Start the application using Gunicorn (production server)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]