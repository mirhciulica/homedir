#!/usr/bin/env python

from datetime import datetime
import logging
import logging.config
from queue import Queue
import re
import subprocess
import sys
import time
from threading import Thread

import mpd

DISPLAYED_VALUE_TEMPLATE = "\x06\uE195 \x05{glyph} \x01{value}"

class ThreadCommon(Thread):
    def __init__(self, config_obj, daemonic):
        Thread.__init__(self)
        self._logger = logging.getLogger("DwmStatusThread")
        self._logger.info("started thread initialization")
        self._ok_to_run = True
        self._config_obj = config_obj
        self.daemon = daemonic
        self.displayed_value = ""
        
    def _compute_value(self):
        return "dummy"

    def _update_displayed_value(self, new_value):
        temp_value = str(new_value).format(glyph=self._config_obj['glyph'])
        self.displayed_value = DISPLAYED_VALUE_TEMPLATE.format(
            glyph=self._config_obj['glyph'],
            value=temp_value
        )
        self._logger.debug("new displayed value: %s", self.displayed_value)

    def _run_loop(self):
        raise NotImplementedError

    def run(self):
        self._logger.info("starting thread")
        try:
            self._run_loop()
        except Exception:
            self._logger.exception("Exception in some thread")
        self._logger.info("closing thread")

    def join(self, timeout=None):
        self._logger.info("stoping thread")
        self._ok_to_run = False
        Thread.join(self, timeout)


class MpdThread(ThreadCommon):
    def __init__(self, config_obj, daemonic):
        ThreadCommon.__init__(self, config_obj, daemonic)
        self.mpdSuccess = False
        #self._connect_mpd()

    def _connect_mpd(self):
        while not self.mpdSuccess:
            try:
                self.mpd_client = mpd.MPDClient()
                self.mpd_client.connect("127.0.0.1", 6600)
                self.mpdSuccess = True
                self._logger.info("connected to mpd daemon")
            except:
                self.mpdSuccess = False
                time.sleep(self._config_obj['delay_alt'])
                self._logger.warning(
                    "could not connect to mpd daemon. trying again later"
                )

    def _compute_value(self):
        if self.mpdSuccess:
            return self.mpd_client.status()['state']
        else:
            return "unknown"

    def _run_loop(self):
        while self._ok_to_run:
            self._logger.debug("while true %d", time.time())
            if not  self.mpdSuccess:
                self._connect_mpd()
            self._update_displayed_value(self._compute_value())
            time.sleep(self._config_obj['delay'])


class CpuThread(ThreadCommon):
    def __init__(self, config_obj, daemonic):
        ThreadCommon.__init__(self, config_obj, daemonic)
        
    def _read_proc_stat(self):
        with open("/proc/stat", "r") as f:
            # needing only user, nice, system and idle times
            proc_data = f.readline().split(" ")[2:6]
        return {
            'user':int(proc_data[0]),
            'nice':int(proc_data[1]),
            'system':int(proc_data[2]),
            'idle':int(proc_data[3])
        }


    def _compute_value(self):
        stat_a = self._read_proc_stat()
        total_a = sum(stat_a.values())
        time.sleep(.5)
        stat_b = self._read_proc_stat()
        total_b = sum(stat_b.values())

        stat_diff = (stat_b['idle'] - stat_a['idle'])
        total_diff = (total_b - total_a)

        if abs(total_diff) < 0.00000001:
            return "{:.0%}".format(0)
        else:
            return "{:.0%}".format(1 - stat_diff / total_diff)


    def _run_loop(self):
        while self._ok_to_run:
            self._logger.debug("while true %d", time.time())
            self._update_displayed_value(self._compute_value())
            time.sleep(self._config_obj['delay'])


class MemThread(ThreadCommon):
    def __init__(self, config_obj, daemonic):
        ThreadCommon.__init__(self, config_obj, daemonic)
        
    def _compute_value(self):
        p = subprocess.Popen(["free", "-m"], stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()
        
        fields = re.search(
            r'Mem\:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)',
            str(stdout),re.M
        ).group

        # 1-total, 2-used, 3-free, 4-shared, 5-buffers, 6-cached
        used_mem = (int(fields(2)) - int(fields(5)) - int(fields(6)))
        return "{:.0%}".format(used_mem / int(fields(1)))

    def _run_loop(self):
        while self._ok_to_run:
            self._logger.debug("while true %d", time.time())
            self._update_displayed_value(self._compute_value())
            time.sleep(self._config_obj['delay'])


class TempThread(ThreadCommon):
    def __init__(self, config_obj, daemonic):
        ThreadCommon.__init__(self, config_obj, daemonic)

    def _compute_value(self):
        p = subprocess.Popen(["acpi", "-t"], stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()

        match = re.search('\d+\.\d', str(stdout))

        return "{0}\xb0C".format(match.group())

    def _run_loop(self):
        while self._ok_to_run:
            self._logger.debug("while true %d", time.time())
            self._update_displayed_value(self._compute_value())
            time.sleep(self._config_obj['delay'])


class BatThread(ThreadCommon):
    def __init__(self, config_obj, daemonic):
        ThreadCommon.__init__(self, config_obj, daemonic)

    def _is_on_line(self):
        p = subprocess.Popen(["acpi", "-V"], stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()

        return str(stdout).find("on-line") > 0

    def _compute_value(self):
        p = subprocess.Popen(["acpi", "-b"], stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()

        match = re.search('\d+%', str(stdout))

        return match.group()

    def _update_displayed_value(self, new_value):
        if self._is_on_line():
            self.displayed_value = DISPLAYED_VALUE_TEMPLATE.format(
                glyph=self._config_obj['glyph_alt'],
                value=new_value
            )
        else:
            self.displayed_value = DISPLAYED_VALUE_TEMPLATE.format(
                glyph=self._config_obj['glyph'],
                value=new_value
            )
        self._logger.debug("new displayed value: %s", self.displayed_value)

    def _run_loop(self):
        while self._ok_to_run:
            self._logger.debug("while true %d", time.time())
            self._update_displayed_value(self._compute_value())
            time.sleep(self._config_obj['delay'])


class VolThread(ThreadCommon):
    def __init__(self, config_obj, daemonic):
        ThreadCommon.__init__(self, config_obj, daemonic)

    def _compute_value(self):
        p = subprocess.Popen(
            ["amixer", "-c", "0", "get", "PCM"], 
            stdout=subprocess.PIPE
        )
        stdout, stderr = p.communicate()

        match = re.search('\d+%', str(stdout))

        return match.group()

    def _run_loop(self):
        while self._ok_to_run:
            self._logger.debug("while true %d", time.time())
            self._update_displayed_value(self._compute_value())
            time.sleep(self._config_obj['delay'])


class PacThread(ThreadCommon):
    def __init__(self, config_obj, daemonic):
        ThreadCommon.__init__(self, config_obj, daemonic)
        self._update_displayed_value(0)
        
    def _compute_value(self):
        p = subprocess.Popen(["pacman", "-Qqu"], stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()

        return (len(str(stdout).split("\\n")) - 1)

    def _run_loop(self):
        while self._ok_to_run:
            self._logger.debug("while true %d", time.time())
            time.sleep(self._config_obj['delay'])
            self._update_displayed_value(self._compute_value())
        self._logger.info("closing thread")


class DateTimeThread(ThreadCommon):
    def __init__(self, config_obj, daemonic):
        ThreadCommon.__init__(self, config_obj, daemonic)
        
    def _compute_value(self):
        now = datetime.now()
        return now.strftime("%a %d %b %Y \x05{glyph_alt} \x01%H:%M").format(
            glyph_alt=self._config_obj["glyph_alt"]
        )

    def _run_loop(self):
        while self._ok_to_run:
            self._logger.debug("while true %d", time.time())
            self._update_displayed_value(self._compute_value())
            time.sleep(self._config_obj['delay'])


STATUS_THREADS_CONFIG = [
    {'index':0, 'class':MpdThread, 'glyph':"\uE05C", 'delay':2, 'delay_alt':20},
    {'index':1, 'class':CpuThread, 'glyph':"\uE010", 'delay':2},
    {'index':2, 'class':MemThread,'glyph':"\uE0C5", 'delay':5},
    {'index':3, 'class':TempThread, 'glyph':"\uE0CF", 'delay':3},
    {'index':4, 'class':BatThread, 'glyph':"\uE03E", 'glyph_alt':"\uE042", 'delay':3},
    {'index':5, 'class':VolThread, 'glyph':"\uE0E0", 'delay':10},
    {'index':6, 'class':PacThread, 'glyph':"\uE00F", 'delay':300},
    {'index':7, 'class':DateTimeThread, 'glyph':"\uE01F", 'glyph_alt':"\uE018", 'delay':30}
]

class DwmStatusThread(ThreadCommon):
    def __init__(self, config_obj, daemonic):
        ThreadCommon.__init__(self, config_obj, daemonic)
        self._threads = [
            thread_config['class'](thread_config, self.daemon) \
            for thread_config in STATUS_THREADS_CONFIG
        ]

    def join(self, timeout=None):
        for thread in self._threads:
            thread.join()
            thread = None
        
        self._threads = None
        ThreadCommon.join(self, timeout)

    def _run_loop(self):
        for thread in self._threads:
            thread.start()
        while self._ok_to_run:
            self._logger.debug("while true %d", time.time())
            subprocess.Popen([
                "xsetroot",
                "-name",
                " ".join([thread.displayed_value for thread in self._threads])
            ])
            time.sleep(1)
