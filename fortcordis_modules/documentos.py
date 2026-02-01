"""
Módulo de Geração de Documentos Veterinários
Gera PDFs de receituários, atestados, GTA e termos de consentimento
"""

from fpdf import FPDF
from datetime import datetime
from pathlib import Path
import os

class DocumentoVeterinario(FPDF):
    """Classe base para documentos veterinários com cabeçalho padrão"""
    
    def __init__(self, logo_path=None, medico="Dr. [Nome]", crmv="CRMV-CE XXXXX"):
        super().__init__()
        self.logo_path = logo_path
        self.medico = medico
        self.crmv = crmv
    
    def header(self):
        # Logo
        if self.logo_path and os.path.exists(self.logo_path):
            self.image(self.logo_path, 10, 8, 30)
        
        # Informações do médico
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'FORT CORDIS', 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, 'Cardiologia Veterinária', 0, 1, 'C')
        self.cell(0, 5, f'{self.medico} - {self.crmv}', 0, 1, 'C')
        self.cell(0, 5, 'Fortaleza - CE', 0, 1, 'C')
        self.ln(10)

def gerar_receituario_pdf(
    paciente_nome, 
    tutor_nome, 
    especie, 
    peso_kg,
    prescricao_texto,
    medico="Dr. [Nome]",
    crmv="CRMV-CE XXXXX",
    logo_path=None
):
    """
    Gera PDF de receituário veterinário
    """
    pdf = DocumentoVeterinario(logo_path, medico, crmv)
    pdf.add_page()
    
    # Título
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'RECEITUÁRIO VETERINÁRIO', 0, 1, 'C')
    pdf.ln(5)
    
    # Dados do paciente
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 6, f'Data: {datetime.now().strftime("%d/%m/%Y")}', 0, 1)
    pdf.cell(0, 6, f'Paciente: {paciente_nome}', 0, 1)
    pdf.cell(0, 6, f'Tutor: {tutor_nome}', 0, 1)
    pdf.cell(0, 6, f'Espécie: {especie}', 0, 1)
    if peso_kg:
        pdf.cell(0, 6, f'Peso: {peso_kg} kg', 0, 1)
    pdf.ln(5)
    
    # Linha separadora
    pdf.set_draw_color(50, 50, 60)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    # Prescrição (símbolo Rx)
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 8, 'Rx', 0, 1)
    pdf.ln(2)
    
    # Texto da prescrição
    pdf.set_font('Arial', '', 11)
    pdf.multi_cell(0, 6, prescricao_texto)
    
    pdf.ln(10)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    # Assinatura
    pdf.cell(0, 6, f'{medico}', 0, 1, 'R')
    pdf.cell(0, 6, f'{crmv}', 0, 1, 'R')
    
    return pdf.output(dest='S')

def gerar_atestado_saude_pdf(
    paciente_nome,
    tutor_nome,
    especie,
    raca,
    idade,
    finalidade,
    texto_atestado="",
    medico="Dr. [Nome]",
    crmv="CRMV-CE XXXXX",
    logo_path=None
):
    """
    Gera PDF de atestado de saúde veterinário
    """
    pdf = DocumentoVeterinario(logo_path, medico, crmv)
    pdf.add_page()
    
    # Título
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'ATESTADO DE SAÚDE ANIMAL', 0, 1, 'C')
    pdf.ln(10)
    
    # Corpo do atestado
    pdf.set_font('Arial', '', 11)
    
    texto_padrao = f"""Atesto para os devidos fins que o animal {paciente_nome}, espécie {especie}, raça {raca}, com aproximadamente {idade}, de propriedade de {tutor_nome}, foi submetido a exame clínico nesta data, encontrando-se em boas condições de saúde."""
    
    if texto_atestado:
        texto_completo = texto_atestado
    else:
        texto_completo = texto_padrao
    
    if finalidade:
        texto_completo += f"\n\nFinalidade: {finalidade}"
    
    pdf.multi_cell(0, 7, texto_completo)
    
    pdf.ln(10)
    
    # Local e data
    pdf.cell(0, 6, f'Fortaleza - CE, {datetime.now().strftime("%d de %B de %Y")}', 0, 1, 'C')
    
    pdf.ln(20)
    pdf.line(70, pdf.get_y(), 140, pdf.get_y())
    pdf.ln(2)
    pdf.cell(0, 6, f'{medico}', 0, 1, 'C')
    pdf.cell(0, 6, f'{crmv}', 0, 1, 'C')
    
    return pdf.output(dest='S')

def gerar_gta_pdf(
    origem_dados,
    destino_dados,
    animal_dados,
    finalidade,
    medico="Dr. [Nome]",
    crmv="CRMV-CE XXXXX",
    logo_path=None
):
    """
    Gera PDF de Guia de Trânsito Animal (GTA)
    origem_dados: dict com nome, endereco, cidade, cnpj
    destino_dados: dict com nome, endereco, cidade, cnpj
    animal_dados: dict com especie, raca, quantidade, identificacao
    """
    pdf = DocumentoVeterinario(logo_path, medico, crmv)
    pdf.add_page()
    
    # Título
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'GUIA DE TRÂNSITO ANIMAL - GTA', 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, f'Data de Emissão: {datetime.now().strftime("%d/%m/%Y")}', 0, 1)
    pdf.ln(5)
    
    # ORIGEM
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, 'ORIGEM', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 5, f'Proprietário: {origem_dados.get("nome", "")}', 0, 1)
    pdf.cell(0, 5, f'Endereço: {origem_dados.get("endereco", "")}', 0, 1)
    pdf.cell(0, 5, f'Cidade: {origem_dados.get("cidade", "")}', 0, 1)
    pdf.cell(0, 5, f'CNPJ/CPF: {origem_dados.get("cnpj", "")}', 0, 1)
    pdf.ln(5)
    
    # DESTINO
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, 'DESTINO', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 5, f'Proprietário: {destino_dados.get("nome", "")}', 0, 1)
    pdf.cell(0, 5, f'Endereço: {destino_dados.get("endereco", "")}', 0, 1)
    pdf.cell(0, 5, f'Cidade: {destino_dados.get("cidade", "")}', 0, 1)
    pdf.cell(0, 5, f'CNPJ/CPF: {destino_dados.get("cnpj", "")}', 0, 1)
    pdf.ln(5)
    
    # ANIMAL
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, 'DADOS DO ANIMAL', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 5, f'Espécie: {animal_dados.get("especie", "")}', 0, 1)
    pdf.cell(0, 5, f'Raça: {animal_dados.get("raca", "")}', 0, 1)
    pdf.cell(0, 5, f'Quantidade: {animal_dados.get("quantidade", "1")}', 0, 1)
    pdf.cell(0, 5, f'Identificação: {animal_dados.get("identificacao", "")}', 0, 1)
    pdf.ln(5)
    
    # FINALIDADE
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, 'FINALIDADE', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, finalidade)
    pdf.ln(5)
    
    # Atesto
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 6, f'Atesto que o(s) animal(is) relacionado(s) encontra(m)-se em condições de saúde adequadas para o transporte e finalidade especificados.')
    
    pdf.ln(15)
    
    # Assinatura
    pdf.cell(0, 6, f'Fortaleza - CE, {datetime.now().strftime("%d/%m/%Y")}', 0, 1, 'C')
    pdf.ln(15)
    pdf.line(70, pdf.get_y(), 140, pdf.get_y())
    pdf.ln(2)
    pdf.cell(0, 6, f'{medico}', 0, 1, 'C')
    pdf.cell(0, 6, f'{crmv}', 0, 1, 'C')
    
    return pdf.output(dest='S')

def gerar_termo_consentimento_pdf(
    procedimento,
    paciente_nome,
    tutor_nome,
    tutor_cpf,
    riscos_texto="",
    medico="Dr. [Nome]",
    crmv="CRMV-CE XXXXX",
    logo_path=None
):
    """
    Gera PDF de termo de consentimento informado
    """
    pdf = DocumentoVeterinario(logo_path, medico, crmv)
    pdf.add_page()
    
    # Título
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'TERMO DE CONSENTIMENTO INFORMADO', 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font('Arial', '', 10)
    
    # Introdução
    texto_intro = f"""Eu, {tutor_nome}, portador(a) do CPF {tutor_cpf}, proprietário(a) do animal {paciente_nome}, declaro que fui devidamente informado(a) sobre o procedimento de {procedimento} a ser realizado, incluindo seus objetivos, benefícios esperados e possíveis riscos."""
    
    pdf.multi_cell(0, 6, texto_intro)
    pdf.ln(5)
    
    # Riscos
    if riscos_texto:
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 6, 'RISCOS E COMPLICAÇÕES', 0, 1)
        pdf.set_font('Arial', '', 10)
        pdf.multi_cell(0, 6, riscos_texto)
        pdf.ln(5)
    
    # Consentimento
    texto_consentimento = """Declaro que tive a oportunidade de esclarecer todas as minhas dúvidas e que autorizo a realização do procedimento descrito acima.

Estou ciente de que, durante o procedimento, podem surgir situações imprevistas que exijam procedimentos adicionais não mencionados neste termo, e autorizo o médico veterinário a tomar as medidas necessárias para garantir a saúde e bem-estar do meu animal."""
    
    pdf.multi_cell(0, 6, texto_consentimento)
    
    pdf.ln(10)
    
    # Local e data
    pdf.cell(0, 6, f'Fortaleza - CE, {datetime.now().strftime("%d de %B de %Y")}', 0, 1)
    
    pdf.ln(20)
    
    # Linhas de assinatura
    pdf.line(20, pdf.get_y(), 90, pdf.get_y())
    pdf.line(110, pdf.get_y(), 180, pdf.get_y())
    pdf.ln(2)
    
    pdf.cell(85, 6, 'Proprietário/Responsável', 0, 0, 'C')
    pdf.cell(85, 6, 'Médico Veterinário', 0, 1, 'C')
    pdf.ln(2)
    pdf.cell(85, 6, tutor_nome, 0, 0, 'C')
    pdf.cell(85, 6, f'{medico} - {crmv}', 0, 1, 'C')
    
    return pdf.output(dest='S')

def calcular_posologia(peso_kg, dose_mg_kg, concentracao_mg_ml):
    """
    Calcula volume em ml baseado no peso e dose
    peso_kg: peso do animal em kg
    dose_mg_kg: dose em mg/kg
    concentracao_mg_ml: concentração do medicamento em mg/ml
    
    Retorna: volume em ml
    """
    if not peso_kg or not dose_mg_kg or not concentracao_mg_ml:
        return 0.0
    
    dose_total_mg = peso_kg * dose_mg_kg
    volume_ml = dose_total_mg / concentracao_mg_ml
    
    return round(volume_ml, 2)

def formatar_posologia(peso_kg, medicamento_info):
    """
    Formata texto de posologia automaticamente
    medicamento_info: dict com nome, concentracao, dose_padrao_mg_kg, frequencia_padrao, via_administracao
    """
    nome = medicamento_info.get('nome', '')
    concentracao = medicamento_info.get('concentracao', '')
    dose_mg_kg = medicamento_info.get('dose_padrao_mg_kg', 0)
    frequencia = medicamento_info.get('frequencia_padrao', '')
    via = medicamento_info.get('via_administracao', '')
    
    if not peso_kg or not dose_mg_kg:
        return f"{nome} ({concentracao}) - {frequencia} - {via}"
    
    # Extrai concentração numérica (ex: "5mg/ml" -> 5.0)
    try:
        conc_num = float(concentracao.lower().split('mg')[0].strip())
    except:
        conc_num = None
    
    if conc_num:
        volume_ml = calcular_posologia(peso_kg, dose_mg_kg, conc_num)
        return f"{nome} ({concentracao}) - {volume_ml} ml - {frequencia} - {via}"
    else:
        dose_total = peso_kg * dose_mg_kg
        return f"{nome} ({concentracao}) - {dose_total:.1f} mg ({dose_mg_kg} mg/kg) - {frequencia} - {via}"
