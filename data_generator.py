import pandas as pd
import numpy as np
import os
from datetime import datetime

def generate_business_data(business_name, total_months):
    """Generates a coherent set of financial data for a single business over a specified period."""
    end_date = pd.to_datetime('today').normalize()
    start_date = end_date - pd.DateOffset(months=total_months)
    
    #  1. Defining a business profile to make it more randomized
    profile = np.random.choice(['healthy', 'stable', 'struggling'], p=[0.6, 0.2, 0.2])
    print(f"Generating {total_months}m of data for '{business_name}' with profile: {profile}")

    #  2. Generating P&L data for the full period
    months_range = pd.date_range(end=end_date, periods=total_months, freq='ME')
    num_months = len(months_range)

    if profile == 'healthy':
        revenue = np.round(np.random.uniform(3_000_000, 5_000_000, size=num_months), 2)
        cogs_ratio, op_ex_ratio = (0.45, 0.25)
    elif profile == 'stable':
        revenue = np.round(np.random.uniform(2_500_000, 4_000_000, size=num_months), 2)
        cogs_ratio, op_ex_ratio = (0.55, 0.35)
    else: # struggling
        revenue = np.round(np.random.uniform(2_000_000, 3_500_000, size=num_months), 2)
        cogs_ratio, op_ex_ratio = (0.65, 0.45)

    pnl_monthly_df = pd.DataFrame({
        'month': months_range,
        'revenue': revenue,
        'cogs': np.round(revenue * cogs_ratio, 2),
        'operating_expense': np.round(revenue * op_ex_ratio, 2),
        'other_income_expense': np.round(np.random.uniform(-50_000, 50_000, size=num_months), 2)
    })

    #  3. Generating rest of the data
    all_transactions = []
    dates_in_window = pd.to_datetime(pd.date_range(start=start_date, end=end_date, freq='D'))
    
    in_categories = ['customer_payment', 'investment_income', 'asset_sale', 'refund', 'credit']
    out_categories = ['payroll', 'rent', 'utilities', 'supplier_payment', 'loan_repayment', 'tax_payment', 'marketing_spend', 'software_subscription', 'T&E']

    for _, row in pnl_monthly_df.iterrows():
        month_dates = [d for d in dates_in_window if d.month == row['month'].month and d.year == row['month'].year]
        if not month_dates: continue
        
        num_inflows = np.random.randint(15, 30) * len(month_dates)
        inflow_amounts = np.random.dirichlet(np.ones(num_inflows)) * row['revenue']
        
        num_outflows = np.random.randint(20, 40) * len(month_dates)
        total_outflow_target = row['cogs'] + row['operating_expense']
        outflow_amounts = np.random.dirichlet(np.ones(num_outflows)) * total_outflow_target

        for amount in inflow_amounts:
            all_transactions.append({'date': np.random.choice(month_dates), 'amount': amount, 'category': np.random.choice(in_categories), 'in_out': 'in'})
        for amount in outflow_amounts:
            all_transactions.append({'date': np.random.choice(month_dates), 'amount': amount, 'category': np.random.choice(out_categories), 'in_out': 'out'})

    bank_tx_df = pd.DataFrame(all_transactions)
    
    #  Putting in some nsf and ach checks to make it more realistic
    nsf_events = []
    if profile == 'struggling':
        num_nsf = np.random.randint(2, 5)
        num_ach = np.random.randint(2, 5)
    elif profile == 'stable':
        num_nsf = np.random.randint(0, 2)
        num_ach = np.random.randint(0, 2)
    else: # healthy
        num_nsf, num_ach = 0, 0
        
    for _ in range(num_nsf):
        nsf_events.append({'date': np.random.choice(dates_in_window), 'amount': np.round(np.random.uniform(25, 50), 2), 'category': 'nsf_fee', 'in_out': 'out'})
    for _ in range(num_ach):
        nsf_events.append({'date': np.random.choice(dates_in_window), 'amount': np.round(np.random.uniform(500, 2000), 2), 'category': 'returned_ach', 'in_out': 'out'})

    if nsf_events:
        bank_tx_df = pd.concat([bank_tx_df, pd.DataFrame(nsf_events)], ignore_index=True)

    bank_tx_df = bank_tx_df.sort_values(by='date').reset_index(drop=True)
    bank_tx_df['amount'] = bank_tx_df['amount'].round(2)
    bank_tx_df['counterparty'] = [f'Counterparty_{i}' for i in np.random.randint(1, 100, size=len(bank_tx_df))]

    initial_balance = np.round(np.random.uniform(15_000_000, 25_000_000), 2)
    signed_amounts = np.where(bank_tx_df['in_out'] == 'in', bank_tx_df['amount'], -bank_tx_df['amount'])
    bank_tx_df['balance'] = np.round(initial_balance + signed_amounts.cumsum(), 2)
    
    return pnl_monthly_df, bank_tx_df

def save_sliced_data(business_name, full_pnl, full_bank_tx, months_to_save):
    """Slices the full dataset to the specified window and saves the files."""
    end_date = full_pnl['month'].max()
    start_date = end_date - pd.DateOffset(months=months_to_save)

    pnl_slice = full_pnl[full_pnl['month'] > start_date].copy()
    bank_tx_slice = full_bank_tx[full_bank_tx['date'] > start_date].copy()

    pnl_slice['month'] = pnl_slice['month'].dt.strftime('%Y-%m')

    bank_tx_slice['invoice_date'] = pd.NaT
    bank_tx_slice['due_date'] = pd.NaT
    outflow_mask = bank_tx_slice['in_out'] == 'out'
    num_outflows = outflow_mask.sum()
    if num_outflows > 0:
        invoice_offsets = pd.to_timedelta(np.random.randint(15, 45, size=num_outflows), unit='d')
        due_offsets = pd.to_timedelta(30 + np.random.randint(-5, 10, size=num_outflows), unit='d')
        invoice_dates_calculated = bank_tx_slice.loc[outflow_mask, 'date'] - invoice_offsets
        bank_tx_slice.loc[outflow_mask, 'invoice_date'] = invoice_dates_calculated
        due_dates_calculated = bank_tx_slice.loc[outflow_mask, 'invoice_date'] + due_offsets
        bank_tx_slice.loc[outflow_mask, 'due_date'] = due_dates_calculated
        bank_tx_slice['invoice_date'] = bank_tx_slice['invoice_date'].dt.strftime('%Y-%m-%d')
        bank_tx_slice['due_date'] = bank_tx_slice['due_date'].dt.strftime('%Y-%m-%d')
    
    output_dir = f'data/{business_name}/trailing_{months_to_save}m'
    os.makedirs(output_dir, exist_ok=True)
    bank_tx_slice.to_csv(f'{output_dir}/bank_tx.csv', index=False)
    pnl_slice.to_csv(f'{output_dir}/pnl_monthly.csv', index=False)
    
    vendors_data = {'vendor_id': [f'V{i}' for i in range(1, 101)], 'name': [f'Vendor Name {i}' for i in range(1, 101)], 'category': np.random.choice(['supplies', 'rent', 'utilities', 'marketing', 'logistics', 'software'], size=100), 'is_critical': np.random.choice([True, False], size=100, p=[0.3, 0.7])}
    pd.DataFrame(vendors_data).to_csv(f'{output_dir}/vendors.csv', index=False)


if __name__ == "__main__":
    for name in ['business_a', 'business_b']:
        full_pnl_df, full_bank_tx_df = generate_business_data(name, 6)
        save_sliced_data(name, full_pnl_df, full_bank_tx_df, 6)
        save_sliced_data(name, full_pnl_df, full_bank_tx_df, 3)

    print("Data generated successfully in the 'data' directory.")
