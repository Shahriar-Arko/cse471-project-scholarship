from app.extensions import db
import datetime

class CostReference(db.Document):
    country = db.StringField(required=True, unique=True)
    visa_fee = db.FloatField(default=0.0)
    language_test_fee = db.FloatField(default=0.0)
    average_travel_cost = db.FloatField(default=0.0)
    annual_insurance_cost = db.FloatField(default=0.0)
    monthly_living_cost = db.FloatField(default=0.0)
    average_application_fee = db.FloatField(default=0.0)
    currency = db.StringField(default="USD")
    additional_notes = db.StringField(default="")

    meta = {'collection': 'cost_references'}

    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
