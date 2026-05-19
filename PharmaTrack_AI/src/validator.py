import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError, ConfigDict

logger = logging.getLogger(__name__)

class ParameterType(str, Enum):
    TEMP = "TEMP"
    PRESS = "PRESS"
    FLOW = "FLOW"

class StatusCode(str, Enum):
    OK = "OK"
    WARN = "WARN"
    CRITICAL = "CRITICAL"

class ParameterBoundaries:
    TEMP_MIN, TEMP_MAX = 15.0, 85.0
    PRESS_MIN, PRESS_MAX = 0.5, 5.0
    FLOW_MIN, FLOW_MAX = 0.1, 2.5
    
    @classmethod
    def get_bounds(cls, parameter_type: str) -> tuple[float, float]:
        bounds_map = {"TEMP": (cls.TEMP_MIN, cls.TEMP_MAX), "PRESS": (cls.PRESS_MIN, cls.PRESS_MAX), "FLOW": (cls.FLOW_MIN, cls.FLOW_MAX)}
        return bounds_map[parameter_type]

class LogRecord(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    timestamp: str
    instrument_id: str = Field(..., pattern=r"^INST-[A-Z0-9]{3}$")
    parameter_type: ParameterType
    value: float
    status_code: StatusCode
    raw_line: Optional[str] = None
    line_number: Optional[int] = None

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp_format(cls, value: str) -> str:
        try:
            datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise ValueError(f"Timestamp must be in YYYY-MM-DD HH:MM:SS format, got: {value}")
        return value

    @model_validator(mode="after")
    def validate_value_boundaries(self) -> "LogRecord":
        min_bound, max_bound = ParameterBoundaries.get_bounds(self.parameter_type.value)
        if not (min_bound <= self.value <= max_bound):
            raise ValueError(f"{self.parameter_type.value} value {self.value} outside range [{min_bound}, {max_bound}]")
        return self

    def to_dict(self) -> dict[str, Any]:
        d = self.model_dump()
        d["parameter_type"] = self.parameter_type.value
        d["status_code"] = self.status_code.value
        return d

class LogValidator:
    def __init__(self, quarantine_dir: Path) -> None:
        self._quarantine_dir = quarantine_dir
        self._validated_count = 0
        self._quarantined_count = 0
        self._quarantine_dir.mkdir(parents=True, exist_ok=True)
        
    def validate_record(self, data: dict[str, Any]) -> Optional[LogRecord]:
        try:
            validated = LogRecord(**data)
            self._validated_count += 1
            return validated
        except ValidationError as exc:
            self._quarantined_count += 1
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            q_file = self._quarantine_dir / f"quarantine_{ts}.json"
            
            # Pydantic v2 errors standard formats dictionary format me extract karne ke liye
            # .errors() me raw exceptions ko string components me map kar dete hain string formatting se
            serializable_errors = []
            for err in exc.errors():
                serializable_err = err.copy()
                if "ctx" in serializable_err and "error" in serializable_err["ctx"]:
                    # Raw ValueError object ko clean string representation me badlo
                    serializable_err["ctx"]["error"] = str(serializable_err["ctx"]["error"])
                serializable_errors.append(serializable_err)

            with open(q_file, "w") as f:
                json.dump({
                    "original_data": data, 
                    "errors": serializable_errors
                }, f, indent=2)
            return None

    def validate_batch(self, records: list[dict[str, Any]]) -> list[LogRecord]:
        valid_records = []
        for r in records:
            v = self.validate_record(r)
            if v: valid_records.append(v)
        return valid_records

    def get_statistics(self) -> dict[str, int]:
        return {"validated": self._validated_count, "quarantined": self._quarantined_count}