import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup


class WebCrawler:
    def __init__(self):
        self.internal_urls = set()
        self.sub_internal_urls = set()
        self.total_urls_visited = 0

    
    def scrape_with_mod_security_fix(self, url):
        """
        Scrape the HTML content of a webpage and fix Mod_Security errors.
        """
        # Create a session with a custom user-agent header.
        session = requests.Session()
        session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'

        # Send a GET request to the URL.
        response = session.get(url)

        # Check if the response contains a Mod_Security error.
        if response.status_code == 403 and 'mod_security' in response.text:
            # Send a second GET request with a blank Referer header.
            response = session.get(url, headers={'Referer': ''})

        # Parse the HTML content.
        soup = BeautifulSoup(response.content, 'html.parser')

        # Return the parsed HTML content.
        return soup
    

    def get_all_website_links(self, url):
        """
        Returns all URLs that is found on `url` in which it belongs to the same website
        """
        urls = set()
        domain_name = urlparse(url).netloc
        try:
            soup = self.scrape_with_mod_security_fix(url)
            for a_tag in soup.findAll("a"):
                href = a_tag.attrs.get("href")
                if href == "" or href is None:
                    continue
                href = urljoin(url, href)
                parsed_href = urlparse(href)
                href = parsed_href.scheme + "://" + parsed_href.netloc + parsed_href.path
                if not self.is_valid(href):
                    continue
                if self.is_webpage(href) == False:
                    continue
                if href in self.internal_urls:
                    continue
                if domain_name not in href:
                    continue
                urls.add(href)
                self.internal_urls.add(href)
        except:
            pass

        return urls
    
    def get_all_subdomain_links(self, url):
        """
        Returns all URLs that is found on subdomain `url` in which it belongs to the same website
        """
        urls = set()
        domain_name = urlparse(url).netloc + urlparse(url).path
        soup = self.scrape_with_mod_security_fix(url)
        for a_tag in soup.findAll("a"):
            href = a_tag.attrs.get("href")
            if href == "" or href is None:
                continue
            href = urljoin(url, href)
            parsed_href = urlparse(href)
            href = parsed_href.scheme + "://" + parsed_href.netloc + parsed_href.path

            if not self.is_valid(href):
                continue
            if self.is_webpage(href) == False:
                continue
            if href in self.sub_internal_urls:
                continue
            if domain_name not in href:
                continue
            urls.add(href)
            self.sub_internal_urls.add(href)
        return urls

    def crawl(self, url, max_urls=100):
        """
        Crawls a web page and extracts all links.
        """
        self.total_urls_visited += 1
        links = self.get_all_website_links(url)
        for link in links:
            if self.total_urls_visited > max_urls:
                break
            self.crawl(link, max_urls=max_urls)

    def crawl_sub(self, url, max_urls=100):
        """
        Crawls a web page and extracts all links.
        """
        self.total_urls_visited += 1
        links = self.get_all_subdomain_links(url)
        for link in links:
            if self.total_urls_visited > max_urls:
                break
            self.crawl(link, max_urls=max_urls)

    def get_internal_urls(self):
        """
        Returns a set of all internal URLs.
        """
        return self.internal_urls
    
    def get_sub_internal_urls(self):
        """
        Returns a set of all sub internal URLs.
        """
        return self.sub_internal_urls
    
    def is_valid(self, url):
        """
        Checks whether `url` is a valid URL.
        """
        parsed = urlparse(url)
        return bool(parsed.netloc) and bool(parsed.scheme)
    
    def is_webpage(self, url):
        """
        Function to check if a URL points to a webpage based on file extension.
        """
        webpage_extensions = ['.html', '.htm', '.php', '.asp', '.aspx', '.jsp', '.jspx', '.cfm', '.cgi', '.pl', '.shtml', '.xhtml']
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        return any(path.endswith(ext) for ext in webpage_extensions) or not '.' in path


def internal_links_from_url(url):
    """
    Returns a set of all internal URLs from a given URL.
    """
    crawler = WebCrawler()
    crawler.crawl(url)
    return crawler.get_internal_urls()  

def internal_subdomain_links_from_url(url):
    """
    Returns a set of all internal URLs from a given URL.
    """
    crawler = WebCrawler()
    crawler.crawl_sub(url)
    return crawler.get_sub_internal_urls()  

# # Example usage:
# crawler = WebCrawler()
# crawler.crawl("https://www.argyle.co.in")
# internal_urls = crawler.get_internal_urls()
# external_urls = crawler.get_external_urls()
# print("Internal URLs:")
# for url in internal_urls:
#     print(url)
# print("External URLs:")
# for url in external_urls:
#     print(url)

#print(len(internal_links_from_url('https://www.washington.edu/datasciencemasters/')))

#print(internal_subdomain_links_from_url('https://www.washington.edu/datasciencemasters/'))