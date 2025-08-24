import os
import requests
import time
from typing import TypedDict, List, Dict, Optional
from dotenv import load_dotenv
from io import BytesIO
from PIL import Image
import base64

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
import retrive as db_logic

# A simple OCR service API for text detection
OCR_API_URL = "https://api.ocr.space/parse/image"

# Ensure your API keys are loaded from the .env file.
load_dotenv()
API_KEY = os.getenv('API_KEY')
SEARCH_ENGINE_ID = os.getenv('SEARCH_ENGINE_ID')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
OCR_API_KEY = os.getenv('OCR_API_KEY')
url="https://www.googleapis.com/customsearch/v1"
# Initialize the Groq and Gemini LLMs
llm_groq = ChatGroq(temperature=0, groq_api_key=GROQ_API_KEY, model_name="qwen/qwen3-32b")
llm_gemini = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash", 
    google_api_key=API_KEY,
    temperature=0.7,
    max_output_tokens=1024,
)
llm_gemini_vision = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=API_KEY,
    temperature=0.7,
)

def get_image_urls(prompt: str) -> List[str]:
    """
    Fetches a list of image links from Google Custom Search API based on the prompt.
    """
    if not API_KEY or not SEARCH_ENGINE_ID:
        print("Error: API key or Search Engine ID not found.")
        return []

    params = {
        'q': prompt,
        'key': API_KEY,
        'cx': SEARCH_ENGINE_ID,
        'searchType': 'image',
        'num': 10,
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        response_data = response.json().get('items', [])
        
        if response_data:
            return [item['link'] for item in response_data]
        else:
            print("No images found for the query.")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching images: {e}")
        return []

def run_ocr_tool(image_path_or_url: str) -> str:
    """
    Performs OCR on an image URL or local file path using a third-party API.
    """
    if not OCR_API_KEY:
        return "OCR API key not found."

    payload = {'isOverlayRequired': False, 'apikey': OCR_API_KEY}
    files = {}

    if image_path_or_url.startswith('http'):
        payload['url'] = image_path_or_url
    else:
        try:
            files['file'] = open(image_path_or_url, 'rb')
        except FileNotFoundError:
            return "File not found."

    try:
        response = requests.post(OCR_API_URL, data=payload, files=files)
        response.raise_for_status()
        result = response.json()
        
        if result.get('ParsedResults'):
            text = result['ParsedResults'][0]['ParsedText']
            return text
        else:
            return ""
    except Exception as e:
        return f"OCR Error: {e}"
    finally:
        if 'file' in files:
            files['file'].close()


def check_for_text(image_path_or_url: str) -> str:
    """
    Checks if an image contains text by using the web-based OCR tool.
    Returns the extracted text if found, otherwise an empty string.
    """
    extracted_text = run_ocr_tool(image_path_or_url)
    return extracted_text


def analyze_image_once(image_path_or_url: str) -> str:
    """
    Performs a single, comprehensive analysis of an image using Gemini.
    """
    print("Performing one-time analysis of the image with Gemini...")
    full_prompt = "Provide a detailed, structured analysis of this image, including any text and key objects."
    
    if image_path_or_url.startswith('http'):
        image_content = {"type": "image_url", "image_url": image_path_or_url}
    else:
        try:
            with open(image_path_or_url, "rb") as f:
                image_bytes = f.read()
            image_content = {
                "type": "image_url", 
                "image_url": f"data:image/{image_path_or_url.split('.')[-1]};base64,{base64.b64encode(image_bytes).decode('utf-8')}"
            }
        except FileNotFoundError:
            return "File not found."

    response = llm_gemini_vision.invoke(
        [
            HumanMessage(
                content=[
                    {"type": "text", "text": full_prompt},
                    image_content,
                ]
            )
        ]
    )
    return response.content

def run_rag_pipeline(question: str, image_analysis: str, image_url: str) -> str:
    """
    Runs the RAG pipeline to answer the user's question.
    It uses the small LLM first and falls back to Gemini if needed.
    """
    rag_prompt = f"Using the following image analysis: '{image_analysis}', answer this question: {question}"
    
    answer = ""
    print("Attempting to get response from Groq model...")
    
    if not GROQ_API_KEY:
        print("Groq API key not found. Forcing fallback to Gemini.")
    else:
        try:
            response_groq = llm_groq.invoke([HumanMessage(content=rag_prompt)])
            answer = response_groq.content
            print(f"Groq raw response: {answer}")
            if not answer.strip() or "i cannot answer that based on the provided context" in answer.lower():
                answer = "" 
        except Exception as e:
            print(f"Error with Groq API: {e}. Forcing fallback to Gemini.")
            answer = ""

    if not answer.strip():
        print("Falling back to Gemini model.")
        response_gemini = llm_gemini_vision.invoke(
            [
                HumanMessage(
                    content=[
                        {"type": "text", "text": question},
                        {"type": "image_url", "image_url": image_url},
                    ]
                )
            ]
        )
        answer = response_gemini.content
    
    return answer

def run_full_analysis_pipeline(image_query: str, file_path: Optional[str] = None):
    """
    Orchestrates the image search, analysis, and caching.
    """
    if file_path:
        final_url = file_path
        print(f"Analyzing local file: {final_url}")
    else:
        print("No existing analysis found. Performing web search and analysis...")
        image_urls = get_image_urls(prompt=image_query)
        if not image_urls:
            return None, None
            
        final_url = ""
        for url_to_check in image_urls:
            try:
                # Check for a valid image by performing OCR first
                extracted_text = check_for_text(url_to_check)
                if extracted_text and len(extracted_text.strip()) > 10:
                    final_url = url_to_check
                    analysis = extracted_text
                    print(f"OCR found text. Using extracted text as analysis.")
                    break
                else:
                    # If no text is found, check if Gemini can process it
                    llm_gemini_vision.invoke([HumanMessage(content=[{"type": "text", "text": "Describe this image."}, {"type": "image_url", "image_url": url_to_check}])])
                    final_url = url_to_check
                    analysis = analyze_image_once(final_url)
                    print(f"Found a compatible URL for Gemini and performed analysis: {final_url}")
                    break
            except Exception as e:
                print(f"Skipping incompatible URL: {url_to_check}. Reason: {e}")
                continue

        if not final_url:
            print("Failed to find a compatible image after trying all URLs.")
            return None, None
    
    # Analyze the image (either from URL or local file)
    analysis = ""
    if file_path:
        analysis_source = file_path
    else:
        analysis_source = final_url

    extracted_text = check_for_text(analysis_source)
    if extracted_text and len(extracted_text.strip()) > 10:
        analysis = extracted_text
        print(f"OCR found text. Using extracted text as analysis.")
    else:
        print("Image contains no text. Performing general Gemini analysis...")
        analysis = analyze_image_once(analysis_source)

    db_logic.save_image_analysis(image_query if not file_path else "Uploaded File", final_url, analysis)
    return final_url, analysis

