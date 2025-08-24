# Interactive Image Q&A Bot

This project is an interactive web application that allows users to perform image analysis and ask questions about an image using a hybrid RAG (Retrieval-Augmented Generation) pipeline. The application can either search for an image based on a user's natural language query or analyze an image uploaded directly by the user.

## ✨ Key Features

- **Intelligent Image Retrieval:** Search for images online using a natural language prompt or retrieve images from a cache.
- **Direct Image Upload:** Analyze local images by uploading them directly through the web interface.
- **Optimized Analysis Pipeline:** Uses a dedicated OCR tool to extract text from images, and a smart LLM fallback for comprehensive analysis when needed.
- **Efficient RAG Q&A:** Utilizes a small, fast LLM (Groq) for answering questions based on image analysis, with a more powerful VLM (Gemini) as a fallback for complex queries.
- **Data Persistence:** Stores all image analyses in a Google Sheet for caching, improving performance and reducing API costs for repeat queries.
- **User-Friendly Interface:** Features a clean, intuitive chat interface built with Streamlit.

## ⚙️ Project Structure

The project is modular and organized into three main files:

- **main.py**: The Streamlit frontend, handling the user interface and orchestrating backend logic calls.
- **analysis_answer.py**: The core backend logic for image search, analysis, OCR, and the RAG pipeline.
- **retrive.py**: A dedicated library for managing data storage and retrieval from the Google Sheet.

## 🚀 Setup and Installation

### Prerequisites

- Python 3.9 or higher
- A Google Cloud Project with the Custom Search API enabled
- An API key from Google AI Studio
- A Groq API key
- An API key for the ocr.space service
- A Google Cloud Service Account with access to Google Sheets

### Configuration

1. **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <project_directory>
    ```

2. **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3. **Set up your `.env` file:**
    Create a `.env` file in your project's root directory and add the following variables:
    ```
    API_KEY="your_google_api_key"
    SEARCH_ENGINE_ID="your_google_custom_search_id"
    GROQ_API_KEY="your_groq_api_key"
    OCR_API_KEY="your_ocr_space_api_key"
    GOOGLE_SHEETS_CREDENTIALS_PATH="path/to/your/service_account_key.json"
    GOOGLE_SHEET_URL="your_google_sheet_url"
    ```

4. **Set up Google Sheets:**
    - Create a new Google Sheet.
    - Share the sheet with your service account's email address (found in the JSON key file), granting Editor access.
    - Copy the sheet's URL and add it to your `.env` file.

### Running the Application

To start the application, navigate to the project directory and run the main.py file using Streamlit:

```bash
streamlit run main.py
```

The application will open in your default web browser.

---

