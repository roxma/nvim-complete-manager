
func! cm#snippet#init()
	if ((!exists('g:cm_completed_snippet_enable') || g:cm_completed_snippet_enable) && !exists('g:cm_completed_snippet_engine'))
        if exists('g:loaded_neosnippet')
            let g:cm_completed_snippet_enable = 1
            let g:cm_completed_snippet_engine = 'neosnippet'
        elseif exists('g:did_plugin_ultisnips')
            let g:cm_completed_snippet_enable = 1
            let g:cm_completed_snippet_engine = 'ultisnips'
        elseif exists('g:snipMateSources')
            let g:cm_completed_snippet_enable = 1
            let g:cm_completed_snippet_engine = 'snipmate'
        else
            let g:cm_completed_snippet_enable = 0
            let g:cm_completed_snippet_engine = ''
        endif
    endif

    let g:cm_completed_snippet_enable = get(g:, 'cm_completed_snippet_enable', 0)
    let g:cm_completed_snippet_engine = get(g:, 'cm_completed_snippet_engine', '')

    if g:cm_completed_snippet_engine == 'neosnippet'
        call s:neosnippet_init()
    endif
    if g:cm_completed_snippet_engine == 'snipmate'
        call s:snipmate_init()
    endif
endfunc

func! cm#snippet#completed_is_snippet()
    call cm#snippet#check_and_inject()
    let completed_extra = s:get_completed_extra()

    " By some reason, 'is_snippet' is not passed when dealing with on-fly
    " snippets (i.e. expand function parameters). So check both 'snippet'
    " and 'is_snippet' columns until proper propagation of 'is_snippet' is
    " fixed.
    if has_key(completed_extra, 'snippet')
      return completed_extra.snippet != ''
    endif
    return get(completed_extra, 'is_snippet', 0)
endfunc

func! cm#snippet#check_and_inject()
    let completed_extra = s:get_completed_extra()

    if empty(v:completed_item) || !has_key(v:completed_item,'info') || empty(v:completed_item.info) || get(completed_extra, 'snippet', '') == ''
        return ''
    endif

    if g:cm_completed_snippet_engine == 'ultisnips'
        call s:ultisnips_inject()

    " elseif g:cm_completed_snippet_engine == 'snipmate'
        " nothing needs to be done for snipmate

    elseif g:cm_completed_snippet_engine == 'neosnippet'
        call s:neosnippet_inject()
    endif

    return ''
endfunc

func! s:ultisnips_inject()
    if get(b:,'_cm_us_setup',0)==0
        " UltiSnips_Manager.add_buffer_filetypes('%s.snips.ncm' % vim.eval('&filetype'))
        let b:_cm_us_setup = 1
        let b:_cm_us_filetype = 'ncm'
        call UltiSnips#AddFiletypes(b:_cm_us_filetype)
        augroup cm
            autocmd InsertLeave <buffer> exec g:_uspy 'UltiSnips_Manager._added_snippets_source._snippets["ncm"]._snippets = []'
        augroup END
    endif
    exec g:_uspy 'UltiSnips_Manager._added_snippets_source._snippets["ncm"]._snippets = []'
    let completed_extra = s:get_completed_extra()
    call UltiSnips#AddSnippetWithPriority(completed_extra.snippet_word, completed_extra.snippet, '', 'i', b:_cm_us_filetype, 1)
endfunc

func! s:neosnippet_init()
    " Not compatible with neosnippet#enable_completed_snippet. NCM
    " choose a different approach
    let g:neosnippet#enable_completed_snippet=0
    augroup cm
        autocmd InsertEnter * call s:neosnippet_cleanup()
    augroup END
    let s:neosnippet_injected = []
endfunc

func! s:neosnippet_inject()
    let snippets = neosnippet#variables#current_neosnippet()
    let completed_extra = s:get_completed_extra()

    let item = {}
    let item['options'] = { "word": 1, "oneshot": 0, "indent": 0, "head": 0}
    let item['word'] = completed_extra.snippet_word
    let item['snip'] = completed_extra.snippet
    let item['description'] = ''

    let snippets.snippets[completed_extra.snippet_word] = item

    " remember for cleanup
    let s:neosnippet_injected = add(s:neosnippet_injected, completed_extra.snippet_word)
endfunc

func! s:neosnippet_cleanup()
    let cs = neosnippet#variables#current_neosnippet()
    for word in s:neosnippet_injected
        if has_key(cs.snippets, word)
          unlet cs.snippets[word]
        endif
    endfor
    let s:neosnippet_injected = []
endfunc

func! s:snipmate_init()
    " inject ncm's handler into snipmate
    let g:snipMateSources.ncm = funcref#Function('cm#snippet#_snipmate_snippets')
endfunc

func! cm#snippet#_snipmate_snippets(scopes, trigger, result)
    let completed_extra = s:get_completed_extra()
    if empty(v:completed_item) || get(completed_extra, 'snippet', '') == ''
        return
    endif
    " use version 1 snippet syntax
    let a:result[completed_extra.snippet_word] = {'default': [completed_extra.snippet, 1] }
endfunc

func! s:get_completed_extra()
    if get(v:completed_item, 'user_data', '') !=# ''
      let user_data = json_decode(v:completed_item.user_data)
      if type(user_data) == v:t_dict
        return user_data
      endif
    endif
    return {}
endfunc
