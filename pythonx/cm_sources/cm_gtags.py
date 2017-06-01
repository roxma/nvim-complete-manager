# -*- coding: utf-8 -*-

# For debugging, use this command to start neovim:
#
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim
#
#
# Please register source before executing any other code, this allow cm_core to
# read basic information about the source without loading the whole module, and
# modules required by this module
from cm import register_source, getLogger, Base
import subprocess

register_source(name='cm-gtags',
                priority=8,
                abbreviation='Gtags',
                word_pattern=r'\w+',
                cm_refresh_patterns=r'\w+')

logger = getLogger(__name__)


class Source(Base):

    GTAGS_DB_NOT_FOUND_ERROR = 3

    def __init__(self, nvim):
        super().__init__(nvim)
        self._checked = False
        self._files = self.nvim.call('tagfiles')

        try:
            from distutils.spawn import find_executable
            if not find_executable("global"):
                self.message('error', "Can't find [global] binary. \
                    Please install global www.gnu.org/s/global/global.html")
        except:
            pass

    def print_global_error(self, global_exitcode):
        if global_exitcode == 1:
            error_message = '[cm-gtags] Error: file does not exists'
        elif global_exitcode == 2:
            error_message = '[cm-gtags] Error: invalid argumnets\n'
        elif global_exitcode == 3:
            error_message = '[cm-gtags] Error: GTAGS not found'
        elif global_exitcode == 126:
            error_message = '[cm-gtags] Error: permission denied\n'
        elif global_exitcode == 127:
            error_message = '[cm-gtags] Error: \'global\' command not found\n'
        else:
            error_message = '[cm-gtags] Error: global command failed\n'

        logger.info("result %s", error_message)

    def is_word_valid_for_search(self, word):
        FORRBIDDEN_CHARACTERS = [
                '^', '$', '{', '}', '(', ')', '.',
                '*', '+', '[', ']', '?', '\\'
                ]

        for forbbiden_char in FORRBIDDEN_CHARACTERS:
            if forbbiden_char in word:
                return False
        return True

    def get_pos(self, lnum, col, src):
        lines = src.split(b'\n')
        pos = 0
        for i in range(lnum-1):
            pos += len(lines[i])+1
        pos += col-1
        return pos

    def cm_refresh(self, info, ctx):
        base = ctx['base']

        if not self.is_word_valid_for_search(base):
            return []

        # invoke global
        command = ['global', '-q', '-c', base]
        proc = subprocess.Popen(command,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL)

        output = proc.communicate(timeout=30)

        global_exitcode = proc.returncode
        if global_exitcode == self.GTAGS_DB_NOT_FOUND_ERROR:
            return []

        if global_exitcode != 0:
            self.print_global_error(global_exitcode)

        matches = output[0].decode('utf8').splitlines()

        logger.info('startcol %s, matches %s', ctx['startcol'], matches)

        self.complete(info, ctx, ctx['startcol'], matches)
