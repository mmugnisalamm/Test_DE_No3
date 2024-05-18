import requests
from bs4 import BeautifulSoup
import re
import time
import json
import os

class WikipediaScraper:
    def __init__(self, start_urls, output_file='scraped_data.json'):
        self.start_urls = start_urls
        self.scraped_urls = set()
        self.to_scrape_urls = set(start_urls)
        self.scraping = True
        self.output_file = output_file
        self.data = []

        # Load previously scraped data if it exists
        if os.path.exists(self.output_file):
            with open(self.output_file, 'r') as file:
                self.data = json.load(file)
                self.scraped_urls = {item['url'] for item in self.data}
                print(f"Loaded {len(self.scraped_urls)} scraped URLs from previous sessions.")

    def get_article_details(self, url):
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Title
        title = soup.find('h1', {'id': 'firstHeading'}).text

        # Body
        body = soup.find('div', {'id': 'bodyContent'}).text

        # Related Links
        related_links = set()
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('/wiki/') and not href.startswith(('/wiki/Special:', '/wiki/Help:', '/wiki/Template:', '/wiki/Category:', '/wiki/File:', '/wiki/Portal:', '/wiki/Talk:')):
                full_url = 'https://en.wikipedia.org' + href
                if full_url not in self.scraped_urls:
                    related_links.add(full_url)

        # Creation date
        creation_date = None
        for li in soup.find_all('li'):
            if li.find('a', href=re.compile('/history')):
                history_link = 'https://en.wikipedia.org' + li.find('a')['href']
                history_response = requests.get(history_link)
                history_soup = BeautifulSoup(history_response.text, 'html.parser')
                for history_li in history_soup.find_all('li', {'class': 'mw-history-histlinks'}):
                    timestamp = history_li.find('a', {'class': 'mw-changeslist-date'})
                    if timestamp:
                        creation_date = timestamp.text
                        break
                if creation_date:
                    break

        return {
            'url': url,
            'title': title,
            'body': body,
            'related_links': list(related_links),
            'creation_date': creation_date
        }

    def scrape(self):
        while self.scraping and self.to_scrape_urls:
            current_url = self.to_scrape_urls.pop()
            if current_url in self.scraped_urls:
                continue

            try:
                print(f'Scraping: {current_url}')
                details = self.get_article_details(current_url)
                self.data.append(details)
                self.save_data()  # Save data after each successful scrape

                self.scraped_urls.add(current_url)
                self.to_scrape_urls.update(details['related_links'])

            except Exception as e:
                print(f'Error scraping {current_url}: {e}')
            time.sleep(1)  # To avoid overwhelming the server

    def save_data(self):
        with open(self.output_file, 'w') as file:
            json.dump(self.data, file, indent=4)

    def stop(self):
        self.scraping = False
        self.save_data()  # Save data when stopping

def read_urls_from_file(file_path):
    with open(file_path, 'r') as file:
        urls = file.read().splitlines()
    return urls

if __name__ == '__main__':
    start_urls = read_urls_from_file('links.txt')
    scraper = WikipediaScraper(start_urls)
    try:
        scraper.scrape()
    except KeyboardInterrupt:
        print('Scraping stopped by user.')
        scraper.stop()
