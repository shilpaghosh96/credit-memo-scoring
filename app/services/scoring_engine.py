import numpy as np

def calculate_scorecard(features):
    """Calculates the scorecard based on the computed features."""
    
    #  1. Normalized the features to a 0-100 scale 
    liquidity_score = np.clip((features['days_cash_on_hand'] / 30) * 100, 0, 100)
    
    # If median cash flow is negative, the score is 0. Otherwise, it's based on variability.
    if features['median_monthly_nocf'] < 0:
        cash_flow_score = 0
    else:
        cash_flow_score = np.clip((1 - features['weekly_net_cashflow_variability']) * 100, 0, 100) if features['weekly_net_cashflow_variability'] is not None else 50
        
    stability_score = np.clip((1 - features['mom_revenue_variability']) * 100, 0, 100) if features['mom_revenue_variability'] is not None else 50
    discipline_score = 100 - np.clip(features['nsf_count'] * 20, 0, 100)
    concentration_score = 100 - np.clip((features['top_vendor_share'] - 0.2) * 200, 0, 100)

    #  2. CFX-Lite Score 
    weights = {'Liquidity': 0.25, 'Cash flow': 0.35, 'Discipline': 0.20, 'Stability': 0.10, 'Concentration': 0.10}
    score = sum([
        liquidity_score * weights['Liquidity'],
        cash_flow_score * weights['Cash flow'],
        discipline_score * weights['Discipline'],
        stability_score * weights['Stability'],
        concentration_score * weights['Concentration']
    ])

    #  3. Grade 
    grade = 'E'
    if score >= 80: grade = 'A'
    elif score >= 70: grade = 'B'
    elif score >= 60: grade = 'C'
    elif score >= 45: grade = 'D'

    #  4. Eligible Capital 
    base_multiples = {'A': 4.0, 'B': 3.0, 'C': 2.0, 'D': 1.0, 'E': 0}
    # If the grade is poor, base capital will be low or zero.
    base_capital = features['median_monthly_nocf'] * base_multiples[grade]
    
    # Ensure base capital isn't negative, which makes no sense.
    base_capital = max(0, base_capital)

    volatility_discount = max(0.6, 1 - (features['weekly_net_cashflow_variability'] or 0.5))
    liquidity_guard = 0.5 if features['days_cash_on_hand'] < 15 else 1.0
    discipline_penalty = 0.8 if features['nsf_count'] >= 2 else 1.0
    concentration_penalty = 0.85 if features['top_vendor_share'] > 0.35 else 1.0
    adjusted_capital = base_capital * volatility_discount * liquidity_guard * discipline_penalty * concentration_penalty

    revenue_cap = 0.15 * features['annualized_revenue']
    eligible_capital = min(adjusted_capital, revenue_cap)
    if grade in ['A', 'B']: eligible_capital = max(eligible_capital, 5000)

    #  5. CECL-lite Expected Loss 
    pd_by_grade = {'A': 0.015, 'B': 0.03, 'C': 0.06, 'D': 0.12, 'E': 0.25}
    lgd = 0.35 if features['nsf_count'] == 0 and features['percent_of_days_below_zero'] == 0 else 0.45
    ead = 0.70 * eligible_capital
    expected_loss_annualized = pd_by_grade[grade] * lgd * ead

    #  6. Reason Codes 
    reasons = []
    if features['days_cash_on_hand'] < 15: reasons.append('LOW_LIQ')
    if features['mom_revenue_variability'] > 0.3: reasons.append('REV_VAR')
    if features['top_vendor_share'] > 0.35: reasons.append('HIGH_CONC')
    if features['nsf_count'] >= 2: reasons.append('NSF_EVENTS')
    if features['dscr_proxy'] < 1.25: reasons.append('LOW_DSCR')
    if features['median_monthly_nocf'] < 0: reasons.append('NEGATIVE_CASHFLOW')

    if not reasons:
        if features['mom_revenue_variability'] < 0.1: reasons.append('REV_STABLE')
        if features['days_cash_on_hand'] >= 15: reasons.append('CASH_BUFFER')
        if features['nsf_count'] == 0: reasons.append('NO_NSF')
        if features['weekly_net_cashflow_variability'] < 0.3: reasons.append('CONSISTENT_CASHFLOW')
        if features['top_vendor_share'] < 0.2: reasons.append('DIVERSIFIED_VENDORS')

    return {
        'score': score,
        'grade': grade,
        'eligible_capital': eligible_capital,
        'expected_loss_annualized': expected_loss_annualized,
        'reason_codes': reasons[:3]
    }
