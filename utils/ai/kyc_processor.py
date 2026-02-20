import sys
import json
import os

def process_kyc(image_path):
    """
    Simulates OCR processing of an identity document.
    In production, this would use Tesseract or AWS Textract.
    """
    if not os.path.exists(image_path):
        return {"status": "error", "message": "File not found"}
    
    # Simulate processing delay/logic
    # For simulation, we'll "extract" some data based on the filename or just dummy data
    file_name = os.path.basename(image_path).lower()
    
    # Mock data extraction
    status = "flagged" if "fake" in file_name else "verified"
    
    return {
        "status": status,
        "extractedData": {
            "idNumber": "199412345678V" if status == "verified" else "XXXXXXXXXXXXX",
            "name": "TEST USER" if status == "verified" else "UNKNOWN",
            "expiryDate": "2030-01-01",
            "documentType": "NIC" if "nic" in file_name else "Passport"
        },
        "confidence": 0.95 if status == "verified" else 0.45,
        "recommendation": "Approve" if status == "verified" else "Manual Review Required"
    }

if __name__ == "__main__":
    try:
        input_data = sys.stdin.read()
        if not input_data:
            print(json.dumps({"error": "No input"}))
            sys.exit(1)
            
        data = json.loads(input_data)
        path = data.get('imagePath', '')
        
        result = process_kyc(path)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
