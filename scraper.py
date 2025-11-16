#!/usr/bin/env python3
"""
Amazon Product Scraper for Godrej Kitchen Appliances
Extracts product details including ASIN, name, price, rating, and more
Supports pagination and exports to Excel
"""

import random
import requests
from bs4 import BeautifulSoup
import json
import re
import time
from urllib.parse import urlparse, parse_qs, urljoin
import pandas as pd
from datetime import datetime
from email_report import send_report
import os

# Multiple user agents to rotate
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
]

BASE_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

def make_headers():
    return {
        **BASE_HEADERS,
        'User-Agent': random.choice(USER_AGENTS),
    }

def extract_asin_from_url(url):
    """Extract ASIN from product URL"""
    # ASIN pattern in Amazon URLs: /dp/ASIN or /gp/product/ASIN
    pattern = r'/(?:dp|gp/product)/([A-Z0-9]{10})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def extract_asin_from_data_asin(element):
    """Extract ASIN from data-asin attribute"""
    return element.get('data-asin', '')

def determine_brand_from_plan(plan_text):
    """Map plan text to provider brand based on keywords."""
    t = plan_text.lower()
    if 'acko' in t:
        return 'Acko'
    if 'onsitego' in t:
        return 'Onsitego'
    if 'one assist' in t or 'oneassist' in t:
        return 'One Assist'
    if 'zopper' in t:
        return 'Zopper India'
    if 'servify' in t:
        return 'Servify'
    # Default heuristics
    if 'extended warranty' in t and 'by' not in t:
        return 'Zopper India'
    if 'total protection' in t and 'by' not in t:
        return 'Zopper India'
    return 'Unknown'

def get_product_plans(asin, product_name):
    """Fetch up to 3 unique protection plan entries from a product page."""
    url = f"https://www.amazon.in/dp/{asin}"
    plans = []
    try:
        resp = requests.get(url, headers=make_headers(), timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')

        # Locate protection plan section
        protection_section = None
        headings = soup.find_all(['h2','h3','h4','span'], string=re.compile(r'Add a Protection Plan', re.I))
        if headings:
            protection_section = headings[0].find_parent(['div','section'])
        if not protection_section:
            protection_section = soup.find('div', {'id': re.compile(r'warranty|protection', re.I)})
        if not protection_section:
            any_div = soup.find('div', string=re.compile(r'warranty|protection plan', re.I))
            if any_div:
                protection_section = any_div.find_parent('div')

        if not protection_section:
            return []

        seen = set()
        for node in protection_section.find_all(['label','span','div']):
            text = node.get_text(" ", strip=True)
            m = re.search(r'(.+?)\s+for\s+₹\s*([0-9,]+(?:\.\d{2})?)', text, flags=re.I)
            if not m:
                continue
            name = m.group(1).strip()
            if not any(k in name.lower() for k in ['warranty','protection','plan','cleaning','service','installation']):
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            price = float(m.group(2).replace(',', '')) if m.group(2) else None
            brand = determine_brand_from_plan(name)
            plans.append({'Plan Name': name, 'Plan Price': price, 'Plan Brand': brand})
            if len(plans) >= 3:
                break
        return plans
    except requests.exceptions.RequestException:
        return []


def get_next_page_url(soup, current_url):
    """Extract next page URL from pagination"""
    try:
        # Look for the "Next" button/link
        next_button = soup.find('a', {'class': 's-pagination-next'})
        if next_button and next_button.get('href'):
            return urljoin(current_url, next_button['href'])
        
        # Alternative: look for pagination link with specific aria-label
        next_link = soup.find('a', {'aria-label': 'Go to next page'})
        if next_link and next_link.get('href'):
            return urljoin(current_url, next_link['href'])
    except Exception as e:
        print(f"Error finding next page: {e}")
    
    return None

def scrape_amazon_products(url):
    """Scrape product details from Amazon search results"""
    
    print(f"Fetching URL: {url}\n")
    
    try:
        response = requests.get(url, headers=make_headers(), timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check for captcha
        if 'validatecaptcha' in response.text.lower():
            print("\n⚠ Captcha detected - waiting 10 seconds...")
            time.sleep(10)
            return [], None
        
        # Find all product containers
        products = []
        
        # Amazon uses different selectors for product cards
        product_divs = soup.find_all('div', {'data-component-type': 's-search-result'})
        
        # Fallback selector
        if not product_divs:
            product_divs = soup.find_all('div', {'data-asin': True, 'data-index': True})
        
        print(f"Found {len(product_divs)} products\n")
        
        for idx, product_div in enumerate(product_divs, 1):
            try:
                product_data = {}
                
                # Extract ASIN
                asin = extract_asin_from_data_asin(product_div)
                product_data['asin'] = asin
                
                # Extract product title - try multiple selectors
                title_elem = product_div.find('h2')
                if title_elem:
                    title_link = title_elem.find('a')
                    if title_link:
                        product_data['title'] = title_link.get_text(strip=True)
                    else:
                        product_data['title'] = title_elem.get_text(strip=True)
                else:
                    # Try alternative selectors
                    title_span = product_div.find('span', {'class': 'a-size-medium'}) or \
                                product_div.find('span', {'class': 'a-size-base-plus'})
                    product_data['title'] = title_span.get_text(strip=True) if title_span else 'N/A'
                
                # Create simplified product URL using ASIN
                if asin:
                    product_data['url'] = f'https://www.amazon.in/dp/{asin}'
                else:
                    product_data['url'] = 'N/A'
                
                # Extract price
                price_whole = product_div.find('span', {'class': 'a-price-whole'})
                if price_whole:
                    price_fraction = product_div.find('span', {'class': 'a-price-fraction'})
                    price = price_whole.get_text(strip=True).replace(',', '')
                    if price_fraction:
                        price += price_fraction.get_text(strip=True)
                    product_data['price'] = f"₹{price}"
                else:
                    product_data['price'] = 'N/A'
                
                # Extract MRP (original price)
                mrp_elem = product_div.find('span', {'class': 'a-price a-text-price'})
                if mrp_elem:
                    mrp_text = mrp_elem.get_text(strip=True)
                    product_data['mrp'] = mrp_text
                else:
                    product_data['mrp'] = 'N/A'
                
                # Extract discount percentage
                discount_elem = product_div.find('span', string=re.compile(r'\d+%\s+off'))
                if discount_elem:
                    product_data['discount'] = discount_elem.get_text(strip=True)
                else:
                    product_data['discount'] = 'N/A'
                
                # Extract rating
                rating_elem = product_div.find('span', {'class': 'a-icon-alt'})
                if rating_elem:
                    rating_text = rating_elem.get_text(strip=True)
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    product_data['rating'] = rating_match.group(1) if rating_match else 'N/A'
                else:
                    product_data['rating'] = 'N/A'
                
                # Extract number of reviews
                reviews_elem = product_div.find('span', {'class': 'a-size-base'})
                if reviews_elem:
                    reviews_text = reviews_elem.get_text(strip=True)
                    # Look for patterns like (1.2K) or (231)
                    reviews_match = re.search(r'\(([0-9.,KMk]+)\)', reviews_text)
                    product_data['num_reviews'] = reviews_match.group(1) if reviews_match else 'N/A'
                else:
                    product_data['num_reviews'] = 'N/A'
                
                # Extract availability/delivery info
                delivery_elem = product_div.find('span', string=re.compile(r'FREE delivery|delivery'))
                if delivery_elem:
                    product_data['delivery'] = delivery_elem.get_text(strip=True)
                else:
                    product_data['delivery'] = 'N/A'
                
                # Extract product badges (e.g., "Best seller", "Amazon's Choice")
                badge_elem = product_div.find('span', {'class': 'a-badge-label'})
                if badge_elem:
                    product_data['badge'] = badge_elem.get_text(strip=True)
                else:
                    product_data['badge'] = 'N/A'
                
                
                products.append(product_data)
                
                print(f"Product {idx}: {product_data['title'][:60]}... (ASIN: {asin})")
                
            except Exception as e:
                print(f"Error extracting product {idx}: {str(e)}")
                continue
        
        # Get next page URL
        next_page_url = get_next_page_url(soup, url)
        
        return products, next_page_url
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the page: {str(e)}")
        return [], None

def save_to_json(products, filename='amazon_godrej_products.json'):
    """Save products to JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
    print(f"✓ Data saved to {filename}")

def save_to_csv(products, filename='amazon_godrej_products.csv'):
    """Save products to CSV file"""
    import csv
    
    if not products:
        print("No products to save")
        return
    
    keys = products[0].keys()
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(products)
    
    print(f"✓ Data saved to {filename}")

def save_to_excel(products, filename='amazon_godrej_products.xlsx'):
    """Save products to Excel file"""
    if not products:
        print("No products to save")
        return
    
    df = pd.DataFrame(products)
    
    # Create a mapping for better column names
    column_mapping = {
        'asin': 'ASIN',
        'title': 'Product Name',
        'price': 'Current Price',
        'mrp': 'MRP',
        'discount': 'Discount %',
        'rating': 'Rating',
        'num_reviews': 'Number of Reviews',
        'delivery': 'Delivery Info',
        'badge': 'Badge',
        'url': 'Product Link'
    }
    
    # Rename columns that exist in the dataframe
    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
    
    # Reorder columns for better readability
    desired_order = ['ASIN', 'Product Name', 'Current Price', 'MRP', 'Discount %', 
                    'Rating', 'Number of Reviews', 'Delivery Info', 'Badge', 
                    'Product Link']
    
    # Only use columns that exist
    column_order = [col for col in desired_order if col in df.columns]
    df = df[column_order]
    
    # Save to Excel
    df.to_excel(filename, index=False, engine='openpyxl')
    print(f"✓ Data saved to {filename}")

def scrape_all_pages(start_url, max_pages=10):
    """Scrape all pages with pagination support"""
    all_products = []
    current_url = start_url
    page_num = 1
    
    while current_url and page_num <= max_pages:
        print(f"\n{'='*80}")
        print(f"SCRAPING PAGE {page_num}")
        print(f"{'='*80}")
        
        products, next_url = scrape_amazon_products(current_url)
        
        if products:
            all_products.extend(products)
            print(f"\n✓ Page {page_num}: Scraped {len(products)} products")
            print(f"✓ Total products so far: {len(all_products)}")
        else:
            print(f"\n⚠ No products found on page {page_num}")
        
        if not next_url:
            print("\n✓ No more pages found. Scraping complete.")
            break
        
        current_url = next_url
        page_num += 1
        
        # Be polite - add delay between requests (randomized)
        print("\nWaiting before next page...")
        time.sleep(2.5 + random.random() * 2)
    
    return all_products

def attach_plans_and_save(products_df):
    """For each product, fetch up to 3 plans and save a combined Excel report."""
    records = []
    total = len(products_df)
    for idx, row in products_df.iterrows():
        asin = row.get('ASIN')
        name = row.get('Product Name')
        link = row.get('Product Link') or f"https://www.amazon.in/dp/{asin}" if asin else None
        plans = get_product_plans(asin, name)
        # Ensure max 3 entries, fill placeholders if fewer
        while len(plans) < 3:
            plans.append({'Plan Name': None, 'Plan Price': None, 'Plan Brand': None})
        rec = {
            'ASIN': asin,
            'Product Name': name,
            'Current Price': row.get('Current Price'),
            'MRP': row.get('MRP'),
            'Discount %': row.get('Discount %'),
            'Rating': row.get('Rating'),
            'Number of Reviews': row.get('Number of Reviews'),
            'Delivery Info': row.get('Delivery Info'),
            'Badge': row.get('Badge'),
            'Product Link': link,
            'Plan1 Name': plans[0]['Plan Name'], 'Plan1 Price': plans[0]['Plan Price'], 'Plan1 Brand': plans[0]['Plan Brand'],
            'Plan2 Name': plans[1]['Plan Name'], 'Plan2 Price': plans[1]['Plan Price'], 'Plan2 Brand': plans[1]['Plan Brand'],
            'Plan3 Name': plans[2]['Plan Name'], 'Plan3 Price': plans[2]['Plan Price'], 'Plan3 Brand': plans[2]['Plan Brand'],
        }
        records.append(rec)
        if (idx+1) < total:
            time.sleep(2.5)
    out_df = pd.DataFrame(records)
    out_path = 'amazon_godrej_products_with_plans.xlsx'
    out_df.to_excel(out_path, index=False, engine='openpyxl')
    print(f"✓ Data with plans saved to {out_path}")


def main():
    url = "https://www.amazon.in/s?k=godrej&i=kitchen&rh=n%3A976442031%2Cp_123%3A5365053&dc&ds=v1%3A5qd9hpEgVPG5Pl4Mf6Y4kgNn1yhINhAKwqTB4od4cTQ&crid=3L8IMG2PU46QV&qid=1759838119&rnid=91049095031&sprefix=godrej%2Caps%2C355&ref=sr_nr_p_123_1"
    
    print("\n" + "="*80)
    print("AMAZON GODREJ PRODUCTS SCRAPER")
    print("="*80)
    print("This will scrape all pages and save results to Excel, JSON, and CSV")
    print("="*80 + "\n")
    
    # Scrape all pages (max 20 pages to be safe)
    all_products = scrape_all_pages(url, max_pages=20)
    
    if all_products:
        print(f"\n{'='*80}")
        print(f"SCRAPING COMPLETE!")
        print(f"{'='*80}")
        print(f"Total products scraped: {len(all_products)}")
        print(f"{'='*80}\n")
        
        # Save to Excel, JSON, and CSV
        save_to_excel(all_products)
        save_to_json(all_products)
        save_to_csv(all_products)
        
        # Also fetch protection plans and save combined report
        products_df = pd.read_excel('amazon_godrej_products.xlsx')
        attach_plans_and_save(products_df)
        
        # Display summary statistics
        print("\n" + "="*80)
        print("SUMMARY STATISTICS:")
        print("="*80)
        products_with_asin = sum(1 for p in all_products if p.get('asin') and p['asin'] != 'N/A')
        products_with_price = sum(1 for p in all_products if p.get('price') and p['price'] != 'N/A')
        products_with_rating = sum(1 for p in all_products if p.get('rating') and p['rating'] != 'N/A')
        
        print(f"Products with ASIN: {products_with_asin}/{len(all_products)}")
        print(f"Products with Price: {products_with_price}/{len(all_products)}")
        print(f"Products with Rating: {products_with_rating}/{len(all_products)}")
        
        # Try emailing the combined report if configured
        try:
            attachment = "amazon_godrej_products_with_plans.xlsx"
            if not os.path.exists(attachment):
                attachment = "amazon_godrej_products.xlsx" if os.path.exists("amazon_godrej_products.xlsx") else None
            if attachment:
                sent = send_report(
                    attachment,
                    subject=f"Godrej Report {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    body="Automated report attached.",
                )
                if sent:
                    print("✓ Report emailed")
        except Exception as e:
            print(f"⚠️ Email step skipped: {e}")

        # Display sample product
        print("\n" + "="*80)
        print("SAMPLE PRODUCT DATA:")
        print("="*80)
        if all_products:
            for key, value in all_products[0].items():
                print(f"{key:15s}: {str(value)[:60]}..." if len(str(value)) > 60 else f"{key:15s}: {value}")
    else:
        print("\n❌ No products were scraped. The page structure may have changed or there was an error.")

if __name__ == "__main__":
    main()
