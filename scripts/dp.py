#!/usr/bin/python3

import subprocess
import webbrowser


def main():
    subprocess.Popen("open-webui serve")
    webbrowser.get().open("http://localhost:8080")


if __name__ == "__main__":
    main()
