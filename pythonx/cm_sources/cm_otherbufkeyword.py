#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Stefan Haller <fgrsnau@gmail.com>

from cm import register_source
register_source(name='cm-otherbufkeyword',
                priority=4,
                abbreviation='Bufs',
                events=['BufAdd', 'BufDelete', 'BufLeave'],)

from cm import getLogger, Base
import re
import cm_default

logger = getLogger(__name__)

class Source(Base):

    class BufferData:
        __sltos__ = ('changed', 'changedtick', 'deleted', 'words')

        def __init__(self):
            self.changed = False
            self.deleted = False
            self.words = set()

    def __init__(self, nvim):
        super(Source,self).__init__(nvim)
        self._compiled = re.compile(r'\w+')
        self._buffers = {}
        self.update()

    def update(self):
        for buf in self._buffers.values():
            buf.deleted = True

        for buf in self.nvim.buffers:
            schedule_update = (not buf.number in self._buffers) or \
                (self._buffers[buf.number].changed)
            if schedule_update:
                self._buffers[buf.number] = self.rescan_buffer(buf)
            self._buffers[buf.number].deleted = False

        self._buffers = { k:v for k, v in self._buffers.items() if not v.deleted }

    def rescan_buffer(self, buf):
        result = self.BufferData()
        logger.info('rescan_buffer(%s)', buf.number)

        for line in buf:
            for word in self._compiled.finditer(line):
                result.words.add(word.group())

        logger.info('keyword refresh complete, count: %s', len(result.words))
        return result

    def cm_event(self, event, ctx, *args):
        if event == 'BufLeave':
            buf = self._buffers[ctx['bufnr']]
            buf.changed = True
        self.update()

    def cm_refresh(self, info, ctx):
        def gen():
            for num, buf in self._buffers.items():
                # current buffer is handled by different source
                if num != ctx['bufnr']:
                    for word in buf.words:
                        yield word

        matches = (dict(word=word, icase=1) for word in gen())
        matches = self.matcher.process(info, ctx, ctx['startcol'], matches)

        self.complete(info, ctx, ctx['startcol'], matches)
