"""
Exemplo de uso da Biblioteca API

Este script demonstra como usar os principais endpoints da API.
Certifique-se de que a aplicação está rodando com:
    uvicorn app.main:app --reload
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_response(title, response):
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except:
        print(f"Response: {response.text}")

def main():
    print("\n🏛️  EXEMPLO DE USO DA BIBLIOTECA API\n")

    # 1. Registrar um bibliotecário
    print("\n1️⃣  Registrando um bibliotecário...")
    response = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "username": "maria_silva",
            "email": "maria@biblioteca.com",
            "password": "SenhaForte123",
            "user_type": "librarian"
        }
    )
    print_response("Registro do Bibliotecário", response)

    # 2. Login do bibliotecário
    print("\n2️⃣  Fazendo login como bibliotecário...")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "username": "maria_silva",
            "password": "SenhaForte123"
        }
    )
    print_response("Login do Bibliotecário", response)
    librarian_token = response.json()["access_token"]

    # 3. Registrar um leitor
    print("\n3️⃣  Registrando um leitor...")
    response = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "username": "joao_santos",
            "email": "joao@email.com",
            "password": "SenhaForte456",
            "user_type": "reader"
        }
    )
    print_response("Registro do Leitor", response)

    # 4. Login do leitor
    print("\n4️⃣  Fazendo login como leitor...")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "username": "joao_santos",
            "password": "SenhaForte456"
        }
    )
    print_response("Login do Leitor", response)
    reader_token = response.json()["access_token"]

    # 5. Criar alguns livros (como bibliotecário)
    print("\n5️⃣  Criando livros (como bibliotecário)...")
    books_data = [
        {
            "title": "Clean Code",
            "author": "Robert C. Martin",
            "isbn": "978-0132350884",
            "year": 2008,
            "total_quantity": 3,
            "description": "A handbook of agile software craftsmanship"
        },
        {
            "title": "The Pragmatic Programmer",
            "author": "Andrew Hunt & David Thomas",
            "isbn": "978-0135957059",
            "year": 2019,
            "total_quantity": 2,
            "description": "Your Journey to Mastery"
        },
        {
            "title": "Design Patterns",
            "author": "Gang of Four",
            "isbn": "978-0201633610",
            "year": 1994,
            "total_quantity": 4,
            "description": "Elements of Reusable Object-Oriented Software"
        }
    ]

    book_ids = []
    for book_data in books_data:
        response = requests.post(
            f"{BASE_URL}/books/",
            headers={"Authorization": f"Bearer {librarian_token}"},
            json=book_data
        )
        print_response(f"Criando livro: {book_data['title']}", response)
        if response.status_code == 201:
            book_ids.append(response.json()["id"])

    # 6. Listar todos os livros
    print("\n6️⃣  Listando todos os livros...")
    response = requests.get(f"{BASE_URL}/books/")
    print_response("Lista de Livros", response)

    # 7. Buscar livros por título
    print("\n7️⃣  Buscando livros por título (Clean)...")
    response = requests.get(f"{BASE_URL}/books/search?title=Clean")
    print_response("Resultado da Busca", response)

    # 8. Emprestar um livro (como leitor)
    if book_ids:
        print("\n8️⃣  Emprestando um livro...")
        response = requests.post(
            f"{BASE_URL}/loans/",
            headers={"Authorization": f"Bearer {reader_token}"},
            json={"book_id": book_ids[0]}
        )
        print_response("Empréstimo Criado", response)
        if response.status_code == 201:
            loan_id = response.json()["id"]

            # 9. Listar empréstimos ativos
            print("\n9️⃣  Listando empréstimos ativos...")
            response = requests.get(
                f"{BASE_URL}/loans/user/active",
                headers={"Authorization": f"Bearer {reader_token}"}
            )
            print_response("Empréstimos Ativos", response)

            # 10. Verificar informações do livro
            print("\n🔟 Verificando quantidade disponível do livro...")
            response = requests.get(f"{BASE_URL}/books/{book_ids[0]}")
            print_response("Informações do Livro", response)

            # 11. Devolver o livro
            print("\n1️⃣1️⃣  Devolvendo o livro...")
            response = requests.post(
                f"{BASE_URL}/loans/return",
                headers={"Authorization": f"Bearer {reader_token}"},
                json={"loan_id": loan_id}
            )
            print_response("Devolução Registrada", response)

            # 12. Verificar quantidade disponível após devolução
            print("\n1️⃣2️⃣  Verificando quantidade após devolução...")
            response = requests.get(f"{BASE_URL}/books/{book_ids[0]}")
            print_response("Informações do Livro (Após Devolução)", response)

    print("\n" + "="*60)
    print("✅ DEMONSTRAÇÃO CONCLUÍDA!")
    print("="*60)
    print("\n📚 Acesse a documentação em http://localhost:8000/docs")

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("❌ ERRO: Não foi possível conectar à API!")
        print("   Certifique-se de que a aplicação está rodando com:")
        print("   uvicorn app.main:app --reload")
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")
