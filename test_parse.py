import requests
from bs4 import BeautifulSoup

resp = requests.get('https://github.com/trending', headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
soup = BeautifulSoup(resp.text, 'html.parser')
articles = soup.find_all('article', class_='Box-row')
print(f'Articles: {len(articles)}')

for idx, article in enumerate(articles[:5]):
    # Repo name
    h2 = article.find('h2')
    repo_name = ''
    link = ''
    if h2:
        a = h2.find('a')
        if a:
            href = a.get('href', '').strip('/')
            repo_name = href
            link = f"https://github.com/{href}"

    # Description
    desc = ''
    p = article.find('p', class_='color-fg-muted')
    if p:
        desc = p.get_text().strip()

    # Language
    lang = ''
    span = article.find('span', itemprop='programmingLanguage')
    if span:
        lang = span.get_text().strip()

    # Stars
    stars = ''
    stars_link = article.find('a', href=lambda h: h and '/stargazers' in h)
    if stars_link:
        stars = stars_link.get_text().strip()

    # Today stars
    today = ''
    for span in article.find_all('span'):
        text = span.get_text()
        if 'today' in text.lower():
            today = text.strip()
            break

    print(f'\n{idx}: {repo_name}')
    print(f'  Stars: {stars} ({today})')
    print(f'  Lang: {lang}')
    print(f'  Desc: {desc[:80]}')
