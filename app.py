import streamlit as st
import google.generativeai as genai
import json
from PyPDF2 import PdfReader
from PIL import Image

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="MyHealth Insights", page_icon="🩺", layout="centered")

# --- CUSTOM CSS FOR VISUAL APPEAL ---
st.markdown("""
    <style>
    .main-header { font-size: 2.5rem; font-weight: bold; color: #1E3A8A; text-align: center; }
    .sub-header { font-size: 1.2rem; color: #4B5563; text-align: center; margin-bottom: 2rem; }
    .card { padding: 1.5rem; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 1rem; }
    </style>
""", unsafe_allow_html=True)

# --- INITIALIZE API ---
try:
    # This securely fetches the key from the Streamlit Cloud settings
    api_key = st.secrets["API_KEY"]
    genai.configure(api_key=api_key)
    
    # Using 'latest' helps prevent 404 model errors on Streamlit Cloud
    model = genai.GenerativeModel('gemini-1.5-flash') 
except KeyError:
    st.error("System Error: API Key not found in Secrets. Please configure the app settings.")
    st.stop()

# --- HELPER FUNCTIONS ---
def extract_text_from_pdf(file):
    pdf_reader = PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def analyze_report(content, file_type="text"):
    prompt = """
    You are an expert medical data assistant. Analyze the provided medical report.
    Identify all biomarkers (e.g., Vitamin D, Ferritin, Hemoglobin).
    For each biomarker, extract:
    1. The Name
    2. The Patient's Result Value
    3. The Normal Reference Range stated in the report
    4. Status: Determine if the result is "Low", "Normal", or "High" based ONLY on the provided range.
    
    Output the data STRICTLY as a JSON list of dictionaries. Do not include markdown formatting or extra text.
    Example format:
    [
      {"biomarker": "Vitamin B12", "value": "150", "range": "200-900", "status": "Low"},
      {"biomarker": "Iron", "value": "85", "range": "60-170", "status": "Normal"}
    ]
    """
    
    try:
        if file_type == "text":
            response = model.generate_content([prompt, content])
        else: # Image
            response = model.generate_content([prompt, content])
            
        # Clean up the response to ensure it's pure JSON
        cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_text)
    except Exception as e:
        st.error(f"Error analyzing report: {e}")
        return None

# --- MAIN UI ---
st.markdown("<div class='main-header'>🩺 MyHealth Insights</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>Upload your medical report to instantly see what needs your attention.</div>", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload Report (PDF, JPG, PNG)", type=["pdf", "jpg", "jpeg", "png"])

if uploaded_file and api_key:
    if st.button("Analyze My Report", type="primary", use_container_width=True):
        with st.spinner("Analyzing your report securely..."):
            
            # 1. Process File
            if uploaded_file.type == "application/pdf":
                content = extract_text_from_pdf(uploaded_file)
                data = analyze_report(content, "text")
            else:
                image = Image.open(uploaded_file)
                data = analyze_report(image, "image")
            
            # 2. Display Results Visually
            if data:
                st.markdown("---")
                st.subheader("Actionable Insights")
                
                # Filter for items outside normal range
                action_items = [item for item in data if item.get('status') != 'Normal']
                normal_items = [item for item in data if item.get('status') == 'Normal']
                
                if action_items:
                    st.error("🚨 **Areas Requiring Attention:**")
                    for item in action_items:
                        with st.container():
                            col1, col2, col3 = st.columns([2, 1, 1])
                            col1.markdown(f"**{item['biomarker']}**")
                            col2.metric("Your Result", item['value'])
                            col3.metric("Safe Range", item['range'])
                            st.write(f"*Status:* **{item['status']}**")
                            st.divider()
                else:
                    st.success("🎉 All parameters found in the report are within the normal safe ranges!")
                
                # Optional: Show normal items folded away so it doesn't clutter the screen
                if normal_items:
                    with st.expander("View Normal Parameters"):
                        for item in normal_items:
                            st.write(f"✅ **{item['biomarker']}**: {item['value']} (Range: {item['range']})")
                
                st.caption("Disclaimer: This tool is for informational purposes only and is powered by AI. It is not a substitute for professional medical advice, diagnosis, or treatment. Always consult with your doctor regarding your test results.")
