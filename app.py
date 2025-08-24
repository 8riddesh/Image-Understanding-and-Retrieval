import streamlit as st
import analysis_answer as app
import retrive
import os

# Create a temporary directory for uploaded files if it doesn't exist
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def reset_session():
    st.session_state.clear()
    st.rerun()

st.title("Interactive Image Q&A Bot")
st.sidebar.title("App Controls")

if st.sidebar.button("Reset Session"):
    reset_session()

if "image_url" not in st.session_state:
    st.session_state.image_url = ""
if "image_analysis" not in st.session_state:
    st.session_state.image_analysis = ""
if "messages" not in st.session_state:
    st.session_state.messages = []
if "is_analyzed" not in st.session_state:
    st.session_state.is_analyzed = False


uploaded_file = st.file_uploader("Or upload an image file (JPG, PNG, PDF):", type=["jpg", "jpeg", "png", "pdf"])

if uploaded_file is not None and not st.session_state.is_analyzed:
    file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.session_state.clear()
    st.session_state.image_url = file_path
    st.session_state.messages = []
    
    with st.spinner("Performing one-time analysis of the uploaded image..."):
        final_url, analysis = app.run_full_analysis_pipeline(image_query="Uploaded File", file_path=file_path)
    
    if analysis:
        st.session_state.image_url = final_url
        st.session_state.image_analysis = analysis
        st.session_state.is_analyzed = True
        st.success("Image analysis complete and saved to Google Sheet.")
        st.session_state.messages.append({"role": "assistant", "content": "Hello! I have analyzed your uploaded image and am ready to answer your questions about it."})
        st.rerun()
    else:
        st.error("Failed to analyze the uploaded image.")
        st.session_state.clear()
        st.rerun()

if not st.session_state.image_url:
    image_query = st.text_input("Enter a query to find an image:")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Search for Image"):
            if image_query:
                with st.spinner("Checking Google Sheet for existing analysis..."):
                    existing_analysis = retrive.get_analysis_by_query(image_query)
                    if existing_analysis:
                        st.session_state.image_url = existing_analysis.get('Image URL')
                        st.session_state.image_analysis = existing_analysis.get('Analysis')
                        st.success("Found existing analysis in Google Sheet! Skipping search and analysis.")
                        st.session_state.messages.append({"role": "assistant", "content": "Hello! I have found an image and am ready to answer your questions about it."})
                        st.session_state.is_analyzed = True
                        st.rerun()
                    else:
                        st.info("No existing analysis found. Performing web search and analysis...")
                        
                        final_url, analysis = app.run_full_analysis_pipeline(image_query=image_query)
                        
                        if final_url:
                            st.session_state.image_url = final_url
                            st.session_state.image_analysis = analysis
                            st.session_state.is_analyzed = True
                            st.success(f"Image found! URL: {final_url}")
                            st.success("Image analysis complete and saved to Google Sheet.")
                            st.session_state.messages.append({"role": "assistant", "content": "Hello! I have found an image and am ready to answer your questions about it."})
                            st.rerun()
                        else:
                            st.error("Failed to find a compatible image after searching. Please try a different query.")
    
    with col2:
        if st.button("Retrieve Image from Cache"):
            if image_query:
                with st.spinner("Searching for a matching image in the cache..."):
                    retrieved_data = retrive.semantic_search_in_cache(image_query)
                    if retrieved_data!=None:
                        st.session_state.image_url = retrieved_data.get('Image URL')
                        st.session_state.image_analysis = retrieved_data.get('Analysis')
                        st.success("Found a matching image in the cache!")
                        st.session_state.messages.append({"role": "assistant", "content": "Hello! I have retrieved an image from the cache based on your query. You can now ask questions about it."})
                        st.session_state.is_analyzed = True
                        st.rerun()
                    else:
                        st.warning("No matching image found in the cache. Please use 'Search for Image' to find a new one.")
            else:
                st.warning("Please enter a query to search the cache.")
else:
    st.image(st.session_state.image_url, caption="Found Image", use_container_width=True)
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask a question about the image..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            answer = app.run_rag_pipeline(prompt, st.session_state.image_analysis, st.session_state.image_url)
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
