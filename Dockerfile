# Use a lightweight Python image
FROM python:3.13-slim

# Set the working directory inside the container
WORKDIR /app

# Install Poetry globally
RUN pip install poetry

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock ./

# Install project dependencies without dev dependencies
RUN poetry install --no-dev

# Copy all project files into the container
COPY . .

# Expose the Flask default port
EXPOSE 5000

# Set the command to run the Flask application
CMD ["poetry", "run", "python", "llm4quality_api/app.py"]