import streamlit as st
import requests
import json

# Ganti dengan URL webhook PRODUKSI n8n Anda.
# URL webhook-test (seperti yang Anda gunakan sebelumnya) hanya berfungsi saat mendengarkan event tes di n8n.
N8N_WEBHOOK_URL = "https://anahdraw.app.n8n.cloud/webhook-test/3daa2655-3333-4c34-87a4-7eb5e653af9d" 

st.set_page_config(page_title="Demo n8n dengan Output", layout="centered")

st.title("Demo n8n + Streamlit dengan Output")
st.write("Masukkan nama barang di bawah untuk mengirim data ke n8n dan melihat hasilnya.")

# Inisialisasi session_state untuk menyimpan respons dari n8n.
if 'n8n_response' not in st.session_state:
    st.session_state['n8n_response'] = None

with st.form(key='barang_form'):
    barang = st.text_input("Nama Barang")
    submit_button = st.form_submit_button(label='Kirim ke n8n')

if submit_button:
    if barang:
        # Siapkan payload untuk dikirim ke n8n
        payload = {
            "barang": barang,
        }

        try:
            # Gunakan st.spinner untuk memberikan umpan balik visual saat proses berjalan
            with st.spinner("Mengirim data ke n8n..."):
                response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=30)
            
            # Periksa kode status respons
            if response.status_code == 200:
                st.success("Webhook berhasil dikirim! Menerima respons dari n8n.")
                # Ambil respons dalam bentuk JSON dan simpan ke session_state.
                # Metode .json() akan mengurai konten JSON secara otomatis.
                st.session_state['n8n_response'] = response.json()
            else:
                st.error(f"Gagal mengirim webhook. Kode status: {response.status_code}")
                st.session_state['n8n_response'] = None

        except requests.exceptions.RequestException as e:
            st.error(f"Terjadi kesalahan saat menghubungi n8n: {e}")
            st.session_state['n8n_response'] = None
    else:
        st.warning("Silakan masukkan nama barang.")

# Menampilkan output sebagai teks biasa
if st.session_state['n8n_response']:
    st.subheader("Output dari n8n:")
    
    response_data = st.session_state['n8n_response']
    
    # Periksa apakah respons adalah daftar dan memiliki elemen pertama
    if isinstance(response_data, list) and len(response_data) > 0:
        # Akses objek pertama dalam daftar
        first_item = response_data[0]
        
        # Periksa apakah kunci 'output' ada di objek pertama
        if 'output' in first_item:
            output_text = first_item['output']
            st.write(f"**Hasil:** {output_text}")
        else:
            st.warning("Kunci 'output' tidak ditemukan dalam respons n8n.")
    else:
        st.warning("Respons n8n tidak dalam format yang diharapkan.")
