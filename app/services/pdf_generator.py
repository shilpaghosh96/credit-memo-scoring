from fpdf import FPDF
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from datetime import datetime
import os
import pandas as pd

def create_credit_memo(business_name, window, scorecard, features, output_path, bank_df):
    """Generates a one-page Credit Memo PDF with data, flags, and informative charts."""
    
    charts_dir = "uploads/charts"
    os.makedirs(charts_dir, exist_ok=True)

    #  Chart Generation 
    def millions_formatter(x, pos):
        return f'{x / 1e6:.1f}M'

    # Daily Balance Chart
    plt.figure(figsize=(5, 3))
    daily_balance = bank_df.groupby('date')['balance'].last()
    plt.plot(daily_balance.index, daily_balance.values, color='#4285F4', linewidth=2)
    plt.title("Daily Balance", fontsize=12, weight='bold')
    plt.ylabel("Balance (USD)", fontsize=10)
    ax = plt.gca()
    ax.yaxis.set_major_formatter(FuncFormatter(millions_formatter))
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    balance_chart_path = os.path.join(charts_dir, f"balance_{business_name}_{window}.png")
    plt.savefig(balance_chart_path, bbox_inches='tight', pad_inches=0.1)
    plt.close()

    # Weekly Net Cash Flow Chart
    plt.figure(figsize=(5, 3))
    weekly_cash_flow = bank_df.set_index('date').resample('W').apply(lambda x: x[x['in_out'] == 'in']['amount'].sum() - x[x['in_out'] == 'out']['amount'].sum())
    colors = ['#34A853' if val >= 0 else '#EA4335' for val in weekly_cash_flow.values]
    plt.bar(weekly_cash_flow.index, weekly_cash_flow.values, width=5, color=colors)
    plt.title("Weekly Net Cash Flow", fontsize=12, weight='bold')
    plt.ylabel("Net Flow (USD)", fontsize=10)
    plt.axhline(0, color='grey', linewidth=0.8)
    ax = plt.gca()
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'{x/1e3:.0f}K'))
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    cashflow_chart_path = os.path.join(charts_dir, f"cashflow_{business_name}_{window}.png")
    plt.savefig(cashflow_chart_path, bbox_inches='tight', pad_inches=0.1)
    plt.close()


    #  PDF Creation 
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)

    # Header & Summary
    pdf.cell(0, 10, f"Credit Memo: {business_name}", 0, 1, 'C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 10, f"As-of Date: {datetime.now().strftime('%Y-%m-%d')} | Window: {window}", 0, 1, 'C')
    pdf.ln(8)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Summary", 0, 1, 'L')
    pdf.set_fill_color(230, 230, 230)
    summary_text = (f"Score: {scorecard['score']:.0f} | "
                    f"Grade: {scorecard['grade']} | "
                    f"Eligible Capital: ${scorecard['eligible_capital']:,.0f} | "
                    f"Annual ECL: ${scorecard['expected_loss_annualized']:,.0f}")
    pdf.cell(0, 10, summary_text, 1, 1, 'C', 1)
    pdf.ln(8)

    #  Pass/Watch flags 
    def get_flag(metric, value):
        flags = {
            "Days Cash on Hand": '(Pass)' if value >= 15 else '(Watch)',
            "Weekly NCF Variability": '(Pass)' if value < 0.3 else '(Watch)',
            "NSF Count": '(Pass)' if value < 2 else '(Watch)',
            "Returned ACH Count": '(Pass)' if value == 0 else '(Watch)',
            "Vendor Late Proxy (%)": '(Pass)' if value < 35 else '(Watch)',
            "DSCR Proxy": '(Pass)' if value >= 1.25 else '(Watch)'
        }
        return flags.get(metric, '(Pass)')

    # Key Metrics Table
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Key Metrics", 0, 1, 'L')
    pdf.set_font("Arial", '', 10)
    
    metrics = {
        "Avg Daily Balance": f"${features['average_daily_balance']:,.0f}",
        "Days Cash on Hand": f"{features['days_cash_on_hand']:.1f}",
        "Median Monthly NOCF": f"${features['median_monthly_nocf']:,.0f}",
        "Weekly NCF Variability": f"{features['weekly_net_cashflow_variability']:.2f}",
        "NSF Count": f"{features['nsf_count']}",
        "Returned ACH Count": f"{features['returned_ach_count']}",
        "Vendor Late Proxy (%)": f"{features['vendor_late_proxy']:.1f}%",
        "DSCR Proxy": f"{features['dscr_proxy']:.2f}x"
    }
    
    feature_values = {
        "Days Cash on Hand": features['days_cash_on_hand'],
        "Weekly NCF Variability": features['weekly_net_cashflow_variability'],
        "NSF Count": features['nsf_count'],
        "Returned ACH Count": features['returned_ach_count'],
        "Vendor Late Proxy (%)": features['vendor_late_proxy'],
        "DSCR Proxy": features['dscr_proxy']
    }

    col_width = pdf.w / 2.2
    line_height = pdf.font_size * 2
    for metric_name, metric_value_str in metrics.items():
        pdf.cell(col_width, line_height, f"{metric_name}", border=1)
        
        flag = get_flag(metric_name, feature_values.get(metric_name, 0))
        
        #  CHANGE: Set text color based on the flag 
        if flag == '(Watch)':
            pdf.set_text_color(220, 53, 69)  # Red for Watch
        else:
            pdf.set_text_color(40, 167, 69)   # Green for Pass

        pdf.cell(col_width, line_height, f"{metric_value_str} {flag}", border=1, ln=1)
        
        # Reset text color to black for the next row
        pdf.set_text_color(0, 0, 0)

    pdf.ln(8)

    # Reason Codes
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Top Reason Codes", 0, 1, 'L')
    pdf.set_font("Arial", '', 10)
    if scorecard['reason_codes']:
        for code in scorecard['reason_codes']:
            pdf.cell(0, 8, f"- {code}", 0, 1)
    else:
        pdf.cell(0, 8, "- N/A", 0, 1)
    pdf.ln(4)

    # Charts
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Visuals", 0, 1, 'L')
    pdf.image(balance_chart_path, x=pdf.get_x() + 5, y=pdf.get_y(), w=90)
    pdf.image(cashflow_chart_path, x=pdf.get_x() + 105, y=pdf.get_y(), w=90)
    
    pdf.set_y(pdf.get_y() + 60)

    # Footer
    pdf.set_font("Arial", 'I', 8)
    pdf.set_text_color(128)
    pdf.cell(0, 10, "Policy Note: This is an automated credit assessment based on provided cashflow data.", 0, 0, 'C')
    
    pdf.output(output_path)

    # Clean up chart images
    try:
        os.remove(balance_chart_path)
        os.remove(cashflow_chart_path)
    except OSError as e:
        print(f"Error removing chart files: {e}")
