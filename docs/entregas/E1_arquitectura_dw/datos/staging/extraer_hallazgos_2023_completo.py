"""Extrae 12 índices de impunidad por delito de las gráficas 1-12 de Hallazgos 2023.
Requiere: pip install pymupdf pandas
Uso: python extraer_hallazgos_2023_completo.py HALLAZGOS2023.pdf
La lectura se basa en las coordenadas del texto incrustado del PDF; no usa OCR.
"""
import re, sys
from pathlib import Path
import fitz
import pandas as pd

ALIAS = {
 'Mich.':'Michoacán','Qro.':'Querétaro','Gto.':'Guanajuato',
 'B.C.S.':'Baja California Sur','Son.':'Sonora','Coah.':'Coahuila',
 'B.C.':'Baja California','Pue.':'Puebla','Nay.':'Nayarit',
 'Ver.':'Veracruz','Zac.':'Zacatecas','N.L.':'Nuevo León',
 'Q.R.':'Quintana Roo','Sin.':'Sinaloa','Tamps.':'Tamaulipas',
 'S.L.P.':'San Luis Potosí','Tab.':'Tabasco','Ags.':'Aguascalientes',
 'CDMX':'Ciudad de México','Cam.':'Campeche','Camp.':'Campeche',
 'Hgo.':'Hidalgo','E.M.':'Estado de México','Gro.':'Guerrero',
 'Col.':'Colima','Jal.':'Jalisco','Oax.':'Oaxaca','Chiap.':'Chiapas',
 'Chih.':'Chihuahua','Dgo.':'Durango','Yuc.':'Yucatán',
 'Nacional':'Nacional'
}
GRAFICAS = [
 ('homicidio_doloso',22,0),('feminicidio',22,1),
 ('desaparicion',23,0),('secuestro',23,1),
 ('extorsion',24,0),('violacion',24,1),
 ('violencia_familiar',25,0),('abuso_sexual',25,1),
 ('despojo',26,0),('fraude',26,1),
 ('robo_casa_habitacion',27,0),('narcomenudeo',27,1)
]
EXPECTED_NATIONAL={
 'homicidio_doloso':96.86,'feminicidio':86.78,'desaparicion':99.51,
 'secuestro':87.08,'extorsion':98.36,'violacion':94.95,
 'violencia_familiar':96.80,'abuso_sexual':95.85,
 'despojo':96.36,'fraude':None,'robo_casa_habitacion':80.65,
 'narcomenudeo':91.92
}

def extraer(pdf):
    doc=fitz.open(pdf)
    registros=[]
    for delito,pagina,orden in GRAFICAS:
        w=doc[pagina-1].get_text('words')
        porcentajes=[(x,y,s) for x,y,x2,y2,s,*_ in w if re.fullmatch(r'\d{1,3}\.\d{2}%',s)]
        alturas=sorted(set(round(y,1) for x,y,s in porcentajes))
        grupos=[[(x,y,s) for x,y,s in porcentajes if abs(y-alt)<0.2] for alt in alturas]
        grupos=[g for g in grupos if len(g)>=15]
        if len(grupos)!=2: raise ValueError(f'Página {pagina}: {len(grupos)} gráficas encontradas')
        vals=sorted(grupos[orden])
        y=vals[0][1]
        posibles={}
        for x,yy,x2,y2,s,*_ in w:
            if s in ALIAS and y+8 < yy < y+155:
                key=round(yy)
                posibles.setdefault(key,[]).append((x,s))
        candidatos=[]
        for pos,labels in posibles.items():
            if abs(len(labels)-len(vals))<=1:
                candidatos.append((abs(len(labels)-len(vals)),abs(pos-y-55),pos,sorted(labels)))
        if not candidatos: raise ValueError(f'{delito}: sin fila válida de entidades')
        _,_,label_y,labels=min(candidatos)
        if len(labels)!=len(vals):raise ValueError(f'{delito}: {len(vals)} valores vs {len(labels)} entidades')
        for (xp,yp,v),(xl,alias) in zip(vals,labels):
            if abs(xp-xl)>4:raise ValueError(f'{delito}: etiquetas desalineadas en {alias}: {xp} vs {xl}')
            registros.append({'delito':delito,'entidad':ALIAS[alias],'anio':'2023',
                'indice_impunidad':v.rstrip('%'),'unidad':'porcentaje',
                'pagina_pdf':str(pagina),'fuente':'México Evalúa - Hallazgos 2023',
                'abreviatura_original':alias,
                'url_fuente':'https://www.mexicoevalua.org/wp-content/uploads/2024/10/HALLAZGOS2023.pdf'})
    df=pd.DataFrame(registros)
    assert df['delito'].nunique()==12
    assert not df.duplicated(['delito','entidad','anio']).any()
    assert df['indice_impunidad'].astype(float).between(0,100).all()
    assert (df.groupby('delito')['entidad'].apply(lambda a:(a=='Nacional').sum())==1).all()
    for delito,valor in EXPECTED_NATIONAL.items():
        actual=float(df[(df.delito==delito)&(df.entidad=='Nacional')]['indice_impunidad'].iloc[0])
        if valor is not None and abs(actual-valor)>.001:raise AssertionError(f'{delito}: valor nacional inesperado {actual}, esperado {valor}')
    return df

if __name__=='__main__':
    pdf=Path(sys.argv[1] if len(sys.argv)>1 else 'HALLAZGOS2023.pdf')
    df=extraer(pdf)
    ruta=Path(__file__).with_name('stg_mexico_evalua_12_indices.csv')
    df.to_csv(ruta,index=False,encoding='utf-8')
    print(df.groupby('delito',sort=False).agg(filas=('entidad','size'),nacional=('indice_impunidad',lambda s:','.join(s))))
    print('\nTotal filas:',len(df),'| Indicadores:',df.delito.nunique())
    print('Archivo:',ruta)
