import display
from crawler import VaultCrawler


def _test_display(vault):
    crawler = VaultCrawler(vault)
    display.focus(crawler)


if __name__ == '__main__':
    _test_display('C:\\mine\\vaults\\projeto_medicina')
