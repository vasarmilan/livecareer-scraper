# Environment

Test environment:
1. Python 3.7.5
2. scrapy version 1.7.3
3. scrapy-rotating-proxies version 0.6.2

# Usage

Execute following commands with working directory set to the package root directory:

1. gather query metadata:
   `scrapy crawl query_numpage`
2. build resume link database: 
   `scrapy crawl resume_urls`
3. extract resume data: 
   `scrapy crawl resume`
4. export to CSV:
   `python3 ./tocsv.py`
