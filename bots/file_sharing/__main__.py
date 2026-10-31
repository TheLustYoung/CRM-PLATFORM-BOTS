from bots.common.runner import run
from bots.file_sharing import setup

if __name__ == "__main__":
    run("files", setup, [("myfiles", "My files"), ("help", "Help")])
