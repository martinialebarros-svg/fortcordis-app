"""
Script para verificar se laudos estão sendo salvos no banco
Execute: python verificar_laudos_salvos.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path.home() / "FortCordis" / "data" / "fortcordis.db"

print("\n" + "="*70)
print(" VERIFICAR LAUDOS NO BANCO ".center(70))
print("="*70 + "\n")

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

# Verifica tabelas de laudos
print("🔍 Tabelas de laudos:\n")

cursor.execute("""
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name LIKE 'laudos%'
    ORDER BY name
""")

tabelas_laudos = cursor.fetchall()

if tabelas_laudos:
    print(f"✅ Encontradas {len(tabelas_laudos)} tabela(s):\n")
    
    for tab in tabelas_laudos:
        nome_tabela = tab[0]
        
        # Conta registros
        cursor.execute(f"SELECT COUNT(*) FROM {nome_tabela}")
        qtd = cursor.fetchone()[0]
        
        print(f"   📋 {nome_tabela}: {qtd} laudo(s)")
        
        # Mostra estrutura
        cursor.execute(f"PRAGMA table_info({nome_tabela})")
        colunas = cursor.fetchall()
        print(f"      Colunas: {', '.join([c[1] for c in colunas[:10]])}...")
        
        # Se tem laudos, mostra alguns
        if qtd > 0:
            cursor.execute(f"SELECT * FROM {nome_tabela} ORDER BY id DESC LIMIT 3")
            laudos = cursor.fetchall()
            
            print(f"\n      Últimos laudos:")
            for laudo in laudos:
                print(f"         ID: {laudo[0]}")
                # Mostra alguns campos
                if len(laudo) > 1:
                    print(f"         Paciente: {laudo[1] if len(laudo) > 1 else 'N/A'}")
                if len(laudo) > 2:
                    print(f"         Data: {laudo[2] if len(laudo) > 2 else 'N/A'}")
                print()
        else:
            print(f"      ⚠️  NENHUM laudo salvo!\n")
        
        print()
else:
    print("❌ NENHUMA tabela de laudos encontrada!\n")

conn.close()

print("="*70)
print("\n💡 ANÁLISE:\n")

if not tabelas_laudos:
    print("   ❌ Tabelas de laudos não existem")
    print("   → Execute: python corrigir_laudos_e_clinicas_v2.py")
else:
    tem_laudos = False
    for tab in tabelas_laudos:
        cursor = sqlite3.connect(str(DB_PATH)).cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {tab[0]}")
        if cursor.fetchone()[0] > 0:
            tem_laudos = True
            break
    
    if tem_laudos:
        print("   ✅ Laudos estão sendo salvos no banco")
        print("   → O problema pode estar na busca")
    else:
        print("   ⚠️  Tabelas existem MAS estão vazias")
        print("   → Laudos NÃO estão sendo salvos no banco")
        print("   → Apenas o PDF é gerado")

print("\n🎯 PRÓXIMO PASSO:")
print("   Me envie o resultado completo deste script!\n")

print("="*70 + "\n")
