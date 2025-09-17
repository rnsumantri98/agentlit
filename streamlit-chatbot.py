import streamlit as st
import requests

st.title("n8n-Streamlit Demo")

user_input = st.text_input("Enter your message:")

if st.button("Send to n8n"):
        if user_input:
            # Prepare the data to send to n8n
            payload = {"message": user_input}
            # Replace with your actual n8n webhook URL
            n8n_webhook_url = "YOUR_N8N_WEBHOOK_URL"

            # Send the data to n8n
            try:
                response = requests.post(n8n_webhook_url, json=payload)
                response.raise_for_status()  # Raise an exception for bad status codes
                n8n_response = response.json()
                st.success("Message sent to n8n successfully!")
                st.write("Response from n8n:", n8n_response)
            except requests.exceptions.RequestException as e:
                st.error(f"Error sending message to n8n: {e}")
        else:
            st.warning("Please enter a message.")
