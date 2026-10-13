from datetime import date


def get_today() -> date:
    """Data atual usada nas regras de empréstimo.

    Exposta como dependência do FastAPI para que os testes possam simular datas
    (via ``app.dependency_overrides``) sem manipular o relógio do sistema.
    """
    return date.today()
