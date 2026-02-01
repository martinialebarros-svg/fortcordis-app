"""
Script de Inicialização Completa - Fort Cordis
Execute este arquivo UMA VEZ para preparar o sistema

Este script irá:
1. Criar todas as tabelas necessárias
2. Inserir papéis e permissões padrão
3. Criar usuário admin inicial
4. Inserir dados de exemplo (opcional)

ATENÇÃO: Execute apenas na primeira instalação!
"""

import sqlite3
from pathlib import Path
import sys

# Adiciona o diretório modules ao path
sys.path.append(str(Path(__file__).parent / "modules"))

# Importa os módulos
try:
    from auth import (
        inicializar_tabelas_auth,
        inserir_papeis_padrao,
        criar_usuario_admin_inicial
    )
    from rbac import (
        inicializar_tabelas_permissoes,
        inserir_permissoes_padrao,
        associar_permissoes_papeis
    )
except ImportError as e:
    print(f"❌ Erro ao importar módulos: {e}")
    print("\nVerifique se:")
    print("1. A pasta 'modules' existe")
    print("2. Os arquivos auth.py e rbac.py estão dentro dela")
    print("3. O arquivo __init__.py existe em 'modules'")
    sys.exit(1)


# Caminho do banco
DB_PATH = Path.home() / "FortCordis" / "data" / "fortcordis.db"


def criar_pastas_sistema():
    """
    Cria todas as pastas necessárias do sistema.
    """
    print("\n📁 Criando estrutura de pastas...")
    
    pastas = [
        Path.home() / "FortCordis" / "data",
        Path.home() / "FortCordis" / "Laudos",
        Path.home() / "FortCordis" / "Prescricoes",
        Path.home() / "FortCordis" / "Documentos",
        Path.home() / "FortCordis" / "Backups",
        Path.home() / "FortCordis" / "DB",
    ]
    
    for pasta in pastas:
        pasta.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {pasta}")
    
    print("✅ Pastas criadas com sucesso!\n")


def criar_tabelas_base():
    """
    Cria as tabelas principais do sistema que ainda não existem.
    """
    print("📊 Criando tabelas base do sistema...")
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Tabela de tutores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tutores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT UNIQUE,
            rg TEXT,
            endereco TEXT,
            bairro TEXT,
            cidade TEXT,
            estado TEXT DEFAULT 'CE',
            cep TEXT,
            telefone TEXT,
            celular TEXT,
            whatsapp TEXT,
            email TEXT,
            data_nascimento TEXT,
            profissao TEXT,
            observacoes TEXT,
            ativo INTEGER DEFAULT 1,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT
        )
    """)
    
    # Tabela de pacientes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tutor_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            especie TEXT NOT NULL CHECK(especie IN ('Canina', 'Felina', 'Outra')),
            raca TEXT,
            sexo TEXT CHECK(sexo IN ('Macho', 'Fêmea', 'Indefinido')),
            pelagem TEXT,
            data_nascimento TEXT,
            idade_anos INTEGER,
            idade_meses INTEGER,
            peso REAL,
            altura REAL,
            castrado INTEGER DEFAULT 0,
            microchip TEXT UNIQUE,
            registro TEXT,
            alergias TEXT,
            doencas_previas TEXT,
            vacinas TEXT,
            observacoes TEXT,
            foto BLOB,
            ativo INTEGER DEFAULT 1,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT,
            FOREIGN KEY (tutor_id) REFERENCES tutores(id)
        )
    """)
    
    # Tabela de atendimentos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS atendimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL,
            data_atendimento TEXT NOT NULL,
            hora_atendimento TEXT,
            veterinario_id INTEGER,
            tipo TEXT CHECK(tipo IN ('Consulta', 'Retorno', 'Exame', 'Cirurgia', 'Emergência')),
            status TEXT CHECK(status IN ('Agendado', 'Em atendimento', 'Finalizado', 'Cancelado')),
            motivo TEXT,
            observacoes TEXT,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            finalizado_em TEXT,
            FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
            FOREIGN KEY (veterinario_id) REFERENCES usuarios(id)
        )
    """)
    
    # Tabela de consultas (dados clínicos)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consultas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            atendimento_id INTEGER NOT NULL,
            queixa_principal TEXT,
            anamnese TEXT,
            exame_fisico TEXT,
            temperatura REAL,
            frequencia_cardiaca INTEGER,
            frequencia_respiratoria INTEGER,
            pressao_arterial TEXT,
            peso REAL,
            escore_corporal INTEGER,
            hidratacao TEXT,
            mucosas TEXT,
            linfonodos TEXT,
            ausculta_cardiaca TEXT,
            ausculta_respiratoria TEXT,
            abdomen TEXT,
            avaliacao TEXT,
            diagnostico TEXT,
            plano_terapeutico TEXT,
            proxima_avaliacao TEXT,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (atendimento_id) REFERENCES atendimentos(id)
        )
    """)
    
    # Tabela de evolucoes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evolucoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            atendimento_id INTEGER NOT NULL,
            data_evolucao TEXT NOT NULL,
            hora_evolucao TEXT,
            veterinario_id INTEGER NOT NULL,
            texto TEXT NOT NULL,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (atendimento_id) REFERENCES atendimentos(id),
            FOREIGN KEY (veterinario_id) REFERENCES usuarios(id)
        )
    """)
    
    # Tabela de anexos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anexos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            relacionado_tipo TEXT NOT NULL CHECK(relacionado_tipo IN ('paciente', 'atendimento', 'laudo')),
            relacionado_id INTEGER NOT NULL,
            tipo_arquivo TEXT,
            nome_arquivo TEXT NOT NULL,
            caminho_arquivo TEXT NOT NULL,
            tamanho_kb INTEGER,
            descricao TEXT,
            usuario_id INTEGER NOT NULL,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    """)
    
    conn.commit()
    conn.close()
    
    print("✅ Tabelas base criadas!\n")


def inserir_servicos_padrao():
    """
    Insere serviços padrão no sistema.
    """
    print("💰 Inserindo serviços padrão...")
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Cria tabela de serviços se não existir
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS servicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            descricao TEXT,
            valor_base REAL NOT NULL,
            duracao_minutos INTEGER DEFAULT 60,
            categoria TEXT,
            ativo INTEGER DEFAULT 1,
            data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    servicos = [
        ("Ecocardiograma", "Ecocardiograma completo", 300.00, 60, "Cardiologia"),
        ("Eletrocardiograma", "ECG com laudo", 150.00, 30, "Cardiologia"),
        ("Pressão Arterial", "Aferição de pressão arterial", 80.00, 20, "Cardiologia"),
        ("Holter 24h", "Monitorização Holter 24 horas", 450.00, 30, "Cardiologia"),
        ("Raio-X Tórax", "Radiografia torácica", 120.00, 30, "Imagem"),
        ("Ultrassom Abdominal", "Ultrassonografia abdominal", 180.00, 45, "Imagem"),
        ("Consulta Cardiológica", "Consulta com cardiologista", 200.00, 60, "Consulta"),
        ("Retorno Cardiológico", "Retorno cardiológico", 100.00, 30, "Consulta"),
    ]
    
    for nome, desc, valor, duracao, categoria in servicos:
        try:
            cursor.execute(
                """
                INSERT INTO servicos (nome, descricao, valor_base, duracao_minutos, categoria)
                VALUES (?, ?, ?, ?, ?)
                """,
                (nome, desc, valor, duracao, categoria)
            )
            print(f"  ✅ {nome}: R$ {valor:.2f}")
        except sqlite3.IntegrityError:
            print(f"  ⏭️  {nome} (já existe)")
    
    conn.commit()
    conn.close()
    
    print("✅ Serviços inseridos!\n")


def inserir_clinicas_exemplo():
    """
    Insere clínicas de exemplo (opcional).
    """
    resposta = input("\n❓ Deseja inserir clínicas de exemplo? (s/n): ").lower()
    
    if resposta != 's':
        print("⏭️  Pulando clínicas de exemplo\n")
        return
    
    print("\n🏥 Inserindo clínicas de exemplo...")
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Cria tabela se não existir
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clinicas_parceiras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            endereco TEXT,
            bairro TEXT,
            cidade TEXT,
            estado TEXT DEFAULT 'CE',
            telefone TEXT,
            whatsapp TEXT,
            email TEXT,
            cnpj TEXT,
            inscricao_estadual TEXT,
            responsavel_veterinario TEXT,
            crmv_responsavel TEXT,
            observacoes TEXT,
            ativo INTEGER DEFAULT 1,
            data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    clinicas = [
        ("Clínica Centro", "Av. Santos Dumont, 1234", "Aldeota", "Fortaleza", "(85) 3333-1111", "(85) 99999-1111"),
        ("Vet Care", "Rua Major Facundo, 567", "Centro", "Fortaleza", "(85) 3333-2222", "(85) 99999-2222"),
        ("Hospital 24h", "Av. Washington Soares, 890", "Edson Queiroz", "Fortaleza", "(85) 3333-3333", "(85) 99999-3333"),
    ]
    
    for nome, endereco, bairro, cidade, telefone, whatsapp in clinicas:
        try:
            cursor.execute(
                """
                INSERT INTO clinicas_parceiras (nome, endereco, bairro, cidade, telefone, whatsapp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (nome, endereco, bairro, cidade, telefone, whatsapp)
            )
            print(f"  ✅ {nome}")
        except sqlite3.IntegrityError:
            print(f"  ⏭️  {nome} (já existe)")
    
    conn.commit()
    conn.close()
    
    print("✅ Clínicas inseridas!\n")


def verificar_instalacao():
    """
    Verifica se tudo foi instalado corretamente.
    """
    print("\n🔍 Verificando instalação...")
    
    erros = []
    
    # Verifica banco
    if not DB_PATH.exists():
        erros.append("❌ Banco de dados não foi criado")
    else:
        print("  ✅ Banco de dados criado")
    
    # Verifica tabelas essenciais
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    tabelas_essenciais = [
        "usuarios", "papeis", "permissoes", "usuario_papel",
        "tutores", "pacientes", "atendimentos", "servicos"
    ]
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabelas_existentes = [row[0] for row in cursor.fetchall()]
    
    for tabela in tabelas_essenciais:
        if tabela in tabelas_existentes:
            print(f"  ✅ Tabela '{tabela}' existe")
        else:
            erros.append(f"❌ Tabela '{tabela}' não foi criada")
    
    # Verifica se admin foi criado
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE email = 'admin@fortcordis.com'")
    if cursor.fetchone()[0] > 0:
        print("  ✅ Usuário admin criado")
    else:
        erros.append("❌ Usuário admin não foi criado")
    
    conn.close()
    
    if erros:
        print("\n⚠️  Problemas encontrados:")
        for erro in erros:
            print(f"  {erro}")
        return False
    else:
        print("\n✅ Instalação verificada com sucesso!")
        return True


def main():
    """
    Função principal de inicialização.
    """
    print("="*70)
    print(" INICIALIZAÇÃO DO SISTEMA FORT CORDIS ".center(70))
    print("="*70)
    print("\nEste script irá preparar o sistema para o primeiro uso.")
    print("Execute apenas UMA VEZ na primeira instalação.\n")
    
    resposta = input("❓ Deseja continuar? (s/n): ").lower()
    if resposta != 's':
        print("\n❌ Inicialização cancelada.")
        return
    
    print("\n🚀 Iniciando configuração...\n")
    
    # Passo 1: Criar pastas
    criar_pastas_sistema()
    
    # Passo 2: Criar tabelas de autenticação
    print("🔐 Configurando autenticação...")
    inicializar_tabelas_auth()
    inserir_papeis_padrao()
    
    # Passo 3: Criar tabelas de permissões
    print("\n🔒 Configurando permissões...")
    inicializar_tabelas_permissoes()
    inserir_permissoes_padrao()
    associar_permissoes_papeis()
    
    # Passo 4: Criar usuário admin
    print("\n👤 Criando usuário administrador...")
    criar_usuario_admin_inicial()
    
    # Passo 5: Criar tabelas base
    criar_tabelas_base()
    
    # Passo 6: Inserir dados padrão
    inserir_servicos_padrao()
    inserir_clinicas_exemplo()
    
    # Passo 7: Verificar
    if verificar_instalacao():
        print("\n" + "="*70)
        print(" INSTALAÇÃO CONCLUÍDA COM SUCESSO! ".center(70))
        print("="*70)
        print("\n📝 PRÓXIMOS PASSOS:\n")
        print("1. Execute o sistema:")
        print("   streamlit run fortcordis_app.py\n")
        print("2. Faça login com:")
        print("   Email: admin@fortcordis.com")
        print("   Senha: Admin@2026\n")
        print("3. ⚠️  ALTERE A SENHA IMEDIATAMENTE!\n")
        print("4. Crie outros usuários conforme necessário\n")
        print("5. Configure dados profissionais (nome, CRMV)\n")
        print("="*70 + "\n")
    else:
        print("\n⚠️  Instalação concluída com problemas.")
        print("Revise os erros acima e tente executar novamente.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Instalação interrompida pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro durante a instalação: {e}")
        import traceback
        traceback.print_exc()
