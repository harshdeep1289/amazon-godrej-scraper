#!/usr/bin/env python3
"""Quick test for protection plan extraction"""

import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

def determine_brand_from_plan(plan_text):
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
    if 'extended warranty' in t and 'by' not in t:
        return 'Zopper India'
    if 'total protection' in t and 'by' not in t:
        return 'Zopper India'
    return 'Unknown'

def get_product_plans(asin):
    url = f"https://www.amazon.in/dp/{asin}"
    plans = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')
        
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
            print(f"No protection section found for {asin}")
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
            plans.append({'name': name, 'price': price, 'brand': brand})
            if len(plans) >= 3:
                break
        return plans
    except Exception as e:
        print(f"Error for {asin}: {e}")
        return []

# Test with the sample ASIN from your screenshot
test_asin = "B0C2NHPZJF"
print(f"\n Testing ASIN: {test_asin}")
print(f"URL: https://www.amazon.in/dp/{test_asin}\n")

plans = get_product_plans(test_asin)
if plans:
    print(f"Found {len(plans)} plan(s):")
    for i, plan in enumerate(plans, 1):
        print(f"  {i}. {plan['name']}")
        print(f"     Price: ₹{plan['price']}")
        print(f"     Brand: {plan['brand']}\n")
else:
    print("No plans found!")
