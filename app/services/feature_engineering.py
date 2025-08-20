import pandas as pd
import numpy as np

def compute_features(bank_tx_df, pnl_monthly_df, vendors_df=None):
    """Computes financial features from the input dataframes."""
    features = {}

    #  Liquidity 
    daily_balance = bank_tx_df.groupby('date')['balance'].last()
    features['average_daily_balance'] = daily_balance.mean()
    features['percent_of_days_below_zero'] = (daily_balance < 0).mean() * 100
    avg_daily_expenses = pnl_monthly_df['operating_expense'].mean() / 30
    features['days_cash_on_hand'] = features['average_daily_balance'] / avg_daily_expenses if avg_daily_expenses > 0 else 0

    #  Cash flow 
    pnl_monthly_df['nocf'] = pnl_monthly_df['revenue'] - pnl_monthly_df['cogs'] - pnl_monthly_df['operating_expense']
    features['median_monthly_nocf'] = pnl_monthly_df['nocf'].median()

    bank_tx_df['signed_amount'] = np.where(bank_tx_df['in_out'] == 'in', bank_tx_df['amount'], -bank_tx_df['amount'])
    weekly_cash_flow = bank_tx_df.set_index('date')['signed_amount'].resample('W').sum()
    features['weekly_net_cashflow_variability'] = weekly_cash_flow.std() / weekly_cash_flow.mean() if weekly_cash_flow.mean() != 0 else 0

    inflows_df = bank_tx_df[bank_tx_df['in_out'] == 'in']
    total_inflows = inflows_df['amount'].sum()
    credit_inflows = inflows_df[inflows_df['category'] == 'credit']['amount'].sum() 
    features['draw_on_credit_ratio'] = credit_inflows / total_inflows if total_inflows > 0 else 0


    #  Payment discipline (Updated Logic) 
    # Counting NSF and ACH returns based on the 'category' column
    features['nsf_count'] = int((bank_tx_df['category'] == 'nsf_fee').sum())
    features['returned_ach_count'] = int((bank_tx_df['category'] == 'returned_ach').sum())
    
    # Calculate vendor late proxy from new date columns
    # Filtering for outgoing payments that have a due date
    vendor_payments = bank_tx_df[(bank_tx_df['in_out'] == 'out') & (bank_tx_df['due_date'].notna())].copy()
    
    if not vendor_payments.empty:
        # Convert date columns to datetime objects for comparison
        vendor_payments['payment_date'] = pd.to_datetime(vendor_payments['date'])
        vendor_payments['due_date'] = pd.to_datetime(vendor_payments['due_date'])
        
        # A payment is late if it's made after the due date
        late_payments = (vendor_payments['payment_date'] > vendor_payments['due_date']).sum()
        total_payments = len(vendor_payments)
        
        # The proxy is the percentage of late payments
        features['vendor_late_proxy'] = (late_payments / total_payments) * 100 if total_payments > 0 else 0
    else:
        features['vendor_late_proxy'] = 0


    #  Revenue stability 
    features['mom_revenue_variability'] = pnl_monthly_df['revenue'].pct_change().std()
    if len(pnl_monthly_df) >= 3:
        revenue_trend = np.polyfit(range(len(pnl_monthly_df['revenue'][-3:])), pnl_monthly_df['revenue'][-3:], 1)
        features['3_month_slope'] = revenue_trend[0]
    else:
        features['3_month_slope'] = 0
    features['seasonal_delta'] = 0  # Placeholder

    #  Concentration 
    outgoing_transactions = bank_tx_df[bank_tx_df['in_out'] == 'out']
    if not outgoing_transactions.empty:
        vendor_spending = outgoing_transactions.groupby('counterparty')['amount'].sum()
        total_spending = vendor_spending.sum()
        features['top_vendor_share'] = vendor_spending.max() / total_spending if total_spending > 0 else 0
        features['top_5_vendors_share'] = vendor_spending.nlargest(5).sum() / total_spending if total_spending > 0 else 0
    else:
        features['top_vendor_share'] = 0
        features['top_5_vendors_share'] = 0

    #  Coverage (Updated Logic) 
    # Calculate NOCF for the entire period from the P&L data
    total_nocf = pnl_monthly_df['nocf'].sum()
    
    # Calculate Debt Service proxy from bank transaction data
    # Sum of all outflows categorized as 'loan_repayment'
    debt_service = bank_tx_df[bank_tx_df['category'] == 'loan_repayment']['amount'].sum()
    
    # DSCR Proxy = NOCF / Debt Service
    features['dscr_proxy'] = total_nocf / debt_service if debt_service > 0 else 0
    
    # Calculate annualized revenue
    features['annualized_revenue'] = pnl_monthly_df['revenue'].sum() * (12 / len(pnl_monthly_df))

    # Clean up NaNs and return
    return {k: 0 if pd.isna(v) else v for k, v in features.items()}
