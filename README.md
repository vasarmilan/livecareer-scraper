# Environment

Tested with  Python 3.7.5 and scrapy version 1.7.3
Apart from scrapy, the project only uses the standard library.

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
