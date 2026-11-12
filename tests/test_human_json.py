from src.extraction.field_extractor import extract_fields
from src.extraction.clean_output import build_incident

def test_basic_scalar_extraction():
    ocr={'pages':[{'page':1,'tokens':[
      {'text':'OBRA','confidence':.99,'bbox_norm':{'x0':.1,'y0':.1,'x1':.2,'y1':.12}},
      {'text':'UTE PRUEBA','confidence':.99,'bbox_norm':{'x0':.22,'y0':.1,'x1':.4,'y1':.12}},
      {'text':'EDAD','confidence':.99,'bbox_norm':{'x0':.1,'y0':.2,'x1':.16,'y1':.22}},
      {'text':'49','confidence':.99,'bbox_norm':{'x0':.18,'y0':.2,'x1':.2,'y1':.22}}]}]}
    defs={'obra':{'aliases':['OBRA'],'type':'text'},'edad':{'aliases':['EDAD'],'type':'integer'}}
    f=extract_fields(ocr,defs); out=build_incident(f,'test.pdf')
    assert out['datos_generales']['obra']=='UTE PRUEBA'
    assert out['persona_lesionada']['edad']==49
    assert out['persona_lesionada']['grado_lesion'] is None
