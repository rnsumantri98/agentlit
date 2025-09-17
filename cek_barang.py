import streamlit as st
import requests
import json

# Pastikan menggunakan URL webhook produksi n8n Anda.
# URL di bawah adalah URL uji coba yang tidak akan berfungsi.
N8N_WEBHOOK_URL = "https://anahdraw.app.n8n.cloud/webhook-test/3daa2655-3333-4c34-87a4-7eb5e653af9d"

st.title("Demo n8n + Streamlit dengan Output")
st.write("Masukkan nama barang di bawah untuk mengirim data ke n8n dan melihat hasilnya.")

# Inisialisasi session_state untuk menyimpan respons dari n8n
# Ini akan mencegah aplikasi memanggil n8n lagi setiap kali ada interaksi
if 'n8n_response' not in st.session_state:
    st.session_state['n8n_response'] = None

# Gunakan form untuk mengelompokkan input
with st.form(key='barang_form'):
    barang = st.text_input("Nama Barang", key="input_barang")
    submit_button = st.form_submit_button(label='Kirim ke n8n')

# Proses permintaan hanya ketika tombol submit ditekan
if submit_button:
    if barang:
        # Siapkan payload untuk dikirim ke n8n
        payload = {
            "barang": barang,
        }

        try:
            # Mengirim permintaan POST ke webhook n8n
            # Gunakan st.spinner untuk memberikan umpan balik visual saat proses berjalan
            with st.spinner("Mengirim data ke n8n..."):
                response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=30)
            
            # Periksa kode status respons
            if response.status_code == 200:
                st.success("Webhook berhasil dikirim! Menerima respons dari n8n.")
                # Simpan respons JSON ke session_state
                st.session_state['n8n_response'] = response.json()
            else:
                st.error(f"Gagal mengirim webhook. Kode status: {response.status_code}")
                st.session_state['n8n_response'] = None

        except requests.exceptions.RequestException as e:
            st.error(f"Terjadi kesalahan: {e}")
            st.session_state['n8n_response'] = None
    else:
        st.warning("Silakan masukkan nama barang.")

# Menampilkan output di bawah formulir jika ada respons di session_state
if st.session_state['n8n_response']:
    st.subheader("Output dari n8n:")
    st.json(st.session_state['n8n_response'], expanded=True) # Menampilkan JSON yang dapat dikembangkan

