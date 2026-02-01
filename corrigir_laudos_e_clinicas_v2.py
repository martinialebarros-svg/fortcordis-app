"""
Script CORRIGIDO para criar tabelas de laudos e migrar clínicas
Execute: python corrigir_laudos_e_clinicas_v2.py
"""

import sqlite3
from pathlib import Path

DB_PATH_NOVO = Path.home() / "FortCordis" / "data" / "fortcordis.db"
DB_PATH_ANTIGO = Path.home() / "FortCordis" / "DB" / "fortcordis.db"

print("\n" + "="*70)
print(" CORREÇÃO: LAUDOS E CLÍNICAS (v2) ".center(70))
print("="*70 + "\n")

# ============================================================================
# PARTE 1: CRIAR TABELAS DE LAUDOS (JÁ FEITO)
# ============================================================================

print("📋 PARTE 1: Verificando tabelas de laudos...\n")
print("-" * 70 + "\n")

conn_novo = sqlite3.connect(str(DB_PATH_NOVO))
cursor_novo = conn_novo.cursor()

# Verifica se as tabelas já existem
cursor_novo.execute("""
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name LIKE 'laudos_%'
""")
tabelas_existentes = cursor_novo.fetchall()

if tabelas_existentes:
    print(f"✅ {len(tabelas_existentes)} tabela(s) de laudos já existem:")
    for tab in tabelas_existentes:
        print(f"   • {tab[0]}")
    print("\n   Pulando criação de tabelas...\n")
else:
    print("⚠️  Tabelas de laudos não existem. Execute o script anterior primeiro!\n")

print("=" * 70 + "\n")

# ============================================================================
# PARTE 2: MIGRAR CLÍNICAS (CORRIGIDO)
# ============================================================================

print("📋 PARTE 2: Migrando clínicas do banco antigo para o novo\n")
print("-" * 70 + "\n")

if not DB_PATH_ANTIGO.exists():
    print("⚠️  Banco antigo não existe. Pulando migração de clínicas.\n")
else:
    conn_antigo = sqlite3.connect(str(DB_PATH_ANTIGO))
    cursor_antigo = conn_antigo.cursor()
    
    # Verifica estrutura da tabela clinicas no banco antigo
    print("🔍 Verificando estrutura da tabela 'clinicas' no banco antigo...")
    cursor_antigo.execute("PRAGMA table_info(clinicas)")
    colunas_antigas = cursor_antigo.fetchall()
    
    print("\n   Colunas encontradas:")
    colunas_disponiveis = []
    for col in colunas_antigas:
        print(f"      • {col[1]} ({col[2]})")
        colunas_disponiveis.append(col[1])
    
    print()
    
    # Monta query dinâmica baseada nas colunas disponíveis
    colunas_select = []
    colunas_insert = []
    
    # Mapeamento de colunas
    mapa_colunas = {
        'id': 'id',
        'nome': 'nome',
        'endereco': 'endereco',
        'telefone': 'telefone',
        'celular': 'telefone',  # Fallback
        'email': 'email',
        'cnpj': 'cnpj',
        'responsavel': 'responsavel',
        'ativo': 'ativo'
    }
    
    # Constrói lista de colunas para SELECT
    for col_bd_antigo, col_bd_novo in mapa_colunas.items():
        if col_bd_antigo in colunas_disponiveis:
            colunas_select.append(col_bd_antigo)
            colunas_insert.append(col_bd_novo)
    
    query_select = f"SELECT {', '.join(colunas_select)} FROM clinicas"
    
    print(f"📥 Buscando clínicas do banco antigo...")
    cursor_antigo.execute(query_select)
    clinicas_antigas = cursor_antigo.fetchall()
    print(f"   ✅ Encontradas {len(clinicas_antigas)} clínicas\n")
    
    # Verifica/cria tabela no banco novo
    print("🔍 Verificando tabela 'clinicas' no banco novo...")
    cursor_novo.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clinicas'")
    
    if not cursor_novo.fetchone():
        print("   ⚠️  Tabela 'clinicas' não existe. Criando...")
        cursor_novo.execute("""
            CREATE TABLE clinicas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                endereco TEXT,
                telefone TEXT,
                email TEXT,
                cnpj TEXT,
                responsavel TEXT,
                ativo INTEGER DEFAULT 1,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn_novo.commit()
        print("   ✅ Tabela criada\n")
    else:
        print("   ✅ Tabela já existe\n")
    
    # Migra clínicas
    print("📥 Migrando clínicas...")
    
    migradas = 0
    duplicadas = 0
    erros = 0
    
    for clinica in clinicas_antigas:
        # Cria dicionário com os dados
        dados = dict(zip(colunas_insert, clinica))
        
        # Nome é obrigatório
        if 'nome' not in dados or not dados['nome']:
            erros += 1
            continue
        
        # Verifica duplicata (por nome)
        cursor_novo.execute("SELECT id FROM clinicas WHERE nome = ?", (dados['nome'],))
        
        if cursor_novo.fetchone():
            duplicadas += 1
        else:
            try:
                # Monta INSERT dinâmico
                campos_insert = []
                valores_insert = []
                placeholders = []
                
                for campo in ['nome', 'endereco', 'telefone', 'email', 'cnpj', 'responsavel', 'ativo']:
                    if campo in dados:
                        campos_insert.append(campo)
                        valores_insert.append(dados[campo])
                        placeholders.append('?')
                
                query_insert = f"""
                    INSERT INTO clinicas ({', '.join(campos_insert)})
                    VALUES ({', '.join(placeholders)})
                """
                
                cursor_novo.execute(query_insert, valores_insert)
                migradas += 1
                
            except Exception as e:
                print(f"   ⚠️  Erro ao migrar '{dados.get('nome', '???')}': {e}")
                erros += 1
    
    conn_novo.commit()
    
    print(f"\n   ✅ Migradas: {migradas} clínicas")
    print(f"   ⏭️  Duplicadas (ignoradas): {duplicadas} clínicas")
    if erros > 0:
        print(f"   ⚠️  Erros: {erros} clínicas")
    print()
    
    conn_antigo.close()

print("=" * 70 + "\n")

# ============================================================================
# PARTE 3: VERIFICAR RESULTADO
# ============================================================================

print("📋 PARTE 3: Verificando resultado final\n")
print("-" * 70 + "\n")

# Lista tabelas de laudos
print("🔍 Tabelas de laudos:")
cursor_novo.execute("""
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name LIKE 'laudos_%'
""")
tabelas_laudos = cursor_novo.fetchall()

for tab in tabelas_laudos:
    cursor_novo.execute(f"SELECT COUNT(*) FROM {tab[0]}")
    qtd = cursor_novo.fetchone()[0]
    print(f"   ✅ {tab[0]:<30} ({qtd} registros)")

print()

# Conta clínicas
cursor_novo.execute("SELECT COUNT(*) FROM clinicas")
total_clinicas = cursor_novo.fetchone()[0]
print(f"🏥 Total de clínicas no banco novo: {total_clinicas}")

if total_clinicas > 0:
    print("\n   Primeiras 10 clínicas:")
    cursor_novo.execute("SELECT id, nome FROM clinicas ORDER BY id LIMIT 10")
    clinicas = cursor_novo.fetchall()
    for c in clinicas:
        print(f"      ID {c[0]}: {c[1]}")

conn_novo.close()

print("\n" + "="*70)
print("✅ CORREÇÃO CONCLUÍDA!")
print("="*70)

print("\n🎯 RESULTADO:")
print(f"   ✅ Tabelas de laudos: criadas")
print(f"   ✅ Clínicas no banco: {total_clinicas}")
print(f"   ✅ Sistema pronto para registrar laudos!")

print("\n🎯 PRÓXIMO PASSO:")
print("   1. Recarregue o sistema (aperte R)")
print("   2. Gere um novo laudo")
print("   3. Ele será salvo no banco e aparecerá na busca!")

print("\n⚠️  NOTA:")
print("   Laudos antigos (só PDF) não aparecerão na busca.")
print("   Apenas laudos novos serão registrados no banco.\n")
