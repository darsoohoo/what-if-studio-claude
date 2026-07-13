#!/usr/bin/env python3
"""Wait for the local review server, then open the Studio in the default browser."""

import sys
import time
import urllib.error
import urllib.request
import webbrowser

URL = "http://127.0.0.1:8765/studio/"


def main():
    for _ in range(40):
        try:
            with urllib.request.urlopen(URL, timeout=0.5):
                break
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                print("The review server is running an older build without /studio/.", file=sys.stderr)
                print("Close any hidden python review.py processes, then double-click again.", file=sys.stderr)
                return 1
            time.sleep(0.25)
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.25)
    else:
        print(f"Could not reach the review server at {URL}", file=sys.stderr)
        print("Try: cd pipeline && python review.py", file=sys.stderr)
        return 1

    webbrowser.open(URL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
