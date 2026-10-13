"""Integration tests for billing: charges, insurance discount and payment status rules."""
from tests.conftest import next_weekday_datetime


def _schedule(client, recepcionista_headers, patient_id, professional_id, when):
    return client.post(
        "/appointments",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "data_hora": when.isoformat(),
            "duracao_minutos": 30,
        },
        headers=recepcionista_headers,
    ).json()


def test_create_billing_for_appointment(
    client, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, _ = medico_user_and_headers
    patient, _ = patient_user_and_headers
    when = next_weekday_datetime(0, 10, 0)
    appt = _schedule(client, recepcionista_headers, patient.id, professional.id, when)

    resp = client.post(
        "/billing",
        json={
            "patient_id": patient.id,
            "appointment_id": appt["id"],
            "tipo": "consulta",
            "valor": "200.00",
            "forma_pagamento": "pix",
        },
        headers=recepcionista_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert float(body["valor_final"]) == 200.00
    assert body["status"] == "pendente"


def test_create_billing_applies_convenio_discount(
    client, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, _ = medico_user_and_headers
    patient, _ = patient_user_and_headers  # fixture patient has convenio="Unimed"
    when = next_weekday_datetime(1, 10, 0)
    appt = _schedule(client, recepcionista_headers, patient.id, professional.id, when)

    resp = client.post(
        "/billing",
        json={
            "patient_id": patient.id,
            "appointment_id": appt["id"],
            "tipo": "consulta",
            "valor": "300.00",
            "forma_pagamento": "convenio",
            "aplicar_desconto_convenio": True,
        },
        headers=recepcionista_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["convenio_aplicado"] is True
    assert float(body["valor_desconto"]) == 60.00  # 20% of 300.00
    assert float(body["valor_final"]) == 240.00


def test_create_billing_rejects_discount_without_convenio(
    client, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, _ = medico_user_and_headers
    patient, _ = patient_user_and_headers
    client.put(f"/patients/{patient.id}", json={"convenio": None}, headers=recepcionista_headers)

    when = next_weekday_datetime(2, 10, 0)
    appt = _schedule(client, recepcionista_headers, patient.id, professional.id, when)

    resp = client.post(
        "/billing",
        json={
            "patient_id": patient.id,
            "appointment_id": appt["id"],
            "tipo": "consulta",
            "valor": "150.00",
            "forma_pagamento": "dinheiro",
            "aplicar_desconto_convenio": True,
        },
        headers=recepcionista_headers,
    )
    assert resp.status_code == 422


def test_create_billing_rejects_duplicate_for_same_appointment(
    client, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, _ = medico_user_and_headers
    patient, _ = patient_user_and_headers
    when = next_weekday_datetime(3, 10, 0)
    appt = _schedule(client, recepcionista_headers, patient.id, professional.id, when)

    payload = {
        "patient_id": patient.id,
        "appointment_id": appt["id"],
        "tipo": "consulta",
        "valor": "200.00",
        "forma_pagamento": "pix",
    }
    first = client.post("/billing", json=payload, headers=recepcionista_headers)
    assert first.status_code == 201

    second = client.post("/billing", json=payload, headers=recepcionista_headers)
    assert second.status_code == 409


def test_pay_billing_and_prevent_double_payment(
    client, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, _ = medico_user_and_headers
    patient, _ = patient_user_and_headers
    when = next_weekday_datetime(4, 10, 0)
    appt = _schedule(client, recepcionista_headers, patient.id, professional.id, when)

    billing = client.post(
        "/billing",
        json={
            "patient_id": patient.id,
            "appointment_id": appt["id"],
            "tipo": "consulta",
            "valor": "180.00",
            "forma_pagamento": "cartao_credito",
        },
        headers=recepcionista_headers,
    ).json()

    pay = client.post(f"/billing/{billing['id']}/pay", json={}, headers=recepcionista_headers)
    assert pay.status_code == 200
    assert pay.json()["status"] == "pago"

    pay_again = client.post(f"/billing/{billing['id']}/pay", json={}, headers=recepcionista_headers)
    assert pay_again.status_code == 409


def test_cancel_paid_billing_rejected(
    client, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, _ = medico_user_and_headers
    patient, _ = patient_user_and_headers
    when = next_weekday_datetime(5, 10, 0)
    appt = _schedule(client, recepcionista_headers, patient.id, professional.id, when)

    billing = client.post(
        "/billing",
        json={
            "patient_id": patient.id,
            "appointment_id": appt["id"],
            "tipo": "consulta",
            "valor": "100.00",
            "forma_pagamento": "dinheiro",
        },
        headers=recepcionista_headers,
    ).json()
    client.post(f"/billing/{billing['id']}/pay", json={}, headers=recepcionista_headers)

    cancel = client.post(f"/billing/{billing['id']}/cancel", headers=recepcionista_headers)
    assert cancel.status_code == 409


def test_patient_cannot_create_billing(client, recepcionista_headers, medico_user_and_headers, patient_user_and_headers):
    professional, _ = medico_user_and_headers
    patient, patient_headers = patient_user_and_headers
    when = next_weekday_datetime(0, 11, 0)
    appt = _schedule(client, recepcionista_headers, patient.id, professional.id, when)

    resp = client.post(
        "/billing",
        json={
            "patient_id": patient.id,
            "appointment_id": appt["id"],
            "tipo": "consulta",
            "valor": "100.00",
            "forma_pagamento": "dinheiro",
        },
        headers=patient_headers,
    )
    assert resp.status_code == 403


def test_patient_can_view_only_own_billing(
    client, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, _ = medico_user_and_headers
    patient, patient_headers = patient_user_and_headers
    when = next_weekday_datetime(1, 11, 0)
    appt = _schedule(client, recepcionista_headers, patient.id, professional.id, when)

    billing = client.post(
        "/billing",
        json={
            "patient_id": patient.id,
            "appointment_id": appt["id"],
            "tipo": "consulta",
            "valor": "220.00",
            "forma_pagamento": "pix",
        },
        headers=recepcionista_headers,
    ).json()

    own = client.get(f"/billing/{billing['id']}", headers=patient_headers)
    assert own.status_code == 200

    listing = client.get("/billing", headers=patient_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
