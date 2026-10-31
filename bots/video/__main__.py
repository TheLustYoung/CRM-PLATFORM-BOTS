from bots.common.runner import run
from bots.video import setup

if __name__ == "__main__":
    run("video", setup, [("history", "My downloads"), ("help", "Help")])
