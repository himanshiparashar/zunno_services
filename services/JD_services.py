import os
import logging
from flask import Blueprint, request, jsonify

# import extractor functions from invoice_system/extractor.py
from extractor import (
    detect_file_type,
    extract_text_digital,
    extract_text_scanned,
    extract_text_easyocr_pdf,
    extract_text_image,
    extract_with_llm,
    validate_and_fix_json,
)

logger = logging.getLogger(__name__)
jd_blueprint = Blueprint("jd_services", __name__)

@jd_blueprint.route("/process_invoice", methods=["POST"])
def process_invoice():
    """
    Endpoint to process an invoice file (PDF/Image) and return structured JSON.
    Usage: POST with form-data: file=<invoice.pdf>
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    filename = file.filename
    save_path = os.path.join("/tmp", filename)
    file.save(save_path)

    try:
        file_type = detect_file_type(save_path)

        if file_type == "Digital PDF":
            text = extract_text_digital(save_path)
        elif file_type == "Scanned PDF":
            text = extract_text_scanned(save_path)
        elif file_type == "Mixed PDF":
            text = extract_text_easyocr_pdf(save_path)
        elif file_type == "Image File":
            text = extract_text_image(save_path)
        else:
            return jsonify({"error": f"Unsupported file type: {file_type}"}), 400

        extracted = extract_with_llm(text, filename)
        validated = validate_and_fix_json(extracted)

        result = {
            "message": "Invoice processed successfully!",
            "filename": filename,
            "file_type": file_type,
            "llm_extracted": validated,
        }
        return jsonify(result), 200

    except Exception as e:
        logger.exception("Invoice processing failed")
        return jsonify({"error": f"Invoice processing failed: {str(e)}"}), 500

