#!/usr/bin/env python3

import multiprocessing

from itaxotools.reference_formatter import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
