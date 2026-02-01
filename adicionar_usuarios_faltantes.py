"""
Adiciona usuários faltantes ao sistema
Execute: python adicionar_usuarios_faltantes.py
"""

import sys
from pathlib import Path
import sqlite3

# Adiciona módulos ao path
sys.path.append(str(Path(__file__).parent / "modules"))
from auth import criar_usuario

print("\n" + "="*70)
print(" ADICIONAR USUÁRIOS FALTANTES ".center(70))
print("="*70 + "\n")

# Lista de usuários para criar
usuarios_desejados = [
    {
        "nome": "Dr. João Veterinário",
        "email": "veterinario@fortcordis.com",
        "senha": "Veterinario123",
        "papel": "veterinario"
    },
    {
        "nome": "Carlos Financeiro",
        "email": "financeiro@fortcordis.com",
        "senha": "Financeiro123",
        "papel": "financeiro"
    }
]

# Verifica quais já existem
DB_PATH = Path.home() / "FortCordis" / "data" / "fortcordis.db"
conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

cursor.execute("SELECT email FROM usuarios")
emails_existentes = [row[0] for row in cursor.fetchall()]
conn.close()

print("🔍 Verificando usuários existentes...\n")

# Cria apenas os que não existem
criados = 0
ja_existiam = 0

for usuario in usuarios_desejados:
    if usuario["email"] in emails_existentes:
        print(f"⏭️  {usuario['nome']}")
        print(f"   Email: {usuario['email']}")
        print(f"   Status: Já existe no sistema\n")
        ja_existiam += 1
    else:
        sucesso, msg = criar_usuario(
            nome=usuario["nome"],
            email=usuario["email"],
            senha=usuario["senha"],
            papel=usuario["papel"]
        )
        
        if sucesso:
            print(f"✅ {usuario['nome']}")
            print(f"   Email: {usuario['email']}")
            print(f"   Senha: {usuario['senha']}")
            print(f"   Papel: {usuario['papel']}")
            print(f"   {msg}\n")
            criados += 1
        else:
            print(f"❌ {usuario['nome']}")
            print(f"   Erro: {msg}\n")

print("="*70)
print(f"\n📊 RESUMO:")
print(f"   ✅ Criados: {criados}")
print(f"   ⏭️  Já existiam: {ja_existiam}")
print(f"   📋 Total de usuários desejados: {len(usuarios_desejados)}")

if criados > 0:
    print("\n🎉 NOVOS USUÁRIOS CRIADOS COM SUCESSO!")
    print("\nCREDENCIAIS:")
    print("-" * 50)
    for usuario in usuarios_desejados:
        if usuario["email"] not in emails_existentes:
            print(f"👤 {usuario['nome']}")
            print(f"   Email: {usuario['email']}")
            print(f"   Senha: {usuario['senha']}\n")
    print("-" * 50)
    
print("\n💡 Próximo passo:")
print("   Execute novamente: python verificar_usuario.py")
print("   Agora deve mostrar 5 usuários!\n")
print("="*70 + "\n")
