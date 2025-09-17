# mini_app.py
# Versi sederhana untuk praktik ringan: Streamlit UI + FastAPI webhook
# - Tanpa database
# - Data inventory hardcoded (bisa diganti mudah)
# - Satu endpoint webhook: POST /webhook/check_item
# -------------------------------------------------------
# Cara jalankan:
# pip install streamlit fastapi uvicorn pydantic
# streamlit run mini_app.py
# Webhook lokal:
# POST http://localhost:8000/webhook/check_item
# Body JSON: {"sku": "SKU-ANL-CH-200", "location": "GUDANG_PUSAT"}
# -------------------------------------------------------


import os
import threading
from typing import Optional, List
from datetime import date


import streamlit as st
from pydantic import BaseModel
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
import uvicorn


# ====== Config opsional ======
API_KEY = os.getenv("API_KEY", "") # jika ingin pakai header X-API-Key


# ====== Data contoh (ganti sesuai kebutuhan) ======
INVENTORY = [
{
"SKU": "SKU-ANL-CH-200", "Product Name": "Anlene Chocolate", "Variant": "200g",
"UOM": "pcs", "Location": "GUDANG_PUSAT", "Qty": 7,
"Low Stock Threshold": 5, "ETA Restock": date(2025, 9, 22)
},
{
"SKU": "SKU-ANL-CH-600", "Product Name": "Anlene Chocolate", "Variant": "600g",
"UOM": "pcs", "Location": "GUDANG_PUSAT", "Qty": 15,
"Low Stock Threshold": 5, "ETA Restock": None
},
{
"SKU": "SKU-PS5D-825", "Product Name": "PS5 Digital", "Variant": "825GB",
"UOM": "unit", "Location": "GUDANG_PUSAT", "Qty": 12,
"Low Stock Threshold": 3, "ETA Restock": None
},
{
"SKU": "SKU-PS5D-825", "Product Name": "PS5 Digital", "Variant": "825GB",
"UOM": "unit", "Location": "TOKO_BEKASI", "Qty": 2,
"Low Stock Threshold": 3, "ETA Restock": date(2025, 9, 25)
},
]


# ====== Util ======
def check_item(sku: str, location: Optional[str] = None) -> List[dict]:
sku = (sku or "").strip().upper()
loc = (location or "").strip().upper()
results = []
for row in INVENTORY:
if str(row.get("SKU", "")).upper() != sku:
continue
if location and str(row.get("Location", "")).upper() != loc:
continue
qty = int(row.get("Qty") or 0)
thr = int(row.get("Low Stock Threshold") or 0)
low_stock = qty <= thr if thr else False
eta = row.get("ETA Restock")
results.append({
"SKU": row.get("SKU"),
"product_name": row.get("Product Name"),
"variant": row.get("Variant"),
"uom": row.get("UOM"),
main()
