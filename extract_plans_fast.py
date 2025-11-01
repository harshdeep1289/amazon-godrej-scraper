#!/usr/bin/env python3
"""
Fast Amazon Protection Plans Extractor
Optimized version with better performance
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from datetime import datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

def get_brand(text):
    """Quick brand detection"""
    t = text.lower()
    if 'acko' in t: return 'Acko'
    if 'onsitego' in t: return 'Onsitego'
    if 'one assist' in t: return 'One Assist'
    if 'zopper' in t: return 'Zopper India'
    if 'servify' in t: return 'Servify'
    if 'extended warranty' in t and 'by' not in t: return 'Zopper India'
    if 'total protection' in t and 'by' not in t: return 'Zopper India'
    return 'Unknown'

def extract_plans(asin, name):
    """Fast plan extraction"""
    url = f'https://www.amazon.in/dp/{asin}'
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        
        # Get page HTML as text
        html = resp.text
        
        # Find all warranty/protection plan patterns with regex
        # Pattern: "text for ₹price"
        pattern = r'([^<>\n]{10,200}?)\s+(?:for|at|from)\s+₹\s*([0-9,]+(?:\.\d{2})?)'
        matches = re.findall(pattern, html, re.IGNORECASE)
        
        plans = []
        seen = set()
        
        for plan_text, price_text in matches:
            # Clean the text
            plan_name = re.sub(r'<[^>]+>', '', plan_text).strip()
            plan_name = re.sub(r'\s+', ' ', plan_name)
            
            # Must contain warranty/protection keywords
            keywords = ['warranty', 'protection', 'plan', 'year', 'extended', 'service', 'cleaning']
            if not any(k in plan_name.lower() for k in keywords):
                continue
            
            # Skip duplicates
            key = plan_name.lower()
            if key in seen or len(plan_name) < 10:
                continue
            
            seen.add(key)
            
            try:
                price = float(price_text.replace(',', ''))
            except:
                price = None
            
            brand = get_brand(plan_name)
            
            plans.append({
                'Plan Name': plan_name,
                'Plan Price': price,
                'Plan Brand': brand
            })
            
            if len(plans) >= 3:
                break
        
        return plans
        
    except Exception as e:
        return []

def main():
    print("\n" + "="*80)
    print("FAST PROTECTION PLANS EXTRACTOR")
    print("="*80)
    
    try:
        df = pd.read_excel('amazon_godrej_products.xlsx')
        print(f"\n✓ Loaded {len(df)} products")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return
    
    print(f"\nProcessing {len(df)} products (Est. time: ~{len(df)*2/60:.1f} minutes)")
    print("="*80 + "\n")
    
    results = []
    
    for idx, row in df.iterrows():
        asin = row['ASIN']
        name = row['Product Name']
        
        print(f"[{idx+1}/{len(df)}] {asin}...", end=" ", flush=True)
        
        plans = extract_plans(asin, name)
        
        # Ensure exactly 3 plan slots (fill with None if less)
        while len(plans) < 3:
            plans.append({'Plan Name': None, 'Plan Price': None, 'Plan Brand': None})
        
        # Limit to 3 plans
        plans = plans[:3]
        
        result = {
            'ASIN': asin,
            'Product Name': name,
            'Current Price': row.get('Current Price'),
            'MRP': row.get('MRP'),
            'Discount %': row.get('Discount %'),
            'Rating': row.get('Rating'),
            'Number of Reviews': row.get('Number of Reviews'),
            'Product Link': row.get('Product Link'),
            
            'Plan 1 Name': plans[0]['Plan Name'],
            'Plan 1 Price': plans[0]['Plan Price'],
            'Plan 1 Brand': plans[0]['Plan Brand'],
            
            'Plan 2 Name': plans[1]['Plan Name'],
            'Plan 2 Price': plans[1]['Plan Price'],
            'Plan 2 Brand': plans[1]['Plan Brand'],
            
            'Plan 3 Name': plans[2]['Plan Name'],
            'Plan 3 Price': plans[2]['Plan Price'],
            'Plan 3 Brand': plans[2]['Plan Brand'],
        }
        
        results.append(result)
        
        if plans[0]['Plan Name']:
            print(f"✓ {len([p for p in plans if p['Plan Name']])} plan(s)")
        else:
            print("⚠ No plans")
        
        # Delay between requests
        if idx + 1 < len(df):
            time.sleep(2)
    
    # Save results
    output_df = pd.DataFrame(results)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'godrej_products_with_plans_{timestamp}.xlsx'
    
    output_df.to_excel(output_file, index=False, engine='openpyxl')
    
    print("\n" + "="*80)
    print("COMPLETE!")
    print("="*80)
    
    # Stats
    with_plans = sum(1 for r in results if r['Plan 1 Name'] is not None)
    print(f"\nProducts processed: {len(results)}")
    print(f"Products with plans: {with_plans}")
    print(f"Products without plans: {len(results) - with_plans}")
    
    print(f"\n✓ Saved to: {output_file}")
    print("="*80)
    
    # Copy to desktop
    import shutil
    desktop_path = f'/Users/harshdeepsingh/Desktop/{output_file}'
    shutil.copy(output_file, desktop_path)
    print(f"✓ Also copied to Desktop: {output_file}")

if __name__ == "__main__":
    main()
