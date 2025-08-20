import pandas as pd
import numpy as np

def validate_data(bank_tx_path, pnl_monthly_path, vendors_path=None):
    """Performs data quality checks on the uploaded CSV files."""
    results = {}
    passed = True

    try:
        #  bank_tx.csv checks 
        bank_tx_df = pd.read_csv(bank_tx_path, parse_dates=['date'])
        results['bank_tx_missing_dates'] = int(bank_tx_df['date'].diff().dt.days.gt(1).sum())
        results['bank_tx_duplicate_rows'] = int(bank_tx_df.duplicated().sum())
        results['bank_tx_negative_or_empty_amounts'] = int(((bank_tx_df['amount'] < 0) | bank_tx_df['amount'].isnull()).sum())

        #  Balance Continuity Check
        if not bank_tx_df.empty:
            bank_tx_df['signed_amount'] = np.where(bank_tx_df['in_out'] == 'in', bank_tx_df['amount'], -bank_tx_df['amount'])
            
            # Group by date to get the net change and closing balance for each day
            daily_summary = bank_tx_df.groupby('date').agg(
                daily_net_change=('signed_amount', 'sum'),
                closing_balance=('balance', 'last')
            ).reset_index()

            # Get the previous day's closing balance
            previous_closing_balance = daily_summary['closing_balance'].shift(1)
            
            # The expected balance for today is yesterday's close + today's net change
            expected_today_balance = previous_closing_balance + daily_summary['daily_net_change']
            
            # Compare the actual closing balance to the expected, allowing for a small tolerance
            balance_errors = ~np.isclose(daily_summary['closing_balance'][1:], expected_today_balance[1:])
            results['balance_continuity_errors'] = int(balance_errors.sum())
        else:
            results['balance_continuity_errors'] = 0


        #  Category Coverage Check 
        missing_categories = bank_tx_df['category'].isnull().sum()
        total_transactions = len(bank_tx_df)
        if total_transactions > 0:
            category_coverage_percent = ( (total_transactions - missing_categories) / total_transactions ) * 100
            # Fail if coverage is less than 95%
            results['category_coverage_low'] = 1 if category_coverage_percent < 95 else 0
        else:
            results['category_coverage_low'] = 0


        #  pnl_monthly.csv checks 
        pnl_df = pd.read_csv(pnl_monthly_path)
        results['pnl_null_values'] = int(pnl_df[['revenue', 'cogs', 'operating_expense']].isnull().sum().sum())

        #  vendors.csv checks (optional file) 
        if vendors_path:
            try:
                vendors_df = pd.read_csv(vendors_path)
                results['vendors_null_values'] = int(vendors_df[['vendor_id', 'name']].isnull().sum().sum())
                results['vendors_duplicate_ids'] = int(vendors_df['vendor_id'].duplicated().sum())
            except Exception as e:
                results['vendors_read_error'] = str(e)


        # Final check to determine overall pass/fail status
        for key, value in results.items():
            if isinstance(value, (int, float)) and value > 0:
                passed = False

        return {"passed": passed, "checks": results}

    except Exception as e:
        return {"passed": False, "error": str(e)}
