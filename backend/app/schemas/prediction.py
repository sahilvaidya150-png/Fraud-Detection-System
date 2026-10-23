from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TransactionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: int = Field(ge=1, le=743)
    type: Literal["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"]
    amount: float = Field(ge=0, le=92_445_516.64, allow_inf_nan=False)
    oldbalanceOrg: float = Field(ge=0, le=59_585_040.37, allow_inf_nan=False)
    newbalanceOrig: float = Field(ge=0, le=49_585_040.37, allow_inf_nan=False)
    oldbalanceDest: float = Field(ge=0, le=356_015_889.35, allow_inf_nan=False)
    newbalanceDest: float = Field(ge=0, le=356_179_278.92, allow_inf_nan=False)


class PredictionResponse(BaseModel):
    transaction_id: int
    fraud_probability: float = Field(ge=0, le=1)
    threshold: float = Field(ge=0, le=1)
    is_fraud: bool
    risk_level: Literal["High", "Low"]