def main():
st.set_page_config(page_title="Inventory Checker (Streamlit + n8n Webhook)", layout="wide")
ensure_server()


st.title("🔗 Inventory Checker — Streamlit + FastAPI Webhook")
st.caption("Webhook endpoint live at: http://localhost:8000/webhook/check_item")


with st.expander("Webhook usage (for n8n)", expanded=False):
st.markdown(
"""
**HTTP**: `POST /webhook/check_item`


**Headers**:
`Content-Type: application/json`
`X-API-Key: <your_api_key>` *(omit if API_KEY not set)*


**Body (JSON)**:
```json
{ "sku": "SKU-ANL-CH-200", "location": "GUDANG_PUSAT" }
```


**Response (JSON)**:
```json
{
"found": true,
"results": [
{
"SKU": "SKU-ANL-CH-200",
"product_name": "Anlene Chocolate",
"variant": "200g",
"uom": "pcs",
"location": "GUDANG_PUSAT",
"qty": 7,
"low_stock_threshold": 5,
"eta_restock": "2025-09-22",
"low_stock": false
}
]
}
```


To refresh data cache (from CSV/Sheet):
`POST /webhook/refresh_cache`
"""
)


st.subheader("🔍 Quick Check (manual)")
c1, c2, c3 = st.columns([2,2,1])
sku = c1.text_input("SKU", placeholder="e.g., SKU-ANL-CH-200")
location = c2.text_input("Location (optional)", placeholder="e.g., GUDANG_PUSAT / TOKO_BEKASI")
if c3.button("Check"):
df = query_inventory(sku, location if location else None)
if df.empty:
st.error("Item not found")
else:
# highlight low stock
def _hl(row):
low = int(row["Qty"]) <= int(row["Low Stock Threshold"]) if pd.notna(row["Low Stock Threshold"]) else False
style = ['background-color: #ffd6d6' if low else '' for _ in row]
return style
st.dataframe(df.style.apply(_hl, axis=1), use_container_width=True)


st.subheader("📦 Current Inventory Cache")
with engine.connect() as conn:
df_all = pd.read_sql("SELECT * FROM inventory", conn)
st.dataframe(df_all, use_container_width=True)


st.sidebar.header("⚙️ Settings")
if st.sidebar.button("Refresh cache now"):
df = refresh_inventory_cache()
st.sidebar.success(f"Refreshed: {df.shape[0]} rows")




if __name__ == "__main__":
main()
