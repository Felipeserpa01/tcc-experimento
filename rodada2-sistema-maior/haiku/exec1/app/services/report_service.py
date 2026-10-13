from datetime import date
from sqlalchemy.orm import Session

from app.repositories.report_repository import ReportRepository
from app.core.exceptions import ValidationError


class ReportService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ReportRepository(db)

    def get_appointments_by_period(self, start_date: date, end_date: date):
        if start_date > end_date:
            raise ValidationError("Start date must be before end date")

        appointments = self.repository.get_appointments_by_period(start_date, end_date)
        return {
            "total": len(appointments),
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "appointments": appointments
        }

    def get_appointments_by_status(self, start_date: date = None, end_date: date = None):
        if start_date and end_date and start_date > end_date:
            raise ValidationError("Start date must be before end date")

        results = self.repository.get_appointments_by_status(start_date, end_date)
        return {
            "by_status": [
                {"status": str(status), "count": count}
                for status, count in results
            ]
        }

    def get_no_show_rate(self, doctor_id: int = None):
        results = self.repository.get_no_show_count_by_doctor(doctor_id)
        report = []
        for doctor_id_val, total, no_show_count in results:
            no_show_count = no_show_count or 0
            rate = (no_show_count / total * 100) if total > 0 else 0
            report.append({
                "doctor_id": doctor_id_val,
                "total_appointments": total,
                "no_shows": no_show_count,
                "no_show_rate_percent": round(rate, 2)
            })
        return report

    def get_revenue_by_period(self, start_date: date, end_date: date):
        if start_date > end_date:
            raise ValidationError("Start date must be before end date")

        result = self.repository.get_revenue_by_period(start_date, end_date)
        total_revenue = result[0] if result[0] else 0.0
        charge_count = result[1] if result[1] else 0

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_revenue": round(total_revenue, 2),
            "charge_count": charge_count,
            "average_charge": round(total_revenue / charge_count, 2) if charge_count > 0 else 0.0
        }

    def get_most_seen_patients(self, limit: int = 10):
        if limit <= 0 or limit > 100:
            raise ValidationError("Limit must be between 1 and 100")

        results = self.repository.get_most_seen_patients(limit)
        return {
            "patients": [
                {
                    "patient_id": patient.id,
                    "patient_name": patient.user.full_name,
                    "appointment_count": count
                }
                for patient, count in results
            ]
        }
