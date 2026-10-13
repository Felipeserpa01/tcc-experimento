from sqlalchemy.orm import Session
from app.models import WaitingList

class WaitingListRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, waiting_list_id: int):
        return self.db.query(WaitingList).filter(WaitingList.id == waiting_list_id).first()

    def get_by_appointment(self, appointment_id: int):
        return self.db.query(WaitingList).filter(
            WaitingList.appointment_id == appointment_id
        ).order_by(WaitingList.position).all()

    def get_by_patient(self, patient_id: int):
        return self.db.query(WaitingList).filter(
            WaitingList.patient_id == patient_id
        ).all()

    def get_first_in_queue(self, appointment_id: int):
        return self.db.query(WaitingList).filter(
            WaitingList.appointment_id == appointment_id
        ).order_by(WaitingList.position).first()

    def get_not_notified(self):
        return self.db.query(WaitingList).filter(
            WaitingList.notified == False
        ).all()

    def get_all(self, skip: int = 0, limit: int = 100):
        return self.db.query(WaitingList).offset(skip).limit(limit).all()

    def create(self, waiting_list: WaitingList):
        self.db.add(waiting_list)
        self.db.commit()
        self.db.refresh(waiting_list)
        return waiting_list

    def update(self, waiting_list: WaitingList):
        self.db.commit()
        self.db.refresh(waiting_list)
        return waiting_list

    def delete(self, waiting_list_id: int):
        waiting_list = self.get_by_id(waiting_list_id)
        if waiting_list:
            self.db.delete(waiting_list)
            self.db.commit()
            return True
        return False
