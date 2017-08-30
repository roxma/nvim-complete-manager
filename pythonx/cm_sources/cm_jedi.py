# -*- coding: utf-8 -*-

# For debugging
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim

from __future__ import absolute_import
import os

py = 'python3'

# detect python2
if 'VIRTUAL_ENV' in os.environ:
    py2 = os.path.join(os.environ['VIRTUAL_ENV'], 'bin', 'python2')
    if os.path.isfile(py2):
        py = 'python2'

from cm import register_source, getLogger, Base
register_source(name='cm-jedi',
                priority=9,
                abbreviation='Py',
                scoping=True,
                scopes=['python'],
                multi_thread=0,
                # disable early cache to minimize the issue of #116
                # early_cache=1,
                # The last two patterns is for displaying function signatures r'\(\s?', r',\s?'
                cm_refresh_patterns=[r'^(import|from).*\s', r'\.', r'\(\s?', r',\s?'],
                python=py,)

import re
import jedi

logger = getLogger(__name__)

class Source(Base):

    def __init__(self,nvim):
        Base.__init__(self, nvim)
        self._snippet_engine = nvim.vars['cm_completed_snippet_engine']

        # workaround for #62
        try:
            import resource
            import psutil
            mem = psutil.virtual_memory()
            resource.setrlimit(resource.RLIMIT_DATA, (mem.total/3, resource.RLIM_INFINITY))
        except Exception as ex:
            logger.exception("set RLIMIT_DATA failed. %s", ex)
            pass

    def cm_refresh(self,info,ctx,*args):

        path = ctx['filepath']
        typed = ctx['typed']

        # Ignore comment, also workaround jedi's bug #62
        if re.match(r'\s*#', typed):
            return

        src = self.get_src(ctx)
        if not src.strip():
            # empty src may possibly block jedi execution, don't know why
            logger.info('ignore empty src [%s]', src)
            return

        logger.info('context [%s]', ctx)

        # logger.info('jedi.Script lnum[%s] curcol[%s] path[%s] [%s]', lnum,len(typed),path,src)
        script = jedi.Script(src, ctx['lnum'], len(ctx['typed']), path)

        signature_text = ''
        signature = None
        try:
            signatures = script.call_signatures()
            logger.info('signatures: %s', signatures)
            if len(signatures)>0:
                signature = signatures[-1]
                params=[param.description for param in signature.params]
                signature_text = signature.name + '(' + ', '.join(params) + ')'
                logger.info("signature: %s, name: %s", signature, signature.name)
        except Exception as ex:
            logger.exception("get signature text failed %s", signature_text)

        is_import = False
        if re.search(r'^\s*(from|import)', typed):
            is_import = True

        if re.search(r'^\s*(?!from|import).*?[(,]\s*$', typed):
            if signature_text:
                matches = [dict(word='',empty=1,abbr=signature_text,dup=1),]
                # refresh=True
                # call signature popup doesn't need to be cached by the framework
                self.nvim.call('cm#complete', info['name'], ctx, ctx['col'], matches, True, async=True)
            return

        completions = script.completions()
        logger.info('completions %s', completions)

        matches = []

        for complete in completions:

            insert = complete.complete

            try:
                # simply workaround jedi's bug:
                # https://github.com/roxma/nvim-completion-manager/issues/43
                if signature and complete.type=='param' and complete.parent().name!=signature.name:
                    insert = insert.rstrip('=')
            except Exception as ex:
                logger.exception("error processing complete item: %s", complete)

            item = dict(word=ctx['base']+insert,
                        icase=1,
                        dup=1,
                        menu=complete.description,
                        info=complete.docstring()
                        )

            # Fix the user typed case
            if item['word'].lower()==complete.name.lower():
                item['word'] = complete.name

            # snippet support
            try:
                if (complete.type == 'function' or complete.type == 'class'):

                    doc = complete.doc

                    # This line has performance issue
                    # https://github.com/roxma/nvim-completion-manager/issues/126
                    # params = complete.params

                    fundef = doc.split("\n")[0]

                    params = re.search(r'^\s*' + re.escape(complete.name) + r'\((.*)\)$', fundef)

                    if params:
                        item['menu'] = fundef

                    if params and not is_import:
                        logger.debug("building snippet for [%s] [%s] type[%s] doc [%s]", is_import, item['word'], complete.type, doc)

                        num = 1
                        placeholders = []

                        params = params.group(1)
                        if params != '':
                            params = params.split(',')
                            cnt = 0
                            for param in params:
                                cnt += 1
                                if "=" in param or "*" in param:
                                    break
                                else:
                                    name = param.strip('[').strip(' ')

                                    # Note: this is not accurate
                                    if cnt==1 and (name=='self' or name=='cls'):
                                        continue

                                    placeholders.append('${%s:%s}' % (num, name))
                                    num += 1

                                    # skip optional parameters
                                    if "[" in param:
                                        break

                            snip_args = ', '.join(placeholders)
                            if len(placeholders) == 0:
                                # don't jump out of parentheses if function has parameters
                                snip_args='${1}'

                        snippet = '%s(%s)${0}' % (item['word'], snip_args)

                        item['snippet'] = snippet
                        logger.debug('snippet: [%s] placeholders: %s', snippet, placeholders)

            except Exception as ex:
                logger.exception("exception parsing snippet for item: %s, complete: %s", item, complete)

            matches.append(item)

        # cm#complete(src, context, startcol, matches)
        logger.info('matches %s', matches)
        self.complete(info, ctx, ctx['startcol'], matches)

