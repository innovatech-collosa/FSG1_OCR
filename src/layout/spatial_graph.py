from .models import SpatialRelation

def build_relations(tokens,max_neighbors=1):
    rel=[]
    for i,a in enumerate(tokens):
        right=[]; below=[]
        ah=max(1,a.bbox_norm.height); aw=max(1e-6,a.bbox_norm.width)
        for j,b in enumerate(tokens):
            if i==j: continue
            vo=max(0,min(a.bbox_norm.y1,b.bbox_norm.y1)-max(a.bbox_norm.y0,b.bbox_norm.y0))
            ho=max(0,min(a.bbox_norm.x1,b.bbox_norm.x1)-max(a.bbox_norm.x0,b.bbox_norm.x0))
            if b.bbox_norm.x0>=a.bbox_norm.x1 and vo>=min(ah,b.bbox_norm.height)*.35:
                right.append((b.bbox_norm.x0-a.bbox_norm.x1,j))
            if b.bbox_norm.y0>=a.bbox_norm.y1 and ho>=min(aw,b.bbox_norm.width)*.25:
                below.append((b.bbox_norm.y0-a.bbox_norm.y1,j))
        for d,j in sorted(right)[:max_neighbors]: rel.append(SpatialRelation(f"token_{i}",f"token_{j}","NEAREST_RIGHT",round(d,6)))
        for d,j in sorted(below)[:max_neighbors]: rel.append(SpatialRelation(f"token_{i}",f"token_{j}","NEAREST_BELOW",round(d,6)))
    return rel
