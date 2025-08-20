from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import pandas as pd
import shutil
import os
from typing import Optional

from app.services.data_validation import validate_data
from app.services.feature_engineering import compute_features
from app.services.scoring_engine import calculate_scorecard
from app.services.pdf_generator import create_credit_memo

app = FastAPI()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Mount the static directory for CSS and JS files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serves the main HTML page."""
    try:
        with open("app/templates/index.html") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="index.html not found")

@app.post("/score/")
async def score_business(
    business_name: str = Form(...),
    bank_tx_3m: UploadFile = File(...),
    pnl_monthly_3m: UploadFile = File(...),
    vendors_3m: Optional[UploadFile] = File(None),
    bank_tx_6m: UploadFile = File(...),
    pnl_monthly_6m: UploadFile = File(...),
    vendors_6m: Optional[UploadFile] = File(None)
):
    """
    Handles file uploads, validates data, computes scores for 3m and 6m windows,
    and generates a PDF credit memo.
    """
    business_upload_dir = UPLOAD_DIR / business_name
    business_upload_dir.mkdir(exist_ok=True)

    files_map = {
        "3m": {"bank_tx": bank_tx_3m, "pnl_monthly": pnl_monthly_3m, "vendors": vendors_3m},
        "6m": {"bank_tx": bank_tx_6m, "pnl_monthly": pnl_monthly_6m, "vendors": vendors_6m}
    }

    results = {}

    for window, files in files_map.items():
        try:
            #  Save files 
            bank_tx_path = business_upload_dir / f"bank_tx_{window}.csv"
            pnl_monthly_path = business_upload_dir / f"pnl_monthly_{window}.csv"
            vendors_path = None

            with open(bank_tx_path, "wb") as buffer:
                shutil.copyfileobj(files["bank_tx"].file, buffer)
            with open(pnl_monthly_path, "wb") as buffer:
                shutil.copyfileobj(files["pnl_monthly"].file, buffer)
            
            #  Checking if optional vendors file was uploaded 
            vendor_file = files["vendors"]
            if vendor_file and vendor_file.filename:
                vendors_path = business_upload_dir / f"vendors_{window}.csv"
                with open(vendors_path, "wb") as buffer:
                    shutil.copyfileobj(vendor_file.file, buffer)

            #  1. Data Validation 
            validation = validate_data(bank_tx_path, pnl_monthly_path, vendors_path)
            if not validation["passed"]:
                results[window] = {"error": "Data validation failed", "details": validation["checks"]}
                continue

            #  2. Feature Engineering 
            bank_df = pd.read_csv(bank_tx_path, parse_dates=['date'])
            pnl_df = pd.read_csv(pnl_monthly_path)
            vendors_df = pd.read_csv(vendors_path) if vendors_path else None
            features = compute_features(bank_df, pnl_df, vendors_df)

            #  3. Scoring 
            scorecard = calculate_scorecard(features)
            
            #  4. PDF Generation 
            pdf_filename = f"Credit_Memo_{business_name}_{window}.pdf"
            pdf_output_path = business_upload_dir / pdf_filename
            create_credit_memo(business_name, window, scorecard, features, str(pdf_output_path), bank_df)

            results[window] = {
                "scorecard": scorecard,
                "features": features,
                "pdf_download_url": f"/download/{business_name}/{pdf_filename}"
            }

        except Exception as e:
            # Provide a more detailed error message to the frontend
            raise HTTPException(status_code=500, detail=f"Error processing {window} data: {str(e)}")

    return JSONResponse(content=results)

@app.get("/download/{business_name}/{filename}")
async def download_file(business_name: str, filename: str):
    """Provides a download link for the generated PDF."""
    file_path = UPLOAD_DIR / business_name / filename
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='application/pdf', filename=filename)
    raise HTTPException(status_code=404, detail="File not found")
