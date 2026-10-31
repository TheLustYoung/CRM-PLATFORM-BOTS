from bots.common.runner import run
from bots.media import setup

if __name__ == "__main__":
    run("media", setup, [("history", "My downloads"), ("help", "Help")])
