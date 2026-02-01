"""
Script para popular banco de medicamentos cardiológicos
Baseado em fontes: MSD Veterinary Manual, Cardiac Education Group, CardioRush
"""

import sqlite3
from pathlib import Path
from datetime import datetime

db_path = Path.home() / 'FortCordis' / 'DB' / 'fortcordis.db'
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()
now = datetime.now().isoformat()

# Lista completa de medicamentos cardiológicos
# (nome, nome_key, apresentacao, conc_valor, conc_unidade, dose_padrao, dose_min, dose_max, freq, duracao, via, obs, categoria)
medicamentos = [
    # DIURÉTICOS
    ('Furosemida 10mg', 'furosemida 10mg', 'Comprimido', 10.0, 'mg', 2.0, 1.0, 6.0, 'BID a TID', 30, 'VO', 'Diurético de alça. Cães: 1-6mg/kg. Gatos: 1-2mg/kg. Monitorar eletrólitos.', 'Diurético'),
    ('Furosemida 40mg', 'furosemida 40mg', 'Comprimido', 40.0, 'mg', 2.0, 1.0, 6.0, 'BID a TID', 30, 'VO', 'Diurético de alça. Cães: 1-6mg/kg. Gatos: 1-2mg/kg. Monitorar eletrólitos.', 'Diurético'),
    ('Furosemida 10mg/ml', 'furosemida 10mg/ml', 'Solução injetável', 10.0, 'mg/ml', 2.0, 0.5, 4.0, 'q1-6h (agudo)', 3, 'IV/IM', 'Uso emergencial. Cães: 2-4mg/kg. Gatos: 0.5-2mg/kg.', 'Diurético'),
    ('Torasemida 5mg', 'torasemida 5mg', 'Comprimido', 5.0, 'mg', 0.2, 0.1, 0.4, 'SID a BID', 30, 'VO', 'Diurético de alça mais potente. Cães: 0.1-0.4mg/kg.', 'Diurético'),
    ('Torasemida 10mg', 'torasemida 10mg', 'Comprimido', 10.0, 'mg', 0.2, 0.1, 0.4, 'SID a BID', 30, 'VO', 'Diurético de alça mais potente. Para cães maiores.', 'Diurético'),
    ('Espironolactona 25mg', 'espironolactona 25mg', 'Comprimido', 25.0, 'mg', 2.0, 1.0, 4.0, 'SID a BID', 30, 'VO', 'Poupador de potássio. Cães: 1-2mg/kg BID ou 2-4mg/kg SID.', 'Diurético'),
    ('Espironolactona 100mg', 'espironolactona 100mg', 'Comprimido', 100.0, 'mg', 2.0, 1.0, 4.0, 'SID a BID', 30, 'VO', 'Poupador de potássio. Para cães grandes.', 'Diurético'),
    ('Hidroclorotiazida 25mg', 'hidroclorotiazida 25mg', 'Comprimido', 25.0, 'mg', 2.0, 1.0, 4.0, 'SID a BID', 30, 'VO', 'Diurético tiazídico. Cães: 1-4mg/kg. Gatos: 0.5-2mg/kg.', 'Diurético'),

    # INOTRÓPICOS POSITIVOS
    ('Pimobendan 1.25mg', 'pimobendan 1.25mg', 'Comprimido mastigável', 1.25, 'mg', 0.25, 0.25, 0.3, 'BID', 30, 'VO', 'Inodilatador. 1h antes das refeições. Cães e gatos: 0.25mg/kg.', 'Inotrópico'),
    ('Pimobendan 2.5mg', 'pimobendan 2.5mg', 'Comprimido mastigável', 2.5, 'mg', 0.25, 0.25, 0.3, 'BID', 30, 'VO', 'Inodilatador. 1h antes das refeições. Cães e gatos: 0.25mg/kg.', 'Inotrópico'),
    ('Pimobendan 5mg', 'pimobendan 5mg', 'Comprimido mastigável', 5.0, 'mg', 0.25, 0.25, 0.3, 'BID', 30, 'VO', 'Inodilatador. 1h antes das refeições. Cães e gatos: 0.25mg/kg.', 'Inotrópico'),
    ('Pimobendan 10mg', 'pimobendan 10mg', 'Comprimido mastigável', 10.0, 'mg', 0.25, 0.25, 0.3, 'BID', 30, 'VO', 'Inodilatador. Para cães grandes. 0.25mg/kg.', 'Inotrópico'),
    ('Digoxina 0.25mg', 'digoxina 0.25mg', 'Comprimido', 0.25, 'mg', 0.005, 0.0025, 0.005, 'BID', 30, 'VO', 'Glicosídeo cardíaco. Margem terapêutica estreita. Monitorar níveis.', 'Inotrópico'),
    ('Digoxina 0.125mg', 'digoxina 0.125mg', 'Comprimido', 0.125, 'mg', 0.005, 0.0025, 0.01, 'SID a BID', 30, 'VO', 'Para gatos e cães pequenos. Monitorar níveis séricos.', 'Inotrópico'),
    ('Dobutamina 250mg/20ml', 'dobutamina 250mg/20ml', 'Solução injetável', 12.5, 'mg/ml', 5.0, 1.0, 15.0, 'CRI', 1, 'IV', 'Inotrópico IV. Cães: 1-15mcg/kg/min. Gatos: 0.5-5mcg/kg/min.', 'Inotrópico'),

    # IECA (Inibidores da ECA)
    ('Enalapril 5mg', 'enalapril 5mg', 'Comprimido', 5.0, 'mg', 0.5, 0.25, 0.5, 'SID a BID', 30, 'VO', 'IECA. Cães e gatos: 0.25-0.5mg/kg. Pode causar hipotensão.', 'IECA'),
    ('Enalapril 10mg', 'enalapril 10mg', 'Comprimido', 10.0, 'mg', 0.5, 0.25, 0.5, 'SID a BID', 30, 'VO', 'IECA. Cães e gatos: 0.25-0.5mg/kg. Pode causar hipotensão.', 'IECA'),
    ('Enalapril 20mg', 'enalapril 20mg', 'Comprimido', 20.0, 'mg', 0.5, 0.25, 0.5, 'SID a BID', 30, 'VO', 'IECA. Para cães grandes. 0.25-0.5mg/kg.', 'IECA'),
    ('Benazepril 5mg', 'benazepril 5mg', 'Comprimido', 5.0, 'mg', 0.5, 0.25, 0.5, 'SID a BID', 30, 'VO', 'IECA. Eliminação hepatobiliar - melhor para doença renal.', 'IECA'),
    ('Benazepril 10mg', 'benazepril 10mg', 'Comprimido', 10.0, 'mg', 0.5, 0.25, 0.5, 'SID a BID', 30, 'VO', 'IECA. Eliminação hepatobiliar - melhor para doença renal.', 'IECA'),
    ('Benazepril 20mg', 'benazepril 20mg', 'Comprimido', 20.0, 'mg', 0.5, 0.25, 0.5, 'SID a BID', 30, 'VO', 'IECA. Para cães grandes.', 'IECA'),
    ('Ramipril 2.5mg', 'ramipril 2.5mg', 'Comprimido', 2.5, 'mg', 0.125, 0.125, 0.25, 'SID', 30, 'VO', 'IECA. Cães: 0.125-0.25mg/kg SID.', 'IECA'),
    ('Ramipril 5mg', 'ramipril 5mg', 'Comprimido', 5.0, 'mg', 0.125, 0.125, 0.25, 'SID', 30, 'VO', 'IECA. Para cães maiores.', 'IECA'),
    ('Lisinopril 5mg', 'lisinopril 5mg', 'Comprimido', 5.0, 'mg', 0.5, 0.5, 0.5, 'SID a BID', 30, 'VO', 'IECA. Cães: 0.5mg/kg. Gatos: 2.5mg/gato SID.', 'IECA'),
    ('Lisinopril 10mg', 'lisinopril 10mg', 'Comprimido', 10.0, 'mg', 0.5, 0.5, 0.5, 'SID a BID', 30, 'VO', 'IECA. Para cães maiores.', 'IECA'),

    # BRA (Bloqueadores Receptor Angiotensina)
    ('Telmisartana 20mg', 'telmisartana 20mg', 'Comprimido', 20.0, 'mg', 1.5, 1.0, 2.0, 'SID', 30, 'VO', 'BRA. Cães: 1-2mg/kg SID. Gatos: 1.5mg/kg inicial, depois 2mg/kg.', 'BRA'),
    ('Telmisartana 40mg', 'telmisartana 40mg', 'Comprimido', 40.0, 'mg', 1.5, 1.0, 2.0, 'SID', 30, 'VO', 'BRA. Para cães maiores.', 'BRA'),

    # BLOQUEADORES DE CANAL DE CÁLCIO
    ('Amlodipina 2.5mg', 'amlodipina 2.5mg', 'Comprimido', 2.5, 'mg', 0.2, 0.1, 0.6, 'SID a BID', 30, 'VO', 'Anti-hipertensivo. 1a escolha para hipertensão felina.', 'BCC'),
    ('Amlodipina 5mg', 'amlodipina 5mg', 'Comprimido', 5.0, 'mg', 0.2, 0.1, 0.4, 'SID a BID', 30, 'VO', 'Anti-hipertensivo. Cães: 0.1-0.4mg/kg.', 'BCC'),
    ('Amlodipina 10mg', 'amlodipina 10mg', 'Comprimido', 10.0, 'mg', 0.2, 0.1, 0.4, 'SID a BID', 30, 'VO', 'Anti-hipertensivo. Para cães grandes.', 'BCC'),
    ('Diltiazem 30mg', 'diltiazem 30mg', 'Comprimido', 30.0, 'mg', 1.5, 0.5, 3.0, 'TID', 30, 'VO', 'Antiarrítmico classe IV. Cães: 0.5-3mg/kg TID. Gatos: 1.5-3mg/kg.', 'BCC'),
    ('Diltiazem 60mg', 'diltiazem 60mg', 'Comprimido', 60.0, 'mg', 1.5, 0.5, 3.0, 'TID', 30, 'VO', 'Antiarrítmico classe IV. Para cães maiores.', 'BCC'),
    ('Diltiazem 90mg SR', 'diltiazem 90mg sr', 'Comprimido liberação lenta', 90.0, 'mg', 3.0, 1.5, 4.5, 'BID', 30, 'VO', 'Liberação sustentada. Gatos: 30mg/gato BID.', 'BCC'),

    # BETA-BLOQUEADORES
    ('Atenolol 25mg', 'atenolol 25mg', 'Comprimido', 25.0, 'mg', 0.5, 0.2, 1.5, 'SID a BID', 30, 'VO', 'Beta-bloqueador seletivo. Cães: 0.2-1.5mg/kg. Gatos: 6.25-12.5mg/gato.', 'Beta-bloqueador'),
    ('Atenolol 50mg', 'atenolol 50mg', 'Comprimido', 50.0, 'mg', 0.5, 0.2, 1.5, 'SID a BID', 30, 'VO', 'Beta-bloqueador seletivo. Para cães maiores.', 'Beta-bloqueador'),
    ('Atenolol 100mg', 'atenolol 100mg', 'Comprimido', 100.0, 'mg', 0.5, 0.2, 1.5, 'SID a BID', 30, 'VO', 'Beta-bloqueador seletivo. Para cães grandes.', 'Beta-bloqueador'),
    ('Propranolol 10mg', 'propranolol 10mg', 'Comprimido', 10.0, 'mg', 0.5, 0.2, 1.5, 'TID', 30, 'VO', 'Beta-bloqueador não seletivo. Cães: 0.2-1.5mg/kg TID.', 'Beta-bloqueador'),
    ('Propranolol 40mg', 'propranolol 40mg', 'Comprimido', 40.0, 'mg', 0.5, 0.2, 1.5, 'TID', 30, 'VO', 'Beta-bloqueador não seletivo. Para cães maiores.', 'Beta-bloqueador'),
    ('Carvedilol 3.125mg', 'carvedilol 3.125mg', 'Comprimido', 3.125, 'mg', 0.3, 0.2, 1.5, 'BID', 30, 'VO', 'Beta-bloqueador + alfa. Titular lentamente. Cães: 0.2-1.5mg/kg.', 'Beta-bloqueador'),
    ('Carvedilol 6.25mg', 'carvedilol 6.25mg', 'Comprimido', 6.25, 'mg', 0.3, 0.2, 1.5, 'BID', 30, 'VO', 'Beta-bloqueador + alfa. Titular lentamente.', 'Beta-bloqueador'),
    ('Carvedilol 12.5mg', 'carvedilol 12.5mg', 'Comprimido', 12.5, 'mg', 0.3, 0.2, 1.5, 'BID', 30, 'VO', 'Beta-bloqueador + alfa. Para cães maiores.', 'Beta-bloqueador'),
    ('Carvedilol 25mg', 'carvedilol 25mg', 'Comprimido', 25.0, 'mg', 0.3, 0.2, 1.5, 'BID', 30, 'VO', 'Beta-bloqueador + alfa. Para cães grandes.', 'Beta-bloqueador'),
    ('Metoprolol 25mg', 'metoprolol 25mg', 'Comprimido', 25.0, 'mg', 0.5, 0.4, 1.0, 'BID', 30, 'VO', 'Beta-bloqueador seletivo. Cães: 0.4-1.0mg/kg BID.', 'Beta-bloqueador'),
    ('Metoprolol 50mg', 'metoprolol 50mg', 'Comprimido', 50.0, 'mg', 0.5, 0.4, 1.0, 'BID', 30, 'VO', 'Beta-bloqueador seletivo. Para cães maiores.', 'Beta-bloqueador'),

    # ANTIARRÍTMICOS
    ('Sotalol 80mg', 'sotalol 80mg', 'Comprimido', 80.0, 'mg', 2.0, 1.0, 3.5, 'BID', 30, 'VO', 'Classe III. Cães e gatos: 1-3.5mg/kg BID.', 'Antiarrítmico'),
    ('Sotalol 160mg', 'sotalol 160mg', 'Comprimido', 160.0, 'mg', 2.0, 1.0, 3.5, 'BID', 30, 'VO', 'Classe III. Para cães maiores.', 'Antiarrítmico'),
    ('Amiodarona 100mg', 'amiodarona 100mg', 'Comprimido', 100.0, 'mg', 10.0, 5.0, 10.0, 'SID a BID', 30, 'VO', 'Classe III. Cães: 8-10mg/kg BID por 7-10 dias, depois 5-10mg/kg SID. Monitorar tireoide.', 'Antiarrítmico'),
    ('Amiodarona 200mg', 'amiodarona 200mg', 'Comprimido', 200.0, 'mg', 10.0, 5.0, 10.0, 'SID a BID', 30, 'VO', 'Classe III. Para cães maiores. Monitorar tireoide.', 'Antiarrítmico'),
    ('Mexiletina 150mg', 'mexiletina 150mg', 'Cápsula', 150.0, 'mg', 6.0, 4.0, 8.0, 'TID', 30, 'VO', 'Classe IB. Cães: 4-8mg/kg TID. Arritmias ventriculares.', 'Antiarrítmico'),
    ('Mexiletina 200mg', 'mexiletina 200mg', 'Cápsula', 200.0, 'mg', 6.0, 4.0, 8.0, 'TID', 30, 'VO', 'Classe IB. Para cães maiores.', 'Antiarrítmico'),
    ('Procainamida 250mg', 'procainamida 250mg', 'Comprimido', 250.0, 'mg', 15.0, 10.0, 20.0, 'q2-4h', 7, 'VO', 'Classe IA. Cães: 10-20mg/kg q2-4h VO.', 'Antiarrítmico'),
    ('Procainamida 500mg', 'procainamida 500mg', 'Comprimido', 500.0, 'mg', 15.0, 10.0, 20.0, 'q2-4h', 7, 'VO', 'Classe IA. Para cães grandes.', 'Antiarrítmico'),

    # VASODILATADORES
    ('Sildenafil 20mg', 'sildenafil 20mg', 'Comprimido', 20.0, 'mg', 2.0, 1.0, 3.0, 'TID', 30, 'VO', 'Inibidor PDE5. Hipertensão pulmonar. Cães e gatos: 1-3mg/kg TID.', 'Vasodilatador'),
    ('Sildenafil 50mg', 'sildenafil 50mg', 'Comprimido', 50.0, 'mg', 2.0, 1.0, 3.0, 'TID', 30, 'VO', 'Inibidor PDE5. Para cães maiores.', 'Vasodilatador'),
    ('Sildenafil 100mg', 'sildenafil 100mg', 'Comprimido', 100.0, 'mg', 2.0, 1.0, 3.0, 'TID', 30, 'VO', 'Inibidor PDE5. Para cães grandes.', 'Vasodilatador'),
    ('Tadalafil 5mg', 'tadalafil 5mg', 'Comprimido', 5.0, 'mg', 1.5, 1.0, 2.0, 'BID', 30, 'VO', 'Inibidor PDE5. Cães: 1-2mg/kg BID. Alternativa ao sildenafil.', 'Vasodilatador'),
    ('Tadalafil 20mg', 'tadalafil 20mg', 'Comprimido', 20.0, 'mg', 1.5, 1.0, 2.0, 'BID', 30, 'VO', 'Inibidor PDE5. Para cães maiores.', 'Vasodilatador'),
    ('Hidralazina 25mg', 'hidralazina 25mg', 'Comprimido', 25.0, 'mg', 1.0, 0.5, 3.0, 'BID', 30, 'VO', 'Vasodilatador arterial. Cães: 0.5-3mg/kg BID. Titular dose.', 'Vasodilatador'),
    ('Hidralazina 50mg', 'hidralazina 50mg', 'Comprimido', 50.0, 'mg', 1.0, 0.5, 3.0, 'BID', 30, 'VO', 'Vasodilatador arterial. Para cães maiores.', 'Vasodilatador'),
    ('Nitroglicerina 2%', 'nitroglicerina 2%', 'Pomada', 2.0, '%', 0.5, 0.3, 1.0, 'TID', 1, 'Tópica', 'Vasodilatador venoso. 6.3mm pasta/5-10kg na orelha. Uso agudo.', 'Vasodilatador'),

    # ANTITROMBÓTICOS
    ('Clopidogrel 75mg', 'clopidogrel 75mg', 'Comprimido', 75.0, 'mg', 2.0, 1.0, 4.0, 'SID', 30, 'VO', 'Antiagregante. Cães: 1-4mg/kg SID. Gatos: 18.75mg/gato SID (dose de manutenção).', 'Antitrombótico'),
    ('Ácido Acetilsalicílico 100mg', 'aas 100mg', 'Comprimido', 100.0, 'mg', 5.0, 2.0, 10.0, 'q24-72h', 30, 'VO', 'Antiagregante. Cães: 2-10mg/kg SID. Gatos: 81mg q72h (Seg/Qua/Sex).', 'Antitrombótico'),
    ('Ácido Acetilsalicílico 81mg', 'aas 81mg', 'Comprimido infantil', 81.0, 'mg', 5.0, 1.0, 10.0, 'q48-72h', 30, 'VO', 'Antiagregante. Gatos: 1/4 a 1 cp q48-72h.', 'Antitrombótico'),
    ('Rivaroxabana 10mg', 'rivaroxabana 10mg', 'Comprimido', 10.0, 'mg', 1.0, 0.5, 2.0, 'SID a BID', 30, 'VO', 'Anticoagulante oral (Xarelto). Cães: 1-2mg/kg. Gatos: 0.5-1mg/kg.', 'Antitrombótico'),
    ('Rivaroxabana 15mg', 'rivaroxabana 15mg', 'Comprimido', 15.0, 'mg', 1.0, 0.5, 2.0, 'SID a BID', 30, 'VO', 'Anticoagulante oral. Para cães maiores.', 'Antitrombótico'),
    ('Apixabana 2.5mg', 'apixabana 2.5mg', 'Comprimido', 2.5, 'mg', 0.4, 0.25, 0.5, 'BID a TID', 30, 'VO', 'Anticoagulante oral (Eliquis). Cães: 0.25-0.5mg/kg. Gatos: 0.625-1.25mg/gato.', 'Antitrombótico'),
    ('Apixabana 5mg', 'apixabana 5mg', 'Comprimido', 5.0, 'mg', 0.4, 0.25, 0.5, 'BID a TID', 30, 'VO', 'Anticoagulante oral. Para cães maiores.', 'Antitrombótico'),
    ('Enoxaparina 40mg/0.4ml', 'enoxaparina 40mg', 'Seringa preenchida', 100.0, 'mg/ml', 1.0, 0.75, 1.0, 'q6-12h', 7, 'SC', 'Heparina baixo peso. Cães: 0.8mg/kg q6h. Gatos: 0.75-1mg/kg q6-12h.', 'Antitrombótico'),

    # SUPLEMENTOS
    ('Taurina 500mg', 'taurina 500mg', 'Cápsula', 500.0, 'mg', 250.0, 250.0, 500.0, 'BID', 90, 'VO', 'CMD felina e algumas raças caninas. Gatos: 250-500mg BID.', 'Suplemento'),
    ('Taurina 1000mg', 'taurina 1000mg', 'Cápsula', 1000.0, 'mg', 250.0, 250.0, 500.0, 'BID', 90, 'VO', 'Para cães com CMD. 250-1000mg BID conforme tamanho.', 'Suplemento'),
    ('L-Carnitina 500mg', 'l-carnitina 500mg', 'Cápsula', 500.0, 'mg', 50.0, 50.0, 100.0, 'BID a TID', 90, 'VO', 'Suporte metabólico. Cães: 1000-3000mg/cão BID.', 'Suplemento'),
    ('L-Carnitina 1000mg', 'l-carnitina 1000mg', 'Cápsula', 1000.0, 'mg', 50.0, 50.0, 100.0, 'BID a TID', 90, 'VO', 'Para cães maiores com CMD.', 'Suplemento'),
    ('Coenzima Q10 100mg', 'coq10 100mg', 'Cápsula', 100.0, 'mg', 2.0, 1.0, 3.0, 'SID a BID', 90, 'VO', 'Antioxidante cardíaco. Suporte em ICC.', 'Suplemento'),
    ('Ômega 3 1000mg', 'omega 3 1000mg', 'Cápsula', 1000.0, 'mg', 50.0, 30.0, 100.0, 'SID', 90, 'VO', 'Anti-inflamatório. EPA/DHA. Suporte cardiovascular e renal.', 'Suplemento'),

    # BRONCODILATADORES/ANTITUSSÍGENOS
    ('Aminofilina 100mg', 'aminofilina 100mg', 'Comprimido', 100.0, 'mg', 10.0, 5.0, 11.0, 'BID a TID', 30, 'VO', 'Broncodilatador. Cães: 5-11mg/kg BID-TID. Gatos: 5mg/kg BID.', 'Broncodilatador'),
    ('Aminofilina 200mg', 'aminofilina 200mg', 'Comprimido', 200.0, 'mg', 10.0, 5.0, 11.0, 'BID a TID', 30, 'VO', 'Broncodilatador. Para cães maiores.', 'Broncodilatador'),
    ('Teofilina 100mg', 'teofilina 100mg', 'Comprimido', 100.0, 'mg', 10.0, 5.0, 10.0, 'BID', 30, 'VO', 'Broncodilatador. Cães: 5-10mg/kg BID.', 'Broncodilatador'),
    ('Teofilina 200mg SR', 'teofilina 200mg sr', 'Comprimido liberação lenta', 200.0, 'mg', 10.0, 5.0, 10.0, 'SID a BID', 30, 'VO', 'Liberação sustentada. Cães: 10mg/kg BID.', 'Broncodilatador'),
    ('Codeína 30mg', 'codeina 30mg', 'Comprimido', 30.0, 'mg', 1.0, 0.5, 2.0, 'TID a QID', 14, 'VO', 'Antitussígeno. Cães: 0.5-2mg/kg TID-QID. Controlado.', 'Antitussígeno'),
    ('Butorfanol 5mg', 'butorfanol 5mg', 'Comprimido', 5.0, 'mg', 0.5, 0.55, 1.1, 'TID a QID', 14, 'VO', 'Antitussígeno. Cães: 0.55-1.1mg/kg TID-QID.', 'Antitussígeno'),
    ('Hidrocodona 5mg', 'hidrocodona 5mg', 'Comprimido', 5.0, 'mg', 0.5, 0.2, 1.0, 'TID a QID', 14, 'VO', 'Antitussígeno. Cães: 0.2-1mg/kg TID-QID. Controlado.', 'Antitussígeno'),

    # SEDATIVOS/ANSIOLÍTICOS (para estresse cardíaco)
    ('Acepromazina 1mg', 'acepromazina 1mg', 'Comprimido', 1.0, 'mg', 0.05, 0.01, 0.1, 'conforme necessário', 1, 'VO', 'Sedação leve. CUIDADO em cardiopatas. Dose baixa.', 'Sedativo'),
    ('Gabapentina 100mg', 'gabapentina 100mg', 'Cápsula', 100.0, 'mg', 5.0, 2.0, 10.0, 'BID a TID', 30, 'VO', 'Ansiolítico/analgésico. Útil para estresse. Cães/gatos: 2-10mg/kg.', 'Ansiolítico'),
    ('Gabapentina 300mg', 'gabapentina 300mg', 'Cápsula', 300.0, 'mg', 5.0, 2.0, 10.0, 'BID a TID', 30, 'VO', 'Ansiolítico. Para cães maiores.', 'Ansiolítico'),

    # EMERGÊNCIA CARDÍACA
    ('Adrenalina 1mg/ml', 'adrenalina 1mg/ml', 'Solução injetável', 1.0, 'mg/ml', 0.01, 0.01, 0.02, 'q3-5min', 1, 'IV/IT', 'PCR: 0.01-0.02mg/kg IV q3-5min. IT: 0.1-0.2mg/kg diluída.', 'Emergência'),
    ('Atropina 0.25mg/ml', 'atropina 0.25mg/ml', 'Solução injetável', 0.25, 'mg/ml', 0.04, 0.02, 0.04, 'a efeito', 1, 'IV/IM/SC', 'Bradicardia. Cães e gatos: 0.02-0.04mg/kg.', 'Emergência'),
    ('Atropina 0.5mg/ml', 'atropina 0.5mg/ml', 'Solução injetável', 0.5, 'mg/ml', 0.04, 0.02, 0.04, 'a efeito', 1, 'IV/IM/SC', 'Bradicardia. Cães e gatos: 0.02-0.04mg/kg.', 'Emergência'),
    ('Lidocaína 2%', 'lidocaina 2%', 'Solução injetável', 20.0, 'mg/ml', 2.0, 2.0, 4.0, 'bolus + CRI', 1, 'IV', 'Arritmias ventriculares. Cães: 2mg/kg bolus, depois 30-75mcg/kg/min CRI.', 'Emergência'),
    ('Gluconato de Cálcio 10%', 'gluconato calcio 10%', 'Solução injetável', 100.0, 'mg/ml', 100.0, 50.0, 150.0, 'lento IV', 1, 'IV', 'Hipercalemia, hipocalcemia. 50-150mg/kg IV lento 5-15min.', 'Emergência'),
    ('Sulfato de Magnésio 10%', 'sulfato magnesio 10%', 'Solução injetável', 100.0, 'mg/ml', 25.0, 15.0, 30.0, 'lento IV', 1, 'IV', 'Torsades de pointes. 0.15-0.3mEq/kg IV lento 5-15min.', 'Emergência'),
    ('Vasopressina 20UI/ml', 'vasopressina 20ui/ml', 'Solução injetável', 20.0, 'UI/ml', 0.8, 0.4, 0.8, 'bolus único', 1, 'IV', 'PCR: 0.4-0.8UI/kg IV dose única. Alternativa à adrenalina.', 'Emergência'),

    # OUTROS
    ('Trientina 250mg', 'trientina 250mg', 'Cápsula', 250.0, 'mg', 15.0, 10.0, 15.0, 'BID', 90, 'VO', 'Quelante de cobre. Hepatopatia por cobre. Cães: 10-15mg/kg BID.', 'Hepatoprotetor'),
    ('Omeprazol 20mg', 'omeprazol 20mg', 'Cápsula', 20.0, 'mg', 1.0, 0.5, 1.0, 'SID a BID', 30, 'VO', 'IBP. Proteção gástrica em uso de AINEs/corticoides.', 'Gastroprotetor'),
    ('Sucralfato 1g', 'sucralfato 1g', 'Comprimido', 1000.0, 'mg', 50.0, 25.0, 100.0, 'TID a QID', 14, 'VO', 'Protetor de mucosa. 0.25-1g/cão TID-QID. Dar 1h antes das refeições.', 'Gastroprotetor'),
]

# Verifica se precisa adicionar coluna categoria
try:
    cursor.execute('SELECT categoria FROM medicamentos LIMIT 1')
except:
    print('Adicionando coluna categoria...')
    cursor.execute('ALTER TABLE medicamentos ADD COLUMN categoria TEXT')
    conn.commit()

# Limpa medicamentos antigos e insere novos
cursor.execute('DELETE FROM medicamentos')
conn.commit()

for med in medicamentos:
    cursor.execute('''
        INSERT INTO medicamentos (nome, nome_key, apresentacao, concentracao_valor, concentracao_unidade,
            dose_padrao_mgkg, dose_min_mgkg, dose_max_mgkg, frequencia_padrao, duracao_dias_padrao,
            via, observacoes, categoria, ativo, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
    ''', (*med, now, now))

conn.commit()

# Conta por categoria
cursor.execute('''
    SELECT categoria, COUNT(*) as qtd
    FROM medicamentos
    GROUP BY categoria
    ORDER BY qtd DESC
''')
print('\n=== MEDICAMENTOS POR CATEGORIA ===')
total = 0
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]}')
    total += row[1]
print(f'\n  TOTAL: {total} medicamentos')

conn.close()
print('\n✅ Banco de medicamentos atualizado com sucesso!')
print('\nFontes: MSD Veterinary Manual, Cardiac Education Group,')
print('        CardioRush (Tufts), HeartVets, BSAVA Formulary')
