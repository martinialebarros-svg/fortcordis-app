import sqlite3
from pathlib import Path

# Caminho Windows
DB_PATH = Path(r"C:\Users\marti\FortCordis\data\fortcordis.db")

print("\n" + "="*70)
print(" VERIFICAR SE LAUDO FOI SALVO ".center(70))
print("="*70 + "\n")

print(f"🔍 Verificando banco: {DB_PATH}\n")

if not DB_PATH.exists():
    print("❌ BANCO NÃO EXISTE!")
    print(f"   Procurado em: {DB_PATH}\n")
    
    # Tenta caminho alternativo
    alt_path = Path(r"C:\Users\marti\Desktop\FortCordis_Novo\fortcordis.db")
    print(f"🔍 Tentando caminho alternativo: {alt_path}")
    
    if alt_path.exists():
        print("   ✅ Banco encontrado aqui!")
        DB_PATH = alt_path
    else:
        print("   ❌ Também não existe\n")
        print("="*70)
        exit()

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

tabelas = ["laudos_ecocardiograma", "laudos_eletrocardiograma", "laudos_pressao_arterial"]

total_geral = 0

for tabela in tabelas:
    cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
    qtd = cursor.fetchone()[0]
    total_geral += qtd
    
    print(f"📋 {tabela}: {qtd} laudo(s)")
    
    if qtd > 0:
        cursor.execute(f"""
            SELECT id, nome_paciente, data_exame, nome_clinica, arquivo_json
            FROM {tabela}
            ORDER BY id DESC
            LIMIT 3
        """)
        
        print("\n   Últimos laudos:")
        for row in cursor.fetchall():
            print(f"      ID: {row[0]}")
            print(f"      Paciente: {row[1]}")
            print(f"      Data: {row[2]}")
            print(f"      Clínica: {row[3]}")
            print(f"      JSON: {row[4]}")
            print()

conn.close()

print("="*70)
print(f"\n📊 TOTAL: {total_geral} laudo(s) no banco\n")

if total_geral == 0:
    print("⚠️  NENHUM laudo foi salvo!")
    print("\n💡 POSSÍVEIS CAUSAS:")
    print("   1. O código não foi executado (verifique se adicionou)")
    print("   2. Deu erro silencioso (veja mensagens do Streamlit)")
    print("   3. Está salvando em outro banco")
    print("\n🎯 PRÓXIMO PASSO:")
    print("   Gere um laudo NOVO agora e veja se aparece:")
    print("   ✅ Laudo #X registrado no sistema!")
else:
    print("✅ Laudos foram salvos com sucesso!")
    print("\n🎯 PRÓXIMO PASSO:")
    print("   O problema está na BUSCA, não no salvamento")
    print("   Me envie o código da busca!")

print("\n" + "="*70 + "\n")
