#!/usr/bin/env python

import logging
import logging.config
import subprocess
import sys
import time
from threading import Thread

class DwmStarterThread(Thread):
    def __init__(self, daemonic):
        Thread.__init__(self)
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.info("started thread initialization")
        self.daemon = daemonic

    def run(self):
        self._logger.info("starting thread")
        while True:
            self._logger.debug("while true %d", time.time())
            out_path = "~/temp/dwm.out"
            err_path = "~/temp/dwm.err"
            with open(out_path,"ab") as out, open(err_path,"ab") as err:
                p = subprocess.call("dwm", stdout=out, stderr=err)
            time.sleep(3)
        self._logger.info("closing thread")

