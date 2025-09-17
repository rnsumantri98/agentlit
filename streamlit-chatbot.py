import streamlit as st
import requests

# Replace with your actual n8n webhook URL
N8N_WEBHOOK_URL = "https://anahdraw.app.n8n.cloud/webhook-test/3daa2655-3333-4c34-87a4-7eb5e653af9d"

st.title("Simple n8n + Streamlit Demo")
st.write("Enter your details below to send a webhook to an n8n workflow.")

with st.form(key='my_form'):
    barang = st.text_input("Nama Barang")
    submit_button = st.form_submit_button(label='Submit')

if submit_button:
    if name and email:
        # Prepare the payload to send to n8n
        payload = {
            "barang": barang,
        }

        try:
            # Send the POST request to the n8n webhook
            response = requests.post(N8N_WEBHOOK_URL, json=payload)

            if response.status_code == 200:
                st.success(f"Webhook sent successfully! n8n responded: {response.text}")
                # You can see the webhook execution in your n8n instance
            else:
                st.error(f"Failed to send webhook. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            st.error(f"An error occurred: {e}")
    else:
        st.warning("masukkan nama barang.")
