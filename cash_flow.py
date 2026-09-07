def analyze_finances():
    target = 100000
    tax_rate = 0.25
    stripe_pct = 0.029
    stripe_flat = 0.30
    
    # 1. One-time $20 Fee Model
    price_onetime = 20.00
    # Net per transaction after stripe
    net_per_trans_onetime = price_onetime - (price_onetime * stripe_pct + stripe_flat)
    # Gross revenue needed before 25% tax to keep $100k net
    gross_needed_onetime = target / (1 - tax_rate)
    # Users needed
    users_needed_onetime = gross_needed_onetime / net_per_trans_onetime
    
    # 2. $7/Month Subscription Model (Target: Pay off over 12 months)
    price_sub = 7.00
    net_per_trans_sub = price_sub - (price_sub * stripe_pct + stripe_flat)
    # Total net revenue needed per month to hit $100k in 12 months
    net_needed_per_month = target / 12
    # Gross revenue needed per month before tax
    gross_needed_per_month = net_needed_per_month / (1 - tax_rate)
    # Active subscribers needed consistently for 12 months
    subs_needed = gross_needed_per_month / net_per_trans_sub
    
    print(f"One-time $20 Fee: Need {int(users_needed_onetime):,} total buyers.")
    print(f"$7/Month Sub: Need {int(subs_needed):,} steady subscribers for 12 months.")

analyze_finances()