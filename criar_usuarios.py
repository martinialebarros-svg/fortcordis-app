"""
Script para criar usuários no Fort Cordis
Execute: python criar_usuarios.py
"""

import sys
from pathlib import Path

# Adiciona módulos ao path
sys.path.append(str(Path(__file__).parent / "modules"))

from auth import criar_usuario

print("\n" + "="*70)
print(" CRIAR NOVOS USUÁRIOS - FORT CORDIS ".center(70))
print("="*70 + "\n")

# Lista de usuários para criar
usuarios = [
    {
        "nome": "Maria Recepção",
        "email": "recepcao@fortcordis.com",
        "senha": "Recepcao123",
        "papel": "recepcao"
    },
    {
        "nome": "Dr. João Veterinário",
        "email": "veterinario@fortcordis.com",
        "senha": "Vet123",
        "papel": "veterinario"
    },
    {
        "nome": "Dra. Ana Cardiologista",
        "email": "cardio@fortcordis.com",
        "senha": "Cardio123",
        "papel": "cardiologista"
    },
    {
        "nome": "Carlos Financeiro",
        "email": "financeiro@fortcordis.com",
        "senha": "Fin123",
        "papel": "financeiro"
    }
]

print("📝 Criando usuários de teste...\n")

for usuario in usuarios:
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
        print(f"   Papel: {usuario['papel']}\n")
    else:
        print(f"⚠️  {msg}\n")

print("="*70)
print("\n🎉 USUÁRIOS CRIADOS COM SUCESSO!\n")
print("Para testar:")
print("1. Faça logout do admin")
print("2. Faça login com cada usuário acima")
print("3. Observe as diferenças de permissões\n")
print("="*70 + "\n")
