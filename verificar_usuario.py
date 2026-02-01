"""
Script para diagnosticar problemas de login
Execute: python verificar_usuario.py
"""

import sys
from pathlib import Path
import sqlite3

# Caminho do banco
DB_PATH = Path.home() / "FortCordis" / "data" / "fortcordis.db"

print("\n" + "="*70)
print(" DIAGNÓSTICO DE USUÁRIOS - FORT CORDIS ".center(70))
print("="*70 + "\n")

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

# Busca todos os usuários
cursor.execute("""
    SELECT 
        u.id, 
        u.nome, 
        u.email, 
        u.ativo, 
        u.tentativas_login,
        u.bloqueado_ate,
        GROUP_CONCAT(p.nome, ', ') as papeis
    FROM usuarios u
    LEFT JOIN usuario_papel up ON u.id = up.usuario_id
    LEFT JOIN papeis p ON up.papel_id = p.id
    GROUP BY u.id
    ORDER BY u.email
""")

usuarios = cursor.fetchall()

print("📋 LISTA DE USUÁRIOS:\n")

for user in usuarios:
    user_id, nome, email, ativo, tentativas, bloqueado, papeis = user
    
    print(f"👤 {nome}")
    print(f"   Email: {email}")
    print(f"   Ativo: {'✅ Sim' if ativo else '❌ Não'}")
    print(f"   Tentativas falhas: {tentativas}")
    print(f"   Bloqueado: {'🔒 Sim' if bloqueado else '✅ Não'}")
    print(f"   Papéis: {papeis or '⚠️ NENHUM PAPEL ATRIBUÍDO!'}")
    
    # Verifica problemas
    problemas = []
    if not ativo:
        problemas.append("❌ Usuário desativado")
    if bloqueado:
        problemas.append("🔒 Usuário bloqueado temporariamente")
    if not papeis:
        problemas.append("⚠️ Sem papel atribuído")
    if tentativas >= 3:
        problemas.append("⚠️ Tentativas de login esgotadas")
    
    if problemas:
        print(f"   ⚠️ PROBLEMAS ENCONTRADOS:")
        for prob in problemas:
            print(f"      - {prob}")
    else:
        print(f"   ✅ Usuário OK")
    
    print()

conn.close()

print("="*70)
print("\n💡 SOLUÇÕES:\n")
print("1. Se usuário está BLOQUEADO:")
print("   → Execute: python desbloquear_usuario.py [email]\n")
print("2. Se usuário está DESATIVADO:")
print("   → Execute: python reativar_usuario.py [email]\n")
print("3. Se usuário NÃO TEM PAPEL:")
print("   → Execute: python corrigir_papeis.py\n")
print("="*70 + "\n")
