from __future__ import annotations
import re, unicodedata
from rapidfuzz.fuzz import ratio
from .models import Token, ExtractedValue

def norm(s:str)->str:
    s=unicodedata.normalize('NFD',str(s).upper())
    s=''.join(c for c in s if unicodedata.category(c)!='Mn')
    return re.sub(r'[^A-Z0-9]+',' ',s).strip()

def load_tokens(ocr:dict)->list[Token]:
    out=[]
    for page in ocr.get('pages',[]):
        pn=int(page.get('page',1))
        for raw in page.get('tokens',[]):
            b=raw.get('bbox_norm') or raw.get('bbox_px') or {}
            out.append(Token(str(raw.get('text','')).strip(),float(raw.get('confidence',0)),pn,
                float(b.get('x0',0)),float(b.get('y0',0)),float(b.get('x1',0)),float(b.get('y1',0))))
    return out

def _anchor_score(text,aliases): return max((ratio(norm(text),norm(a)) for a in aliases),default=0)

def locate_anchor(tokens,aliases,min_score=76):
    ranked=[(_anchor_score(t.text,aliases),i,t) for i,t in enumerate(tokens)]
    ranked=[x for x in ranked if x[0]>=min_score]
    return max(ranked,default=None,key=lambda x:(x[0],x[2].confidence))

def _same_row(a,b):
    overlap=max(0,min(a.y1,b.y1)-max(a.y0,b.y0))
    return overlap >= .30*max(1e-6,min(a.height,b.height))

def _clean_inline(text,aliases):
    n=norm(text)
    for a in sorted(aliases,key=len,reverse=True):
        na=norm(a)
        if n.startswith(na):
            # remove approximate prefix using original word count
            words=text.split(); return ' '.join(words[len(a.split()):]).strip(' :.-')
    return ''

def extract_scalar(tokens,aliases,kind='text')->ExtractedValue:
    hit=locate_anchor(tokens,aliases)
    if not hit:return ExtractedValue(None,'NOT_FOUND')
    _,idx,a=hit
    inline=_clean_inline(a.text,aliases)
    candidates=[]
    if inline:candidates.append((0.0,inline,a))
    for j,b in enumerate(tokens):
        if j==idx or b.page!=a.page:continue
        if _same_row(a,b) and b.x0>=a.x1-.01:
            gap=max(0,b.x0-a.x1)
            if gap<=max(.15,3*max(a.height,b.height)):candidates.append((gap,b.text,b))
    if not candidates:
        below=[]
        for j,b in enumerate(tokens):
            if j!=idx and b.page==a.page and b.y0>=a.y1 and abs(b.x0-a.x0)<=max(.08,a.x1-a.x0):
                gap=b.y0-a.y1
                if gap<=max(.04,3*a.height):below.append((gap,b.text,b))
        candidates=below
    if not candidates:return ExtractedValue(None,'NOT_FOUND',a.text)
    value=min(candidates,key=lambda x:x[0])[1].strip()
    if kind=='integer':
        m=re.search(r'\b\d{1,3}\b',value); value=int(m.group()) if m else None
    elif kind=='date':
        m=re.search(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',value); value=m.group() if m else None
    elif kind=='time':
        m=re.search(r'\b([01]?\d|2[0-3])(?::([0-5]\d))?\s*H?\b',value,re.I)
        value=(f'{int(m.group(1)):02d}:{m.group(2) or "00"}' if m else None)
    return ExtractedValue(value,'OK' if value not in (None,'') else 'NOT_FOUND',a.text)

def extract_fields(ocr,definitions):
    tokens=load_tokens(ocr); result={}
    for name,spec in definitions.items():
        kind=spec.get('type','text')
        # First human version: multiline uses conservative nearby scalar extraction.
        # It never consumes the rest of the document.
        result[name]=extract_scalar(tokens,spec.get('aliases',[]),'text' if kind=='multiline' else kind)
    return result
