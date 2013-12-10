#!/usr/bin/env python

__version__ = "0.7"

import imp
import logging
import logging.config
import os
import sys
import time
import yaml

from dwmstarter import *
from dwmstatus import *

def setup_logging():
    log_path = os.path.join(os.path.dirname(__file__), "log.conf.yaml")
    if os.path.exists(log_path):
        with open(log_path, 'rt') as f:
            config = yaml.load(f.read())
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=logging.DEBUG)

if __name__ == "__main__":
    setup_logging()
    logger=logging.getLogger("root")
    
    if len(sys.argv) == 2 and sys.argv[1] == "daemonic":
        logger.info('daemonic mode')
        daemonic_mode = True
    else:
        logger.info('non-daemonic mode')
        daemonic_mode = False

    status_thread=DwmStatusThread(None, daemonic_mode)
    starter_thread=DwmStarterThread(daemonic_mode)
    starter_thread.start()
    status_thread.start()

    # read dwmstatus module info and last modification time
    (fd, module_path, description) = imp.find_module("dwmstatus")
    logger.debug("dwmstatus module path: %s", module_path)
    modtime = os.stat(module_path).st_mtime
    logger.debug("dwmstatus module last modification time: %s", modtime)

    try:
        while True:
            time.sleep(3)
            new_modtime = os.stat(module_path).st_mtime
            if not new_modtime == modtime:
                logger.debug("dwmstatus module modified at: %s", new_modtime)
                modtime = new_modtime

                status_thread.join()
                status_thread = None

                logger.info("reloading dwmstatus module")
                imp.reload(sys.modules['dwmstatus'])
                from dwmstatus import *
                status_thread=DwmStatusThread(None, daemonic_mode)
                status_thread.start()

    except:
        logger.exception("Main loop exception")

