
from os import path

import settings
from crawler import VaultCrawler
from display import mainloop


def _main():
    # ../../settings.txt
    root = path.dirname((path.dirname(path.abspath(__file__))))
    filepath = path.join(root, 'settings.txt')

    settings.update_with_user_settings(filepath)

    crawler = VaultCrawler(settings.VAULT)
    mainloop(crawler)



if __name__ == '__main__':
    _main()
