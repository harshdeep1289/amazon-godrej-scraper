#!/usr/bin/env python3
"""
Amazon Protection Plans Extractor - Fixed Version
Extracts warranty and protection plan details from Amazon product pages
"""

import random
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from datetime import datetime

# Headers to mimic a browser request
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

BASE_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

def make_headers():
    return {
        **BASE_HEADERS,
        'User-Agent': random.choice(USER_AGENTS),
    }

def is_captcha(html: str) -> bool:
    text = html.lower()
    return (
        'validatecaptcha' in text or
        'enter the characters you see' in text or
        'api-services-support@amazon.com' in text or
        'sorry, we just need to make sure you' in text
    )

def determine_brand_from_plan(plan_text):
    """Determine the brand/provider from the plan text"""
    plan_lower = plan_text.lower()
    
    if 'acko' in plan_lower:
        return 'Acko'
    elif 'onsitego' in plan_lower:
        return 'Onsitego'
    elif 'one assist' in plan_lower or 'oneassist' in plan_lower:
        return 'One Assist'
    elif 'zopper' in plan_lower:
        return 'Zopper India'
    elif 'servify' in plan_lower:
        return 'Servify'
    elif 'extended warranty' in plan_lower and 'by' not in plan_lower:
        return 'Zopper India'
    elif 'total protection' in plan_lower and 'by' not in plan_lower:
        return 'Zopper India'
    else:
        return 'Unknown'

PLAN_PRICE_PATTERN = re.compile(r'(.+?)\s+(?:for|at|from)\s+₹\s*([0-9,]+(?:\.\d{2})?)', re.IGNORECASE)

def extract_protection_plans(asin, product_name):
    """Extract protection plans from a product page"""
    url = f'https://www.amazon.in/dp/{asin}'
    
    print(f"[{asin}] Checking...", end=" ", flush=True)
    
    plans_data = []
    
    try:
        # Try up to 2 attempts in case of captcha/throttling
        html = ''
        for attempt in range(2):
            resp = requests.get(url, headers=make_headers(), timeout=30)
            resp.raise_for_status()
            html = resp.text
            if not is_captcha(html):
                break
            # Backoff and retry with a different UA
            if attempt == 0:
                time.sleep(4 + random.random() * 2)
                continue
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # First, search within an obvious protection section if present
        protection_section = None
        headings = soup.find_all(['h2', 'h3', 'h4', 'span'], string=re.compile(r'Add a Protection Plan', re.IGNORECASE))
        if headings:
            protection_section = headings[0].find_parent(['div', 'section'])
        if not protection_section:
            protection_section = soup.find('div', {'id': re.compile(r'(attach|apx).*(warranty|protection)|warranty|protection', re.IGNORECASE)})

        seen_plans = set()
        plan_count = 0
        
        # Strategy A: parse labels/spans within the section
        containers = (protection_section.find_all(['label', 'span', 'div']) if protection_section else [])
        for node in containers:
            text = node.get_text(' ', strip=True)
            m = PLAN_PRICE_PATTERN.search(text)
            if not m:
                continue
            plan_name = m.group(1).strip()
            price_text = m.group(2)
            # Filter by keywords
            keywords = ['warranty','protection','plan','service','cleaning','installation','year','extended','damage']
            if not any(k in plan_name.lower() for k in keywords):
                continue
            key = plan_name.lower()
            if key in seen_plans or len(plan_name) < 8:
                continue
            seen_plans.add(key)
            try:
                price = float(price_text.replace(',', ''))
            except:
                price = None
            brand = determine_brand_from_plan(plan_name)
            plans_data.append({
                'ASIN': asin,
                'Product Name': product_name,
                'Plan Name': plan_name,
                'Plan Price': price,
                'Plan Brand': brand,
                'Product Link': url
            })
            plan_count += 1
            if plan_count >= 3:
                break

        # Strategy B: broad search across whole HTML/text if still missing
        if plan_count < 3:
            for match in PLAN_PRICE_PATTERN.finditer(soup.get_text("\n")):
                plan_name = match.group(1).strip()
                price_text = match.group(2)
                if len(plan_name) < 8:
                    continue
                if plan_name.lower() in seen_plans:
                    continue
                keywords = ['warranty','protection','plan','service','cleaning','installation','year','extended','damage']
                if not any(k in plan_name.lower() for k in keywords):
                    continue
                seen_plans.add(plan_name.lower())
                try:
                    price = float(price_text.replace(',', ''))
                except:
                    price = None
                brand = determine_brand_from_plan(plan_name)
                plans_data.append({
                    'ASIN': asin,
                    'Product Name': product_name,
                    'Plan Name': plan_name,
                    'Plan Price': price,
                    'Plan Brand': brand,
                    'Product Link': url
                })
                plan_count += 1
                if plan_count >= 3:
                    break

        if plans_data:
            print(f"✓ Found {len(plans_data)} plan(s)")
        else:
            print("⚠ No plans")
            plans_data.append({
                'ASIN': asin,
                'Product Name': product_name,
                'Plan Name': 'No protection plans available',
                'Plan Price': None,
                'Plan Brand': 'N/A',
                'Product Link': url
            })
    
    except Exception as e:
        print(f"❌ Error: {str(e)[:50]}")
        plans_data.append({
            'ASIN': asin,
            'Product Name': product_name,
            'Plan Name': 'Error fetching data',
            'Plan Price': None,
            'Plan Brand': 'N/A',
            'Product Link': url
        })
    
    return plans_data

def main():
    print("\n" + "="*80)
    print("AMAZON PROTECTION PLANS EXTRACTOR")
    print("="*80)
    
    # Load existing products from Excel
    try:
        df_products = pd.read_excel('amazon_godrej_products.xlsx')
        print(f"\n✓ Loaded {len(df_products)} products from amazon_godrej_products.xlsx")
    except Exception as e:
        print(f"\n❌ Error loading products file: {e}")
        print("Make sure 'amazon_godrej_products.xlsx' exists in the current directory")
        return
    
    # Extract ASINs and Product Names
    asins = df_products['ASIN'].tolist()
    product_names = df_products['Product Name'].tolist()
    
    print(f"\nStarting to extract protection plans from {len(asins)} products...")
    print("This will take approximately {:.1f} minutes".format(len(asins) * 3 / 60))
    print("="*80 + "\n")
    
    all_plans = []
    
    for idx, (asin, product_name) in enumerate(zip(asins, product_names), 1):
        print(f"[{idx}/{len(asins)}] ", end="")
        
        plans = extract_protection_plans(asin, product_name)
        all_plans.extend(plans)
        
        if idx < len(asins):
            time.sleep(3)
    
    df_plans = pd.DataFrame(all_plans)
    
    # Save to Excel
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filename = f'protection_plans_{timestamp}.xlsx'
    
    df_plans.to_excel(output_filename, index=False, engine='openpyxl')
    
    print("\n" + "="*80)
    print("EXTRACTION COMPLETE!")
    print("="*80)
    print(f"\nTotal products processed: {len(asins)}")
    print(f"Total rows in output: {len(all_plans)}")
    print(f"\n✓ Data saved to: {output_filename}")
    
    print("\n" + "="*80)
    print("SUMMARY:")
    print("="*80)
    
    products_with_plans = df_plans[~df_plans['Plan Name'].isin(['No protection plans available', 'Error fetching data'])].shape[0]
    products_without_plans = df_plans[df_plans['Plan Name'] == 'No protection plans available'].shape[0]
    errors = df_plans[df_plans['Plan Name'] == 'Error fetching data'].shape[0]
    
    print(f"Rows with protection plans: {products_with_plans}")
    print(f"Products without plans: {products_without_plans}")
    print(f"Errors: {errors}")
    
    if len(df_plans[df_plans['Plan Brand'] != 'N/A']) > 0:
        print("\nPlans by Brand:")
        brand_counts = df_plans[df_plans['Plan Brand'] != 'N/A']['Plan Brand'].value_counts()
        for brand, count in brand_counts.items():
            print(f"  - {brand}: {count} plans")
    
    print("\n" + "="*80)
    print(f"✅ Complete! Open '{output_filename}' to view all protection plans.")
    print("="*80)

if __name__ == "__main__":
    main()
