from datetime import datetime
from flask import Flask, jsonify, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

app = Flask(__name__)

# --- Konfigurasi Google Sheets ---
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
CREDENTIALS_FILE = "credentials.json"
SPREADSHEET_NAME = "Keuangan Bot"  # Ganti dengan nama Google Sheets yang kamu buat

def get_sheets_table():
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME).sheet1
    return sheet

def parse_expense_text(text):
    words = text.split()
    nominal = 0
    desc_words = []

    for word in words:
        cleaned_word = word.lower().replace("rb", "000").replace("k", "000").replace(".", "").replace(",", "")
        if cleaned_word.isdigit():
            nominal = int(cleaned_word)
        else:
            desc_words.append(word)

    description = " ".join(desc_words) if desc_words else "Pengeluaran Lain"
    category = "Umum"

    return {
        "category": category,
        "description": description,
        "nominal": nominal,
        "method": "QRIS",
    }

@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400

    message = data.get("message") or data.get("text")
    if not message:
        return jsonify({"status": "ignored", "message": "No message text"}), 200

    parsed = parse_expense_text(message)
    
    if parsed["nominal"] == 0:
        return jsonify({"replies": [{"message": "Gagal: Nominal tidak terdeteksi dalam pesan"}]}), 200

    now = datetime.now()
    timestamp = now.strftime("%d/%m/%Y %H:%M:%S")
    date_only = now.strftime("%Y-%m-%d")

    row_data = [
        timestamp,
        date_only,
        message,
        parsed["category"],
        parsed["description"],
        parsed["nominal"],
        parsed["method"],
    ]

    try:
        sheet = get_sheets_table()
        sheet.append_row(row_data)
        response_text = f"✅ Berhasil dicatat!\nKategori: {parsed['category']}\nDeskripsi: {parsed['description']}\nNominal: Rp {parsed['nominal']:,}".replace(",", ".")
        return jsonify({"replies": [{"message": response_text}]}), 200

    except Exception as e:
        return jsonify({"replies": [{"message": f"Terjadi kesalahan sistem: {str(e)}"}]}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
