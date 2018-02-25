"=============================================================================
" cm_icon.vim   devicom support for ncm
" Copyright (c) 2018 MaiLunjiye 
" Author: MaiLunjiye <mailunjiye@gmail.com>
" License: MIT
"=============================================================================

func! cm_icon#_iconSupport(sourceName,orgKind)
    if g:cm_icon_kind_model == 0
        return ""
    endif

    if g:cm_icon_kind_model == 1
        return orgKind
    endif

    let l:sourceDict = get(g:cm_icon_kind_dict,a:sourceName, "NoName")
    return get(l:sourceDict,a:orgKind,a:orgKind)
endfunc

