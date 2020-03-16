import scrapy
import csv
import os
from os.path import dirname
import re
import pickle
import urllib.parse
from math import ceil

ROOTDIR = dirname(dirname(dirname(__file__)))
DATADIR = ROOTDIR + '/data'
HTMLDIR = 'resumes'

os.makedirs(DATADIR, exist_ok=True)
os.makedirs(os.path.join(DATADIR, HTMLDIR), exist_ok=True)

with open(ROOTDIR + '/jobtitles.csv', 'r') as f:
    jobtitle_cache = list(csv.reader(f))[1:]

CACHEFILE = DATADIR + '/cache.pickle'

def _construct_search_urls(jobtitle, be_trick=False):
    base_url = 'https://www.livecareer.com/resume-search/search?'
    jobtitle = jobtitle.lower().replace(' ', '-')
    jt = jobtitle
    if be_trick:
        urls = []
        for be in (0, 5, 15, 20, 25):
            ee = 100 if be == 25 else be + 5
            url_end = urllib.parse.urlencode({
                'jt': jt, 'be': be, 'ee': ee
            })
            urls.append(base_url + url_end)
    else:
        return base_url + urllib.parse.urlencode({'jt': jt})
    return urls

def _load_cache():
    if os.path.isfile(CACHEFILE):
        with open(CACHEFILE, 'rb') as f:
            return pickle.load(f)
    else:
        jobtitles = [title[2] for title in jobtitle_cache]
        all_query_urls = [_construct_search_urls(title) for title in jobtitles]
        all_query_trick_urls = sum(
            [_construct_search_urls(title, be_trick=True)
             for title in jobtitles], [])
        return {
            'resume_urls_by_kw': {
                title: [] for title in jobtitles
            },
            'query_url_by_kw': {
                title: _construct_search_urls(title)
                for title in jobtitles
            },
            'trick_urls_by_kw': {
                title: _construct_search_urls(title, True)
                for title in jobtitles
            },
            'page_nums_by_query_url': {
                query_url: None for query_url in all_query_urls
                + all_query_trick_urls
            },
            'url_data': dict()
        }

def _save_cache(cache):
    with open(CACHEFILE, 'wb') as f:
        pickle.dump(cache, f)

def _get_num(string, strict=True):
    string = string or ''
    found = re.findall('\d+', string)
    if found:
        return int(found[0])
    else:
        if strict:
            raise RuntimeError('No number in string')
        return 0


class QueryScraper(scrapy.Spider):
    # gets number of pages per query URL
    name = "query_numpage"

    def start_requests(self):
        cache = _load_cache()
        urls = list(cache['page_nums_by_query_url'].keys())
        for url in urls:
            if cache['page_nums_by_query_url'][url] is None:
                yield scrapy.Request(
                    url=url, callback=self.parse)
            else:
                self.log(f"{url} already cached")

    def parse(self, response):
        self.log(f"url {response.url} crawled")
        cache = _load_cache()
        resume_n = response.css('h4.disp-table-cell::text').get()
        resume_n = ceil(_get_num(resume_n, strict=False) / 10)
        cache['page_nums_by_query_url'][response.url] = resume_n
        _save_cache(cache)

def _get_query_urls_dict():
    cache = _load_cache()
    jobtitles = [title[2] for title in jobtitle_cache]
    res = dict()
    for title in jobtitles:
        res[title] = []
        base_url = cache['query_url_by_kw'][title]
        urls_nopg = [base_url]
        base_pages = cache['page_nums_by_query_url'][base_url]
        if base_pages >= 20:
            # adding trick urls
            urls_nopg += cache['trick_urls_by_kw'][title]
        for url_nopg in urls_nopg:
            pages_num = cache["page_nums_by_query_url"][url_nopg]
            for i in range(1, min(21, pages_num+1)):
                res[title].append(
                    f"{url_nopg}&pg={i}"
                )
    return res

def _get_query_urls():
    res = []
    d = _get_query_urls_dict()
    for key in d:
        for url in d[key]:
            res.append((key, url))
    return res

class ResumeUrlScraper(scrapy.Spider):
    name = "resume_urls"

    def start_requests(self):
        for title, url in _get_query_urls():
            yield scrapy.Request(
                url=url, callback=self.parse,
                meta={'job_title': title})

    def parse(self, response):
        title = response.meta['job_title']
        cache = _load_cache()
        # get URLs from page
        elems = response.css('ul.resume-list > li > a')
        urls = [
            'https://www.livecareer.com' +\
            elem.attrib['href'] for elem in elems
        ]
        cache['resume_urls_by_kw'][title] =\
            set(cache['resume_urls_by_kw'][title]) | set(urls)
        _save_cache(cache)

def _get_all_urls():
    cache = _load_cache()
    urls = set()
    for val in cache["resume_urls_by_kw"].values():
        urls = urls | set(val)
    return list(urls)

class ResumeSpider(scrapy.Spider):
    name = "resume"

    def start_requests(self):
        urls = _get_all_urls()
        cache = _load_cache()
        self.log(cache['url_data'].keys())
        for url in urls:
            if url in cache['url_data'].keys():
                self.log(f"{url} url already cached")
            else:
                try:
                    yield scrapy.Request(
                        url=url, callback=self.parse)
                except Exception as e:
                    print(f"{url} failed with error {repr(e)}")

    def parse(self, response):
        self.log(f'url scraped: {response.url}\n\n')
        similar_resumes = response.css('.margin-bottom > div.col-sm-4')
        hrefs = []
        days_agos = []
        for resume in similar_resumes:
            hrefs.append(resume.css('a').attrib['href'])
            days_agos.append(
                _get_num(resume.css('p.thumbnail-info').get())
            )
        res = response.css(
            'div.font14 ul.mt10')
        # in order: 1) companies, 2) job titles held, 3) school attended
        # 4) degrees
        elems = []
        for sel in res:
            li_contents = sel.css('li::text').getall()
            span_contents = sel.css('span::text').getall()
            elems.append('\n'.join(li_contents + span_contents))
        document = response.css('#document').get()
        resume_score = response.css('h3.resume-score::text').get()
        resume_score = _get_num(resume_score, False)
        style_tags = response.css('head > style').getall()
        style_tags += response.css('head > link').getall()
        d = {
            'url': response.url,
            'companies_worked': elems[0],
            'schools_attended': elems[1],
            'job_titles_held': elems[2],
            'degrees': elems[3],
            'resume_content_html': document,
            'resume_score': resume_score,
        }
        style = '\n'.join(style_tags)
        html_filecontent = f"""
        <html>
            <head>
                {style}
            </head>
            <body>
                {d['resume_content_html']}
            </body>
        </html>
        """
        html_filename = HTMLDIR + '/' +\
            str(abs(hash(html_filecontent))) + '.html'
        d["html_filename"] = html_filename
        with open(DATADIR + '/' + html_filename, 'w') as f:
            f.write(html_filecontent)
        for i in range(1, 4):
            d[f'similar_resume_{i}_days_since_posted'] = days_agos[i-1]
            d[f'similar_resume_{i}_link'] = hrefs[i-1]
        cache = _load_cache()
        cache["url_data"][response.url] = d
        _save_cache(cache)
