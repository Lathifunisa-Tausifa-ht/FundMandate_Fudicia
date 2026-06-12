import requests
from bs4 import BeautifulSoup
url = 'https://www.screener.in/register/?next=/user/quick_ratios/%3Fnext%3D/company/TCS/consolidated/'
r = requests.get(url, headers={'User-Agent':'Mozilla/5.0'})
print('status', r.status_code)
soup = BeautifulSoup(r.text, 'html.parser')
for form in soup.find_all('form'):
    print('form', form.get('action'))
    for inp in form.find_all('input'):
        print('  input', inp.get('name'), inp.get('type'), inp.get('value'))
