# LLM4Quality API

## Overview

The LLM4Quality API is designed to analyze and classify verbatims to improve the quality of care in hospitals. It provides endpoints for creating, managing, and tracking the status of verbatims in real-time.

## Features

- **Verbatims Management**: Create, retrieve, update, and delete verbatims.
- **Real-time Status Tracking**: Track the status of verbatims in real-time using WebSockets.
- **Classification and Analysis**: Execute a natural language processing pipeline to classify and analyze verbatims.

## Requirements

- Python 3.11
- Docker
- Docker Compose

## Installation

1. **Clone the repository**:
    ```sh
    git clone https://github.com/your-repo/LLM4Quality-APP-back.git
    cd LLM4Quality-APP-back
    ```

2. **Set up environment variables**:
    Copy the `.env.sample` to `.env` and fill in the required values.
    ```sh
    cp .env.sample .env
    ```

3. **Build and run the Docker containers**:
    ```sh
    docker-compose up --build
    ```
    
## Usage

### Running the API

The API will be available at `http://localhost:8080`.

### API Documentation

The API documentation is available at `http://localhost:8080/docs`.

### Running Tests

To run the tests, use the following command:
```sh
pytest
```

## Project Structure

- **`llm4quality_api/`**: Contains the main application code.
  - **`app.py`**: Entry point for the FastAPI application.
  - **`auth.py`**: Handles authentication using Azure AD.
  - **`config/`**: Configuration files.
  - **`controllers/`**: Controllers for handling business logic.
  - **`db/`**: Database connection and management.
  - **`models/`**: Pydantic models for data validation.
  - **`routes/`**: API routes.
  - **`services/`**: Service layer for handling complex operations.
  - **`tasks/`**: Background tasks and worker responses.
  - **`utils/`**: Utility functions and classes.

- **`tests/`**: Contains test cases for the application.
- **`docker-compose.yml`**: Docker Compose configuration.
- **`Dockerfile`**: Dockerfile for building the API service.
- **`pyproject.toml`**: Project dependencies and configuration.


## License

This project is licensed under the MIT License.

## Contact

For any inquiries, please contact:
- Xavier Corbier: [xavier.corbier@umontpellier.fr](mailto:xavier.corbier@umontpellier.fr)
- Romain Mezghenna: [romain24.mezghenna01@gmail.com](mailto:romain24.mezghenna01@gmail.com)
- Lilian Monnereau: [lilian.monnereau@gmail.com](mailto:lilian.monnereau@gmail.com)