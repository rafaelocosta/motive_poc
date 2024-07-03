# Financial Advisor Chatbot

## Overview

This project involves designing a chatbot for a financial advisor. The chatbot interacts with a mock database containing a list of clients, their current holdings, and associated model portfolios. Advisors can ask questions in natural language and receive accurate, verifiable answers. The focus is on creating a detailed system design, including measurements, KPIs, and best practices in data handling, with an optional quick implementation to validate the proposal.

## Getting Started

### Prerequisites

Ensure you have the following installed:

- Docker
- Docker Compose
- OpenAI API Key
- GROQ API Key (Optional)

### Setup

1. Clone the repository:
    ```bash
    git clone https://github.com/rafaelocosta/motive_poc.git
    cd motive_poc
    ```

2. Create a `.env` file in the root directory with your OpenAI or GROQ API keys:
    ```dotenv
    OPENAI_API_KEY=your_openai_api_key
    GROQ_API_KEY=your_groq_api_key
    ```

3. Build and run the Docker containers:
    ```bash
    docker-compose build
    docker-compose up
    ```

## Usage

To interact with the chatbot, use the following `curl` command:

```bash
curl --location 'localhost:8081/ask/' \
--header 'Content-Type: application/json' \
--data '{
    "question": "list the symbol, name and current price for ETF Sector",
    "chat_context": "context_1"
}'
