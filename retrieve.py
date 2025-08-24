import os
import gspread
import re
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
import streamlit as st
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

load_dotenv()
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH')
SPREADSHEET_URL = os.getenv('GOOGLE_SHEET_URL')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# Initialize the Groq LLM for semantic search
llm_groq = ChatGroq(temperature=0, groq_api_key=GROQ_API_KEY, model_name="gemma2-9b-it")

def get_worksheet():
    """
    Connects to the Google Sheet using a service account and returns the worksheet.
    """
    try:
        if not SERVICE_ACCOUNT_FILE or not SPREADSHEET_URL:
            # In a Streamlit app, we use st.error for the UI
            st.error("Please set GOOGLE_SHEETS_CREDENTIALS_PATH and GOOGLE_SHEET_URL in your .env file.")
            return None
        gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
        sh = gc.open_by_url(SPREADSHEET_URL)
        return sh.sheet1
    except Exception as e:
        st.error(f"Error connecting to Google Sheet: {e}")
        return None

def save_image_analysis(image_query: str, image_url: str, analysis: str):
    """
    Saves a single, comprehensive image analysis to the Google Sheet.
    """
    worksheet = get_worksheet()
    if worksheet is None:
        return

    try:
        headers = worksheet.row_values(1)
        if not headers or headers != ['Image Query', 'Image URL', 'Analysis', 'Timestamp']:
            worksheet.clear()
            worksheet.append_row(['Image Query', 'Image URL', 'Analysis', 'Timestamp'])
        
        row_data = [image_query, image_url, analysis, str(datetime.now())]
        worksheet.append_row(row_data)
        st.success("Image analysis saved to Google Sheet.")
    except Exception as e:
        st.error(f"Error saving to Google Sheet: {e}")

def get_analysis_by_query(image_query: str) -> Optional[Dict]:
    """
    Retrieves the comprehensive analysis for a specific image query from the sheet.
    """
    worksheet = get_worksheet()
    if worksheet is None:
        return None
    
    try:
        all_records = worksheet.get_all_records()
        for record in all_records:
            if record.get('Image Query') == image_query:
                return record
        return None
    except Exception as e:
        st.error(f"Error retrieving data from Google Sheet: {e}")
        return None
        
def semantic_search_in_cache(user_prompt: str) -> Optional[Dict]:
    """
    Performs a semantic search for a matching image analysis in the Google Sheet.
    It compares the user's prompt to both the image query and the analysis.
    """
    worksheet = get_worksheet()
    if worksheet is None:
        return None
        
    try:
        records = worksheet.get_all_records()
        if not records:
            return None
            
        # Create a list of all text to search through
        search_texts = [f"Query: {rec['Image Query']}. Analysis: {rec['Analysis']}" for rec in records]
        
        # Use Groq to determine the best match
        # The prompt is now much more concise and direct to get a single number as output.
        prompt = f"""
        Given the following list of items:
        {search_texts}

        Identify the index number (starting from 0) of the item that best matches the user's prompt: "{user_prompt}".
        Respond ONLY with a single integer. Do not add any extra text or explanation.
        If no item is a good match, respond with -1.
        """
        
        response = llm_groq.invoke([HumanMessage(content=prompt)])
        
        # Use regex to extract the index number from the LLM's response
        match = re.search(r'(\d+)', response.content)
        if int(response.content.strip()) == -1:
            return None
        print(response.content,match)
        if match:
            try:
                match_index = int(match.group(1))
            except ValueError:
                print(f"Failed to convert matched string to int: {match.group(1)}")
                return None
        else:
            print(f"LLM did not return an index number. Response: {response.content}")
            return None

        if match_index != -1 and 0 <= match_index < len(records):
            return records[match_index]
            
        return None
        
    except Exception as e:
        st.error(f"Error during semantic search: {e}")
        return None
