import re
import logging
from pathlib import Path
from typing import Optional, Generator
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class ParsedLogEntry:
    timestamp: str
    instrument_id: str
    parameter_type: str
    value: float
    status_code: str
    raw_line: str
    line_number: int

@dataclass
class ParseFailure:
    raw_line: str
    line_number: int
    error_reason: str

@dataclass
class ParseStatistics:
    total_lines: int = 0
    successful_parses: int = 0
    failed_parses: int = 0
    empty_lines: int = 0
    failures: list[ParseFailure] = field(default_factory=list)

class LogParser:
    TIMESTAMP_PATTERN: str = r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})"
    INSTRUMENT_ID_PATTERN: str = r"(INST-[A-Z0-9]{3})"
    PARAMETER_TYPE_PATTERN: str = r"(TEMP|PRESS|FLOW)"
    VALUE_PATTERN: str = r"(-?\d+\.?\d*)"
    STATUS_CODE_PATTERN: str = r"(OK|WARN|CRITICAL)"
    
    def __init__(self, delimiter: str = r"\s*\|\s*") -> None:
        self._delimiter = delimiter
        self._compiled_pattern = self._build_master_pattern()
        self._statistics = ParseStatistics()
        
    def _build_master_pattern(self) -> re.Pattern[str]:
        pattern_parts = [
            f"^\s*{self.TIMESTAMP_PATTERN}",
            self.INSTRUMENT_ID_PATTERN,
            self.PARAMETER_TYPE_PATTERN,
            self.VALUE_PATTERN,
            f"{self.STATUS_CODE_PATTERN}\s*$"
        ]
        master_pattern = self._delimiter.join(pattern_parts)
        return re.compile(master_pattern, re.IGNORECASE)
        
    def _parse_single_line(self, line: str, line_number: int) -> Optional[ParsedLogEntry]:
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("#"):
            self._statistics.empty_lines += 1
            return None
            
        match = self._compiled_pattern.match(stripped_line)
        if match is None:
            failure = ParseFailure(raw_line=stripped_line, line_number=line_number, error_reason="Regex pattern match failed")
            self._statistics.failures.append(failure)
            self._statistics.failed_parses += 1
            return None
            
        try:
            entry = ParsedLogEntry(
                timestamp=match.group(1).strip(),
                instrument_id=match.group(2).strip().upper(),
                parameter_type=match.group(3).strip().upper(),
                value=float(match.group(4).strip()),
                status_code=match.group(5).strip().upper(),
                raw_line=stripped_line,
                line_number=line_number
            )
            self._statistics.successful_parses += 1
            return entry
        except Exception as exc:
            failure = ParseFailure(raw_line=stripped_line, line_number=line_number, error_reason=str(exc))
            self._statistics.failures.append(failure)
            self._statistics.failed_parses += 1
            return None

    def parse_file(self, file_path: Path) -> Generator[ParsedLogEntry, None, None]:
        self._statistics = ParseStatistics()
        if not file_path.exists():
            raise FileNotFoundError(f"Log file does not exist: {file_path}")
        with file_path.open(mode="r", encoding="utf-8") as file_handle:
            for line_number, line in enumerate(file_handle, start=1):
                self._statistics.total_lines += 1
                parsed_entry = self._parse_single_line(line, line_number)
                if parsed_entry is not None:
                    yield parsed_entry

    def parse_file_to_list(self, file_path: Path) -> list[ParsedLogEntry]:
        return list(self.parse_file(file_path))
        
    def get_statistics(self) -> ParseStatistics:
        return self._statistics

    def to_dict(self, entry: ParsedLogEntry) -> dict:
        return {
            "timestamp": entry.timestamp, "instrument_id": entry.instrument_id,
            "parameter_type": entry.parameter_type, "value": entry.value,
            "status_code": entry.status_code, "raw_line": entry.raw_line, "line_number": entry.line_number
        }