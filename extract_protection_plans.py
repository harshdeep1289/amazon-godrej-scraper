#!/usr/bin/env python3
"""
Amazon Protection Plans Extractor
Extracts warranty and protection plan details from Amazon product pages
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from datetime import datetime

# Headers to mimic a browser request
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

def determine_brand_from_plan(plan_text):
    """Determine the brand/provider from the plan text"""
    plan_lower = plan_text.lower()
    
    # Check for specific brand mentions
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
    # If no specific brand mentioned, likely Zopper India (Amazon's default)
    elif 'extended warranty' in plan_lower and 'by' not in plan_lower:
        return 'Zopper India'
    elif 'total protection' in plan_lower and 'by' not in plan_lower:
        return 'Zopper India'
    else:
        return 'Unknown'

def extract_price_from_text(text):
    """Extract price value from text like '₹899.00' or '₹299'"""
    # Remove rupee symbol and commas, extract number
    match = re.search(r'₹\s*([0-9,]+\.?\d*)', text)
    if match:
        price_str = match.group(1).replace(',', '')
        try:
            return float(price_str)
        except:
            return None
    return None

def extract_protection_plans(asin, product_name):
    """Extract protection plans from a product page"""
    url = f'https://www.amazon.in/dp/{asin}'
    
    print(f"\n{'='*80}")
    print(f"Processing: {asin}")
    print(f"Product: {product_name[:60]}...")
    print(f"URL: {url}")
    
    plans_data = []
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for protection plan section
        # Try multiple selectors to find the protection plans
        protection_section = None
        
        # Method 1: Look for "Add a Protection Plan" heading
        headings = soup.find_all(['h2', 'h3', 'h4', 'span'], string=re.compile(r'Add a Protection Plan', re.IGNORECASE))
        if headings:
            protection_section = headings[0].find_parent(['div', 'section'])
        
        # Method 2: Look for warranty-related divs
        if not protection_section:
            protection_section = soup.find('div', {'id': re.compile(r'warranty|protection', re.IGNORECASE)})
        
        # Method 3: Search for elements with warranty text
        if not protection_section:
            warranty_divs = soup.find_all('div', string=re.compile(r'warranty|protection plan', re.IGNORECASE))
            if warranty_divs:
                protection_section = warranty_divs[0].find_parent('div')
        
        if protection_section:
            # Find all text that matches protection plan patterns
            # Look for labels associated with checkboxes or radio buttons
            plan_labels = protection_section.find_all(['label', 'span', 'div'])
            
            seen_plans = set()  # To avoid duplicates
            
            for label in plan_labels:
                text = label.get_text(strip=True)
                
                # Pattern to match protection plans with prices
                # Examples: "2Year Extended Warranty Plan for ₹899.00"
                #          "1 Year Extended warranty by Acko for ₹299.00"
                pattern = r'(.+?)\s+for\s+₹\s*([0-9,]+\.?\d*)'
                match = re.search(pattern, text)
                
                if match:
                    plan_name = match.group(1).strip()
                    price_text = match.group(2)
                    
                    # Skip if we've already seen this plan (avoid duplicates)
                    plan_key = plan_name.lower()
                    if plan_key in seen_plans:
                        continue
                    
                    # Skip if it's not a warranty/protection plan
                    if not any(keyword in plan_name.lower() for keyword in 
                             ['warranty', 'protection', 'plan', 'service', 'cleaning', 'installation']):
                        continue
                    
                    seen_plans.add(plan_key)
                    
                    # Extract price
                    try:
                        price = float(price_text.replace(',', ''))
                    except:
                        price = None
                    
                    # Determine brand
                    brand = determine_brand_from_plan(plan_name)
                    
                    plans_data.append({
                        'ASIN': asin,
                        'Product Name': product_name,
                        'Plan Name': plan_name,
                        'Plan Price': price,
                        'Plan Brand': brand,
                        'Product Link': url
                    })
                    
                    print(f"  ✓ Found: {plan_name} | Price: ₹{price} | Brand: {brand}")
                    
                    # Limit to max 3 plans per product
                    if len(plans_data) >= 3:
                        break
        
        if not plans_data:
            # Broader regex: also match "at"/"from ₹" and search whole page text
            PAT = re.compile(r'(.+?)\s+(?:for|at|from)\s+₹\s*([0-9,]+(?:\.\d{2})?)', re.IGNORECASE)
            for m in PAT.finditer(soup.get_text("\n")):
                plan_name = m.group(1).strip()
                price_text = m.group(2)
                if len(plan_name) < 8:
                    continue
                if not any(keyword in plan_name.lower() for keyword in ['warranty','protection','plan','service','cleaning','installation','year','extended','damage']):
                    continue
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
                if len(plans_data) >= 3:
                    break
        
        if not plans_data:
            print(f"  ⚠ No protection plans found")
            # Add a row indicating no plans found
            plans_data.append({
                'ASIN': asin,
                'Product Name': product_name,
                'Plan Name': 'No protection plans available',
                'Plan Price': None,
                'Plan Brand': 'N/A',
                'Product Link': url
            })
    
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Error fetching page: {str(e)}")
        plans_data.append({
            'ASIN': asin,
            'Product Name': product_name,
            'Plan Name': 'Error fetching data',
            'Plan Price': None,
            'Plan Brand': 'N/A',
            'Product Link': url
        })
    except Exception as e:
        print(f"  ❌ Error parsing page: {str(e)}")
        plans_data.append({
            'ASIN': asin,
            'Product Name': product_name,
            'Plan Name': 'Error parsing data',
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
    print("This will take some time as we need to visit each product page.")
    print("="*80)
    
    all_plans = []
    
    for idx, (asin, product_name) in enumerate(zip(asins, product_names), 1):
        print(f"\nProgress: {idx}/{len(asins)}")
        
        # Extract protection plans for this product
        plans = extract_protection_plans(asin, product_name)
        all_plans.extend(plans)
        
        # Be polite - add delay between requests (3 seconds)
        if idx < len(asins):
            print(f"\nWaiting 3 seconds before next request...")
            time.sleep(3)
    
    # Create DataFrame from all plans
    df_plans = pd.DataFrame(all_plans)
    
    # Save to Excel
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filename = f'protection_plans_{timestamp}.xlsx'
    
    df_plans.to_excel(output_filename, index=False, engine='openpyxl')
    
    print("\n" + "="*80)
    print("EXTRACTION COMPLETE!")
    print("="*80)
    print(f"\nTotal products processed: {len(asins)}")
    print(f"Total protection plans found: {len(all_plans)}")
    print(f"\n✓ Data saved to: {output_filename}")
    
    # Summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS:")
    print("="*80)
    
    products_with_plans = len(df_plans[df_plans['Plan Name'] != 'No protection plans available'])
    products_without_plans = len(df_plans[df_plans['Plan Name'] == 'No protection plans available'])
    
    print(f"Products with protection plans: {products_with_plans}")
    print(f"Products without protection plans: {products_without_plans}")
    
    if len(df_plans[df_plans['Plan Brand'] != 'N/A']) > 0:
        print("\nPlans by Brand:")
        brand_counts = df_plans[df_plans['Plan Brand'] != 'N/A']['Plan Brand'].value_counts()
        for brand, count in brand_counts.items():
            print(f"  - {brand}: {count} plans")
    
    # Display sample data
    print("\n" + "="*80)
    print("SAMPLE DATA (First 3 rows):")
    print("="*80)
    print(df_plans[['ASIN', 'Plan Name', 'Plan Price', 'Plan Brand']].head(3).to_string(index=False))
    
    print("\n" + "="*80)
    print(f"✅ Complete! Open '{output_filename}' to view all protection plans.")
    print("="*80)

if __name__ == "__main__":
    main()
