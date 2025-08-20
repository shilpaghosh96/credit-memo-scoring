# Lender Scorecard Prototype

## 1. Purpose

This project is a demo-ready prototype that provides a rapid, data-driven credit assessment for commercial lenders. The system ingests cash flow data for a business, computes a lender-style scorecard based on clear policy rules, and generates a one-page Credit Memo PDF designed to be understood in 60 seconds.

The goal is to automate the initial stages of credit analysis, allowing a loan officer to quickly gauge a business's financial health and creditworthiness.

---

## 2. Scope

#### In Scope:
* **CSV Data Upload:** A simple web interface to upload financial data.
* **Data Quality Checks:** Lightweight validation of the uploaded files to ensure data integrity.
* **Dual-Window Analysis:** Feature calculation and scoring for both trailing 3-month and 6-month periods.
* **CFX-Lite Scorecard:** Calculation of a final score (0-100) and a corresponding risk grade (A-E).
* **Capital & Loss Estimation:**
    * **Eligible Capital:** An estimate of eligible capital based on cash flow, adjusted by policy rules and penalties.
    * **Expected Loss:** A CECL-lite calculation of potential annualized loss.
* **One-Page Credit Memo:** Generation of a downloadable PDF summarizing all key metrics, flags, reason codes, and visuals.

#### Out of Scope:
* KYC (Know Your Customer), credit bureau integration, and fraud checks.
* Data persistence beyond a single local run.
* Integrations with other banking systems.

---

## 3. Case Study: Sample Businesses

To demonstrate the application's capabilities, this project includes synthetic data for two hypothetical businesses:

* **Business A ("ABC Corp.")** and **Business B ("XYZ Corp.")**

Both are modeled as **medium-sized manufacturers of specialized electronic components** based in the Silicon Valley area. This business type was chosen because it aligns with the data structure, which includes high capital requirements, significant Cost of Goods Sold (COGS), and logistical expenses for shipping high-value components.

---

## 4. Inputs

The application requires the following CSV files for both a **3-month** and a **6-month** trailing window:

#### `bank_tx.csv` (Required)
Contains individual bank transactions.
* `date`: The date of the transaction.
* `amount`: The transaction amount (always positive).
* `balance`: The running account balance after the transaction.
* `counterparty`: The name of the other party in the transaction.
* `category`: The type of transaction (e.g., `payroll`, `customer_payment`, `loan_repayment`).
* `in_out`: The direction of the transaction (`in` or `out`).
* `invoice_date`: (For outflows) The date the bill was issued. (added to feature engineer the vendor late proxy variable)
* `due_date`: (For outflows) The date the payment was due. (added to feature engineer the vendor late proxy variable)

#### `pnl_monthly.csv` (Required)
Contains monthly Profit & Loss summary data.
* `month`: The month of the record (e.g., `2025-08`).
* `revenue`: Total monthly revenue.
* `cogs`: Cost of Goods Sold.
* `operating_expense`: Monthly operating expenses.

#### `vendors.csv` (Optional)
Contains information about the business's vendors.
* `vendor_id`: A unique identifier for the vendor.
* `name`: The name of the vendor.
* `category`: The vendor's industry (e.g., `supplies`, `logistics`).
* `is_critical`: A flag indicating if the vendor is critical to operations.

---

## 5. Outputs

The application produces two primary outputs:

1.  **Web Dashboard:** An interactive, side-by-side comparison of the 3-month and 6-month scorecards, displaying the final Score, Grade, Eligible Capital, and top reason codes.
2.  **Credit Memo PDF:** A downloadable, one-page PDF report that includes:
    * A high-level summary band.
    * A detailed table of 12-15 key financial metrics with **(Pass)** or **(Watch)** flags.
    * The top three reason codes driving the score.
    * Informative charts for daily balance and weekly net cash flow.

---

## 6. How to Run

1.  **Set up the environment:**
    ```bash
    conda create --name lender_scorecard_env python=3.9
    conda activate lender_scorecard_env
    pip install -r requirements.txt
    ```

2.  **Generate sample data (optional):**
    To create the sample data for the two manufacturing businesses, run:
    ```bash
    python data_generator.py
    ```
    This will create the necessary CSV files in the `data/` directory.

3.  **Start the web server:**
    ```bash
    uvicorn app.main:app --reload
    ```

4.  **Access the application:**
    Open your web browser and navigate to `http://127.0.0.1:8000`.
