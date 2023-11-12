import openai
import streamlit as st
import jsonlines
import subprocess
import os
import requests
from dotenv import load_dotenv

# Check for .env and load if present
if os.path.exists('.env'):
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ORG_ID = os.getenv("ORG_ID")

else:
    OPENAI_API_KEY = None
    ORG_ID = None

st.header('Fine-tune OpenAI & test the responses')

# If OPENAI_API_KEY is not found, provide instructions and input to save to .env
if not OPENAI_API_KEY:
    st.warning("Your OpenAI API key is not found in a .env file.")
    st.write("Please provide your OpenAI API key below to save it securely in a .env file.")
    user_api_key = st.text_input('Enter your OpenAI API Key:')
    if st.button('Save API Key'):
        with open('.env', 'w') as env_file:
            env_file.write(f"OPENAI_API_KEY='{user_api_key}'")
        st.success('Your API Key has been saved to .env file!')
        OPENAI_API_KEY = user_api_key
if not ORG_ID:
    st.warning("Your ORG_ID is not found in a .env file.")
    st.write("Please provide your ORG_ID below to save it securely in a .env file.")
    user_org_id = st.text_input('Enter your ORG_ID:')
    if st.button('Save ORG_ID'):
        with open('.env', 'a') as env_file:  # Appending to the .env file
            env_file.write(f"\nORG_ID='{user_org_id}'")  # Using double quotes for the f-string and single quotes for the value
        st.success('Your ORG_ID has been saved to .env file!')
        ORG_ID = user_org_id

# Toggle visibility of the Help section using session state
if 'show_help' not in st.session_state:
    st.session_state.show_help = False

if st.button('Help'):
    st.session_state.show_help = not st.session_state.show_help

if st.session_state.show_help:
    st.write(
        """
        To train the model please use 10 to 100 examples or more.  
        1. **User Prompts**: Enter a question under the label "Enter your question? Human:".
        2. **AI Response**: Provide your ideal AI-generated response.
        3. **Custom System Message**: Add a custom system message or stick with the default message "You are a helpful and friendly assistant.".
        4. **Data Saving**: Upon pressing the "Accept Inputs" button, the provided data gets formatted and appended to an `output.jsonl` file.
        5. **TRAINING_FILE_ID Input**: Users can input their TRAINING_FILE_ID required for fine-tuning. You will receive an email from OpenAI when the model has been trained.
        5. **Upload file to OpenAI for fine-tunning**
        6. **Send for Fine-Tuning**: A button to send the `output.jsonl` file to OpenAI for fine-tuning.
        7. **Chat Window**: Test the fine-tuned model by sending messages and viewing the model's response.
          
          
        ### Validate your data -  Details from OpenAI
        - **Data Inspection**: The script initially loads the dataset from `output.jsonl` and prints the number of examples and the first example to provide an overview.
        - **Format Error Checks**: The script checks for various formatting issues such as:
        - Incorrect data types
        - Missing message lists
        - Unrecognized message keys
        - Missing content
        - Unrecognized roles in messages
        - Absence of an assistant's message
        - **Token Count**: It calculates the number of tokens for each message and provides distribution statistics such as:
        - Range (Min and Max)
        - Average (Mean)
        - Middle Value (Median)
        - 5th Percentile
        - 95th Percentile

        ##  Understanding OpenAI's Statistics  

        - **Number of Messages per Example Distribution**: Provides statistics about the number of messages in each example.
        - **Total Tokens per Example Distribution**: Indicates the total number of tokens in each example.
        - **Assistant Tokens per Example Distribution**: Pertains to the number of tokens in the assistant's messages within each example.
           For each distribution, the following statistics are provided:
        - **Range**: The smallest and largest values.
        - **Average (Mean)**: The average value.
        - **Middle Value (Median)**: The middle value when sorted.
        - **5th Percentile**: 5% of the data lies below this value.
        - **95th Percentile**: 95% of the data lies below this value.
        """
    )

# Get prompts from the user
system_message_default = 'You are a helpful and friendly assistant.'
system_message = st.text_area('Enter your custom system message:', value=system_message_default)
prompt_text = st.text_area('Enter your question? Human:', height=200)
ideal_generated_text = st.text_area('Enter your ideal AI generated response:', height=200)

if st.button('Append to output.jsonl'):
    # Format and save data to jsonl
    data = {
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt_text},
            {"role": "assistant", "content": ideal_generated_text}
        ]
    }
    with jsonlines.open('output.jsonl', mode='a') as writer:
        writer.write(data)
    st.success('Data has been appended to JSONL file!')

if st.button('Validate your data', key="check_data_btn_2"):
    result = subprocess.run(['python', 'openaicheck.py'], capture_output=True, text=True)
    st.write(result.stdout)

# Initialize session state
if 'file_id' not in st.session_state:
    st.session_state.file_id = ""

# Upload to OpenAI
uploaded_file = st.file_uploader("Choose an output.jsonl file", type="jsonl")
if uploaded_file:
    if st.button('Upload to OpenAI'):
        with open("uploaded_output.jsonl", "wb") as f:
            f.write(uploaded_file.getvalue())
        
        url = "https://api.openai.com/v1/files"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        }
        files = {
            "purpose": (None, "fine-tune"),
            "file": ("uploaded_output.jsonl", open("uploaded_output.jsonl", "rb")),
        }
        
        response = requests.post(url, headers=headers, files=files)
        response_dict = response.json()
        st.session_state.file_id = response_dict["id"]
        if response.status_code == 200:
            st.success("File successfully uploaded to OpenAI!")
        else:
            st.error("Failed to upload file. Please check the API key and file format.")

# Input for TRAINING_FILE_ID
train_id =  value=st.session_state.file_id

if st.button('Create fine-tuning job'):
    if not train_id:
        st.warning("Please enter a TRAINING_FILE_ID before sending for fine tuning.")
    else:
        # Send the output.jsonl for fine tuning
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        data = {
            "training_file": train_id,
            "model": "gpt-3.5-turbo-0613"
        }
        response = requests.post("https://api.openai.com/v1/fine_tuning/jobs", headers=headers, json=data)
        st.write(response.json())

# Set OpenAI API key directly if available
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    api_key_input = st.sidebar.text_input('Enter your OpenAI API Key:', key='api_key_input_unique')
    if api_key_input:
        openai.api_key = api_key_input

# Additional features for fine-tuning jobs and models
# Create a sidebar for additional operations
st.sidebar.title("Additional Operations")

# Input for Fine-Tuning Model ID
if 'ft_model_id' not in st.session_state:
    st.session_state.ft_model_id = ""

ft_model_id_raw = st.sidebar.text_input("Enter Fine-Tuning Model ID:", value=st.session_state.ft_model_id)
ft_model_id = ft_model_id_raw.strip("\"")
st.session_state.ft_model_id = ft_model_id

# Option to list 10 fine-tuning jobs
if st.sidebar.button('List 10 Fine-Tuning Jobs', key='ListJobsButton'):
    try:
        fine_tuning_jobs = openai.FineTuningJob.list(limit=10)
        st.write("### Fine-Tuning Jobs (Limited to 10)")
        st.write(fine_tuning_jobs)
    except Exception as e:
        st.write(f"Error: {e}")

# Button to trigger the API call and get the response
if st.sidebar.button('Use the OpenAI Playground for test', key='GetResponseButton'):
    try:
        st.sidebar.markdown("[Go to OpenAI Playground](https://platform.openai.com/playground)")
    except Exception as e:
        st.sidebar.write(f"Error: {e}")

# Retrieve the state of a fine-tune
if st.sidebar.button('Retrieve Fine-Tune State', key='RetrieveFineTuneButton'):
    try:
        fine_tune_state = openai.FineTuningJob.retrieve(st.session_state.ft_model_id)
        st.write("### Fine-Tune State")
        st.write(fine_tune_state)
    except Exception as e:
        st.write(f"Error: {e}")

# Cancel a job
if st.sidebar.button('Cancel Fine-Tune Job', key='CancelFineTuneButton'):
    try:
        openai.FineTuningJob.cancel(st.session_state.ft_model_id)
        st.sidebar.write("### Job Cancelled")
    except Exception as e:
        st.sidebar.write(f"Error: {e}")

# List events from a fine-tuning job
if st.sidebar.button('List Fine-Tune Events', key='ListFineTuneEventsButton'):
    try:
        fine_tune_events = openai.FineTuningJob.list_events(id=st.session_state.ft_model_id, limit=10)
        st.write("### Fine-Tune Events (Limited to 10)")
        st.write(fine_tune_events)
    except Exception as e:
        st.sidebar.write(f"Error: {e}")

# Delete a fine-tuned model
if st.sidebar.button('Delete Fine-Tuned Model', key='DeleteFineTunedModelButton'):
    try:
        openai.Model.delete(st.session_state.ft_model_id)
        st.sidebar.write("### Fine-Tuned Model Deleted")
    except Exception as e:
        st.sidebar.write(f"Error: {e}")
