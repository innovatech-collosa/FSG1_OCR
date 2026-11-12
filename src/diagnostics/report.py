def build_report(filename,pages_tokens):
    tokens=[t for p in pages_tokens for t in p]; conf=[t.confidence for t in tokens]
    return {"documento":filename,"paginas":len(pages_tokens),"tokens":len(tokens),"confianza_media":round(sum(conf)/len(conf),6) if conf else None,"tokens_baja_confianza":sum(c<.70 for c in conf)}
