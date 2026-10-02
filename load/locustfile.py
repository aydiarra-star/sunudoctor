"""Load test for SunuDoctor (Locust).

This measures REAL latency and error rates against a running instance. No
result is ever fabricated: run it and read the actual numbers it prints.

Usage:
    pip install locust
    locust -f load/locustfile.py --host http://localhost:8000 \
        --headless -u 20 -r 5 -t 30s --only-summary

The script never uses real patient data: it generates throwaway, clearly
synthetic accounts per run.
"""
from __future__ import annotations

import random
import string

from locust import HttpUser, between, task


def _rand(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


class AnonymousUser(HttpUser):
    """Unauthenticated reads: public metadata and health."""

    weight = 1
    wait_time = between(0.5, 2)

    @task(3)
    def health(self):
        self.client.get("/api/health", name="/api/health")

    @task(2)
    def meta(self):
        self.client.get("/api/meta", name="/api/meta")


class ProfessionalUser(HttpUser):
    """Authenticated professional workflow."""

    weight = 3
    wait_time = between(1, 3)

    token: str | None = None

    def on_start(self):
        self._register_and_login()

    def _register_and_login(self):
        email = f"load_{_rand()}@loadtest.sn"
        payload = {
            "email": email,
            "password": "LoadTest123!",
            "full_name": f"Load {_rand(4)}",
            "role": "doctor",
            "profession": "medecin",
        }
        with self.client.post(
            "/api/auth/register", json=payload, name="/api/auth/register", catch_response=True
        ) as r:
            if r.status_code == 201:
                self.token = r.json()["access_token"]
                r.success()
            elif r.status_code == 429:
                r.success()  # rate limiting is expected under load
            else:
                r.failure(f"register {r.status_code}")

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(2)
    def list_patients(self):
        self.client.get("/api/patients", headers=self.headers, name="/api/patients")

    @task(3)
    def scribe_pipeline(self):
        if not self.token:
            return
        with self.client.post(
            "/api/patients",
            json={"first_name": "Load", "last_name": _rand(5)},
            headers=self.headers,
            name="/api/patients [create]",
            catch_response=True,
        ) as r:
            if r.status_code != 201:
                r.failure(f"create patient {r.status_code}")
                return
            patient_id = r.json()["id"]
            r.success()

        cons = self.client.post(
            "/api/scribe/consultations",
            json={"patient_id": patient_id},
            headers=self.headers,
            name="/api/scribe/consultations",
        )
        if cons.status_code != 201:
            return
        cid = cons.json()["id"]

        t = self.client.post(
            "/api/scribe/transcribe",
            json={
                "consultation_id": cid,
                "language_hint": "wolof",
                "text_hint": "Patient bi dafa am douleur ci ventre bi depuis trois days, te fièvre du.",
            },
            headers=self.headers,
            name="/api/scribe/transcribe",
        )
        if t.status_code != 200:
            return
        tid = t.json()["transcription_id"]

        self.client.post(
            "/api/scribe/structure",
            json={"transcription_id": tid},
            headers=self.headers,
            name="/api/scribe/structure",
        )

    @task(1)
    def read_plans(self):
        self.client.get("/api/billing/plans", name="/api/billing/plans")
