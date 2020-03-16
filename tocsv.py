#!/usr/bin/env python3
import os
import csv
import pickle

MAINDIR = os.path.dirname(__file__)
DATADIR = MAINDIR + '/data'
OUTFILE = DATADIR + '/resume_data.csv'
HTMLDIR = 'resumes'

os.makedirs(DATADIR, exist_ok=True)
os.makedirs(os.path.join(DATADIR, HTMLDIR), exist_ok=True)

with open(MAINDIR + '/jobtitles.csv', 'r') as f:
    jobtitle_cache = list(csv.reader(f))[1:]

CACHEFILE = DATADIR + '/cache.pickle'

def _title_data_by_title(job_title):
    for line in jobtitle_cache:
        if line[2].lower() == job_title.lower():
            return {
                'job_title_id': line[0],
                'job_title_category': line[1],
                'job_title_keyword': line[2]
            }
    raise RuntimeError(f"No job_title {job_title}!")

with open(CACHEFILE, 'rb') as f:
    cache = pickle.load(f)

FIELDNAMES = [
    'url',
    'companies_worked',
    'schools_attended',
    'job_titles_held',
    'degrees',
    'resume_content_html',
    'resume_score',
    'job_title_id', 'job_title_category', 'job_title_keyword'] + [
        "similar_resume_1_link", "similar_resume_1_days_since_posted",
        "similar_resume_2_link", "similar_resume_2_days_since_posted",
        "similar_resume_3_link", "similar_resume_3_days_since_posted",
        "html_filename"]

kws = cache["resume_urls_by_kw"].keys()

rows = []
for kw in kws:
    for url in cache["resume_urls_by_kw"][kw]:
        # url = "https://www." + url.split('//')[1]
        if url in cache["url_data"].keys():
            d = cache["url_data"][url]
            title_data = _title_data_by_title(kw)
            d.update(title_data)
            rows.append(d)

with open(OUTFILE, 'w') as f:
    writer = csv.DictWriter(f, FIELDNAMES)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
