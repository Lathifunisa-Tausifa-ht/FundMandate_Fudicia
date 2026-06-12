import zipfile
path = '.temp_crawl4ai_download/crawl4ai-0.8.9-py3-none-any.whl'
with zipfile.ZipFile(path) as z:
    for name in ['crawl4ai/__init__.py', 'crawl4ai/crawlers/__init__.py', 'crawl4ai/crawlers/google_search/crawler.py']:
        print('---', name)
        try:
            data = z.read(name).decode('utf-8')
        except KeyError:
            print('MISSING', name)
            continue
        print('\n'.join(data.splitlines()[:120]))
        print()