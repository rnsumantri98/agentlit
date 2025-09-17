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

# Menampilkan output di bawah formulir jika ada respons di session_state
if st.session_state['n8n_response']:
    st.subheader("Output dari n8n:")
    # st.json() sangat berguna untuk menampilkan respons JSON yang terstruktur dan mudah dibaca.
    st.json(st.session_state['n8n_response'])
    
    # Contoh cara mengambil data spesifik dari respons JSON
    response_data = st.session_state['n8n_response']
    if 'pesan' in response_data:
        st.info(f"Pesan n8n: {response_data['pesan']}")
    if 'barang_yang_diminta' in response_data:
        st.write(f"Barang yang diproses: **{response_data['barang_yang_diminta']}*
