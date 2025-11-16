#!/usr/bin/env python3
"""Debug script to see what's on the Amazon page"""

import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# Test with the ASIN from your screenshot
asin = "B0C2NHPZJF"
url = f'https://www.amazon.in/dp/{asin}'

print(f"Fetching: {url}\n")

resp = requests.get(url, headers=HEADERS, timeout=30)
html = resp.text

# Save the HTML to a file for inspection
with open('debug_page.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✓ Saved full HTML to: debug_page.html\n")

# Look for any mention of warranty/protection
soup = BeautifulSoup(html, 'html.parser')

# Search for protection/warranty related text
keywords = ['Protection Plan', 'Warranty', 'Extended Warranty', 'Acko', 'Onsitego']

print("Searching for protection plan keywords in page:\n")
for keyword in keywords:
    elements = soup.find_all(string=re.compile(keyword, re.IGNORECASE))
    if elements:
        print(f"✓ Found '{keyword}': {len(elements)} occurrences")
        for elem in elements[:2]:  # Show first 2
            text = str(elem).strip()[:100]
            print(f"  - {text}...")
    else:
        print(f"✗ '{keyword}' not found")

# Look for price patterns with rupee symbol
print("\n\nLooking for price patterns (for ₹XXX):")
price_patterns = re.findall(r'([^<>\n]{20,80})\s+for\s+₹\s*([0-9,]+(?:\.\d{2})?)', html[:50000], re.IGNORECASE)
if price_patterns:
    print(f"✓ Found {len(price_patterns)} price patterns")
    for i, (text, price) in enumerate(price_patterns[:5], 1):
        clean_text = re.sub(r'<[^>]+>', '', text).strip()
        print(f"{i}. '{clean_text}' for ₹{price}")
else:
    print("✗ No price patterns found")

print(f"\n\nHTML file saved. Check 'debug_page.html' to see full page content.")
print(f"You can open it in a text editor to search for warranty/protection text.")
