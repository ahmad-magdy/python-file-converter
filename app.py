import io
import os
import zipfile
from datetime import timedelta
from typing import List
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, send_file, abort
)
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
from PIL import Image
import img2pdf
import pytesseract

# --------- Configuration ----------
UPLOAD_FOLDER = "uploads"
RESULTS_FOLDER = "results"
ALLOWED_PDF_EXT = {"pdf"}
ALLOWED_IMG_EXT = {"jpg", "jpeg", "png"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-for-deployment")
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_UPLOAD_MB", 60)) * 1024 * 1024
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["RESULTS_FOLDER"] = RESULTS_FOLDER
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = timedelta(seconds=0)

# ===== FIX FOR REPLIT TESSERACT PATH =====
tesseract_path = os.environ.get('TESSERACT_CMD')
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
# ==============================================

# ---------- Helpers ----------
def allowed_file(filename: str, allowed: set) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed

def pdf_bytes_to_jpegs(pdf_bytes: bytes, dpi: int = 200, jpeg_quality: int = 90) -> List[bytes]:
    """Return list of JPEG bytes, one per PDF page."""
    images: List[bytes] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=jpeg_quality, optimize=True)
            images.append(buf.getvalue())
    return images

def images_bytes_to_pdf(image_bytes_list: List[bytes]) -> bytes:
    """Return single PDF bytes created from image bytes list (keeps order)."""
    img_streams = [io.BytesIO(b) for b in image_bytes_list]
    pdf_bytes = img2pdf.convert(img_streams)
    return pdf_bytes

# ---------- Routes ----------
@app.get("/")
def index():
    return render_template("index.html")

# 1) PDF -> JPG(s)
@app.post("/convert/pdf-to-jpg")
def convert_pdf_to_jpg():
    file = request.files.get("pdf")
    dpi = int(request.form.get("dpi", 200))
    quality = int(request.form.get("quality", 90))

    if not file or file.filename == "":
        flash("Please choose a PDF file.", "error")
        return redirect(url_for("index"))

    if not allowed_file(file.filename, ALLOWED_PDF_EXT):
        flash("Only .pdf files are allowed.", "error")
        return redirect(url_for("index"))

    try:
        pdf_bytes = file.read()
        images = pdf_bytes_to_jpegs(pdf_bytes, dpi=dpi, jpeg_quality=quality)
        if not images:
            flash("No pages found in PDF.", "error")
            return redirect(url_for("index"))

        base = os.path.splitext(secure_filename(file.filename))[0]
        if len(images) == 1:
            out_name = f"{base}_page1.jpg"
            return send_file(io.BytesIO(images[0]), mimetype="image/jpeg",
                             as_attachment=True, download_name=out_name)
        else:
            zip_name = f"{base}_pages.zip"
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for i, img_bytes in enumerate(images, start=1):
                    zf.writestr(f"{base}_page{i}.jpg", img_bytes)
            zip_buffer.seek(0)
            return send_file(zip_buffer, mimetype="application/zip",
                             as_attachment=True, download_name=zip_name)
    except Exception as e:
        app.logger.exception("PDF->JPG failed")
        flash(f"Conversion failed: {e}", "error")
        return redirect(url_for("index"))

# 2) JPG(s) -> PDF
@app.post("/convert/jpg-to-pdf")
def convert_jpg_to_pdf():
    files = request.files.getlist("images")
    if not files or all(f.filename == "" for f in files):
        flash("Please choose one or more image files.", "error")
        return redirect(url_for("index"))

    image_bytes_list = [f.read() for f in files if f and allowed_file(f.filename, ALLOWED_IMG_EXT)]
    if not image_bytes_list:
        flash("No valid images provided (jpg/jpeg/png).", "error")
        return redirect(url_for("index"))

    try:
        pdf_bytes = images_bytes_to_pdf(image_bytes_list)
        return send_file(io.BytesIO(pdf_bytes), mimetype="application/pdf",
                         as_attachment=True, download_name="images_merged.pdf")
    except Exception as e:
        app.logger.exception("JPG->PDF failed")
        flash(f"Conversion failed: {e}", "error")
        return redirect(url_for("index"))

# 3) Image -> Text (OCR)
@app.post("/image-to-text")
def image_to_text():
    file = request.files.get("image")
    lang = request.form.get("lang", "eng")

    if not file or file.filename == "":
        flash("Please choose an image file.", "error")
        return redirect(url_for("index"))
    if not allowed_file(file.filename, ALLOWED_IMG_EXT):
        flash("Only JPG, JPEG, or PNG files are allowed for OCR.", "error")
        return redirect(url_for("index"))

    try:
        img = Image.open(file.stream).convert("RGB")
        text = pytesseract.image_to_string(img, lang=lang)
        base = os.path.splitext(secure_filename(file.filename))[0]
        out_txt_name = f"{base}_ocr.txt"
        out_txt_path = os.path.join(app.config["RESULTS_FOLDER"], secure_filename(out_txt_name))
        with open(out_txt_path, "w", encoding="utf-8") as f:
            f.write(text)
        return render_template("ocr_result.html", text=text,
                               txt_download=out_txt_name, lang=lang)
    except Exception as e:
        app.logger.exception("OCR failed")
        flash(f"OCR failed: {e}", "error")
        return redirect(url_for("index"))

# Download result TXT helper
@app.get("/download-txt/<filename>")
def download_txt(filename):
    safe_name = secure_filename(filename)
    path = os.path.join(app.config["RESULTS_FOLDER"], safe_name)
    if os.path.isfile(path):
        return send_file(path, as_attachment=True)
    abort(404)

# Health check for the hosting service
@app.get("/healthz")
def healthz():
    return {"status": "ok"}
