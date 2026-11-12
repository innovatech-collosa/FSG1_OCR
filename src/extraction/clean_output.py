from __future__ import annotations

def v(fields,name,default=None):
    x=fields.get(name); return default if not x or x.status!='OK' else x.value

def build_incident(fields,source_filename,version='2.1.1'):
    return {
      'documento': {'archivo': source_filename, 'version_extractor': version},
      'datos_generales': {
        'obra': v(fields,'obra',''), 'fecha_accidente':v(fields,'fecha_accidente'),
        'hora_trabajo':v(fields,'hora_trabajo',''), 'hora_accidente':v(fields,'hora_accidente'),
        'empresa':v(fields,'empresa',''), 'fecha_baja':v(fields,'fecha_baja'), 'sin_baja':None},
      'persona_lesionada': {
        'nombre':v(fields,'nombre',''), 'edad':v(fields,'edad'),
        'categoria_profesional':v(fields,'categoria_profesional',''),
        'parte_cuerpo_lesionada':{'codigo':v(fields,'parte_cuerpo_codigo'),'descripcion':''},
        'lesion':{'codigo':v(fields,'lesion_codigo'),'descripcion':''},
        'grado_lesion':None},
      'atencion_accidentado': [],
      'datos_accidente': {
        'pais':v(fields,'pais',''), 'provincia':v(fields,'provincia',''), 'municipio':v(fields,'municipio',''),
        'lugar':'', 'trabajo_realizado':v(fields,'trabajo_realizado',''), 'testigos':v(fields,'testigos',''),
        'descripcion_accidente':v(fields,'descripcion_accidente',''),
        'fallos_o_condiciones':v(fields,'fallos_o_condiciones',''), 'agente_causante':v(fields,'agente_causante','')},
      'clasificacion': {
        'riesgo':{'codigo':v(fields,'riesgo_codigo'),'descripcion':''},
        'condicion_peligrosa':{'codigo':v(fields,'condicion_peligrosa_codigo'),'descripcion':''},
        'causalidad':{'codigo':v(fields,'causalidad_codigo'),'descripcion':''}},
      'circunstancias': {
        'trabajo_habitual':None, 'proteccion_colectiva':None, 'proteccion_individual':None,
        'in_itinere':None, 'acto_temerario':None, 'detectado_anteriormente':None,
        'requiere_reevaluacion_riesgos':None},
      'medidas_preventivas_correctivas':v(fields,'medidas_preventivas_correctivas',''),
      'campos_pendientes_de_detector_visual': [
        'grado_lesion','atencion_accidentado','circunstancias']
    }
