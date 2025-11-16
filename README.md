# Amazon Godrej Products Scraper

A Python web scraper that extracts product details from Amazon India's Godrej kitchen appliances search results.

## Features

- ✅ Scrapes all product details including:
  - ASIN (Amazon Standard Identification Number)
  - Product Name
  - Current Price
  - MRP (Maximum Retail Price)
  - Discount Percentage
  - Rating
  - Number of Reviews
  - Delivery Information
  - Product Badge (e.g., "Amazon's Choice")
  - Product Link
  - Product Image URL

- ✅ **Multi-page Scraping**: Automatically navigates through all available pages
- ✅ **Multiple Export Formats**: Saves data to Excel (.xlsx), JSON (.json), and CSV (.csv)
- ✅ **Rate Limiting**: Includes delays between requests to be respectful to the server
- ✅ **Error Handling**: Robust error handling for network issues and parsing errors

## Requirements

- Python 3.7+
- Required libraries:
  - `requests` - For making HTTP requests
  - `beautifulsoup4` - For HTML parsing
  - `pandas` - For data manipulation
  - `openpyxl` - For Excel file creation

## Installation

1. Install required packages:
```bash
pip3 install requests beautifulsoup4 pandas openpyxl
```

## Usage

Run the scraper:

```bash
cd /Users/harshdeepsingh/amazon_godrej_scraper
python3 scraper.py
```

The script will:
1. Start scraping from the provided Amazon URL
2. Navigate through all available pages (up to 10 pages)
3. Extract product details from each page
4. Save the results to three files:
   - `amazon_godrej_products.xlsx` (Excel format)
   - `amazon_godrej_products.json` (JSON format)
   - `amazon_godrej_products.csv` (CSV format)

## Output Files

### Excel File (`amazon_godrej_products.xlsx`)
A well-formatted spreadsheet with columns:
- ASIN
- Product Name
- Current Price
- MRP
- Discount %
- Rating
- Number of Reviews
- Delivery Info
- Badge
- Product Link
- Image URL

### JSON File (`amazon_godrej_products.json`)
Raw JSON data for programmatic access.

### CSV File (`amazon_godrej_products.csv`)
Comma-separated values format for easy import into other tools.

## Configuration

You can modify the following parameters in the `main()` function:

- `url`: Change the Amazon search URL to scrape different products
- `max_pages`: Adjust the maximum number of pages to scrape (default: 10)

## Notes

- The scraper includes a 2.5-second delay between page requests to be respectful to Amazon's servers
- If Amazon's page structure changes, the scraper may need updates
- Some products may have missing data (shown as "N/A" in the output)

## Legal & Ethical Considerations

- This scraper is for educational purposes
- Always respect robots.txt and website terms of service
- Don't overload servers with too many requests
- Consider using Amazon's official API for commercial applications

## Troubleshooting

If the scraper doesn't work:

1. **Check Internet Connection**: Ensure you have a stable internet connection
2. **Update Libraries**: Run `pip3 install --upgrade requests beautifulsoup4 pandas openpyxl`
3. **Amazon Structure Changed**: Amazon may have updated their HTML structure. Check the selectors in the code.
4. **Rate Limiting**: If you're blocked, wait some time before trying again

## Author

Created for scraping Godrej kitchen appliances from Amazon India.

## License

MIT License - Use at your own risk.
