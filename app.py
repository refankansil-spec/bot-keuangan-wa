from datetime import datetime
from flask import Flask, jsonify, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

app = Flask(__name__)

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDENTIALS_FILE = "credentials.json"
SPREADSHEET_NAME = "Keuangan Bot"

def get_sheets_table():
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
    client = gspread.authorize(creds)
    return client.open(SPREADSHEET_NAME).sheet1

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
    return {"category": "Umum", "description": description, "nominal": nominal, "method": "QRIS"}

@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    try:
        data = request.json or {}
        
        # AutoResponder biasanya menaruh pesan di dalam objek "query"
        query_data = data.get("query", {})
        message = query_data.get("message") or data.get("message") or ""
        
        if not message:
            return jsonify({"replies": [{"message": "Gagal: Format pesan dari AutoResponder tidak terbaca."}]}), 200

        parsed = parse_expense_text(message)
        if parsed["nominal"] == 0:
            return jsonify({"replies": [{"message": "Gagal: Nominal angka tidak terdeteksi."}]}), 200

        now = datetime.now()
        row_data = [
            now.strftime("%d/%m/%Y %H:%M:%S"),
            now.strftime("%Y-%m-%d"),
            message,
            parsed["category"],
            parsed["description"],
            parsed["nominal"],
            parsed["method"],
        ]

        sheet = get_sheets_table()
        sheet.append_row(row_data)
        
        response_text = f"✅ Berhasil dicatat!\nDeskripsi: {parsed['description']}\nNominal: Rp {parsed['nominal']:,}".replace(",", ".")
        return jsonify({"replies": [{"message": response_text}]}), 200

    except Exception as e:
        # Menangkap error seperti credentials.json salah/tidak ada
        return jsonify({"replies": [{"message": f"Error Sistem: {str(e)}"}]}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
