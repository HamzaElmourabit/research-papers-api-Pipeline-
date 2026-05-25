"""
Data Quality Monitoring Module
Provides metrics tracking, validation, and alerting
"""

import logging
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class QualityLevel(Enum):
    """Data quality levels"""
    CRITICAL = "CRITICAL"  # < 80% valid
    WARNING = "WARNING"    # 80-95% valid
    GOOD = "GOOD"          # >= 95% valid


@dataclass
class DataQualityMetrics:
    """Tracks data quality metrics for a batch"""
    
    batch_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Counts
    total_records: int = 0
    valid_records: int = 0
    rejected_records: int = 0
    
    # Field-level issues
    null_fields: Dict[str, int] = field(default_factory=dict)
    invalid_fields: Dict[str, int] = field(default_factory=dict)
    
    # Duplicates
    duplicate_records: int = 0
    duplicate_ids: List[str] = field(default_factory=list)
    
    # Errors
    errors: Dict[str, str] = field(default_factory=dict)
    
    def get_validation_rate(self) -> float:
        """Get percentage of valid records"""
        if self.total_records == 0:
            return 0.0
        return (self.valid_records / self.total_records) * 100
    
    def get_quality_level(self) -> QualityLevel:
        """Determine data quality level"""
        rate = self.get_validation_rate()
        if rate < 80:
            return QualityLevel.CRITICAL
        elif rate < 95:
            return QualityLevel.WARNING
        else:
            return QualityLevel.GOOD
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dict for logging/storage"""
        metrics_dict = asdict(self)
        metrics_dict['timestamp'] = self.timestamp.isoformat()
        metrics_dict['validation_rate'] = self.get_validation_rate()
        metrics_dict['quality_level'] = self.get_quality_level().value
        return metrics_dict
    
    def log_summary(self):
        """Log a summary of metrics"""
        rate = self.get_validation_rate()
        quality = self.get_quality_level()
        
        logger.info(
            f"Data Quality Report - {self.batch_id}",
            extra={
                "batch_id": self.batch_id,
                "total": self.total_records,
                "valid": self.valid_records,
                "rejected": self.rejected_records,
                "validation_rate": f"{rate:.2f}%",
                "quality_level": quality.value,
                "duplicates": self.duplicate_records
            }
        )
        
        if self.null_fields:
            logger.warning(
                f"Null fields detected in batch {self.batch_id}",
                extra={"null_fields": self.null_fields}
            )
        
        if quality == QualityLevel.CRITICAL:
            logger.critical(
                f"Critical data quality issue in batch {self.batch_id}",
                extra={
                    "validation_rate": rate,
                    "threshold": 80
                }
            )
        elif quality == QualityLevel.WARNING:
            logger.warning(
                f"Data quality below target in batch {self.batch_id}",
                extra={
                    "validation_rate": rate,
                    "target": 95
                }
            )


class DataQualityValidator:
    """Validates and tracks data quality"""
    
    def __init__(self, batch_id: str):
        self.batch_id = batch_id
        self.metrics = DataQualityMetrics(batch_id=batch_id)
        self.validation_errors: List[Dict[str, Any]] = []
    
    def validate_record(self, record: Dict[str, Any], record_id: str) -> bool:
        """
        Validate a single record
        
        Returns:
            True if record is valid, False otherwise
        """
        self.metrics.total_records += 1
        
        try:
            # Check required fields
            required_fields = ['arxiv_id', 'title', 'abstract', 'authors']
            for field in required_fields:
                if field not in record or record[field] is None:
                    self.metrics.null_fields[field] = self.metrics.null_fields.get(field, 0) + 1
                    return self._record_validation_error(
                        record_id, f"Missing required field: {field}"
                    )
                
                if isinstance(record[field], str) and not record[field].strip():
                    self.metrics.null_fields[field] = self.metrics.null_fields.get(field, 0) + 1
                    return self._record_validation_error(
                        record_id, f"Empty field: {field}"
                    )
            
            # Check field types
            if not isinstance(record.get('authors'), list) or len(record['authors']) == 0:
                self.metrics.invalid_fields['authors'] = self.metrics.invalid_fields.get('authors', 0) + 1
                return self._record_validation_error(
                    record_id, "Authors must be non-empty list"
                )
            
            self.metrics.valid_records += 1
            return True
            
        except Exception as e:
            return self._record_validation_error(record_id, str(e))
    
    def check_duplicates(self, records: List[Dict[str, Any]], id_field: str = 'arxiv_id') -> int:
        """
        Check for duplicate records
        
        Returns:
            Count of duplicate records found
        """
        seen_ids = set()
        duplicates = 0
        
        for record in records:
            record_id = record.get(id_field)
            if record_id in seen_ids:
                duplicates += 1
                self.metrics.duplicate_records += 1
                self.metrics.duplicate_ids.append(record_id)
            else:
                seen_ids.add(record_id)
        
        if duplicates > 0:
            logger.warning(
                f"Duplicates detected in batch {self.batch_id}",
                extra={
                    "duplicate_count": duplicates,
                    "sample_ids": self.metrics.duplicate_ids[:5]
                }
            )
        
        return duplicates
    
    def _record_validation_error(self, record_id: str, error: str) -> bool:
        """Record a validation error and return False"""
        self.metrics.rejected_records += 1
        self.validation_errors.append({
            "record_id": record_id,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        self.metrics.errors[error] = self.metrics.errors.get(error, 0) + 1
        return False
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary"""
        return {
            "batch_id": self.batch_id,
            "metrics": self.metrics.to_dict(),
            "validation_errors": self.validation_errors[:10],  # First 10 errors
            "total_errors": len(self.validation_errors)
        }


class DataQualityAlert:
    """
    Raises alerts based on data quality thresholds
    """
    
    def __init__(
        self,
        critical_threshold: float = 80,
        warning_threshold: float = 95,
        duplicate_threshold: int = 5
    ):
        self.critical_threshold = critical_threshold
        self.warning_threshold = warning_threshold
        self.duplicate_threshold = duplicate_threshold
    
    def check_metrics(self, metrics: DataQualityMetrics) -> Optional[Dict[str, Any]]:
        """
        Check metrics against thresholds and return alert if needed
        
        Returns:
            Alert dict if threshold exceeded, None otherwise
        """
        rate = metrics.get_validation_rate()
        
        if rate < self.critical_threshold:
            alert = {
                "severity": "CRITICAL",
                "batch_id": metrics.batch_id,
                "alert_message": f"Validation rate {rate:.2f}% below critical threshold {self.critical_threshold}%",
                "validation_rate": rate,
                "timestamp": datetime.utcnow().isoformat()
            }
            logger.critical(alert["alert_message"], extra=alert)
            return alert
        
        elif rate < self.warning_threshold:
            alert = {
                "severity": "WARNING",
                "batch_id": metrics.batch_id,
                "alert_message": f"Validation rate {rate:.2f}% below warning threshold {self.warning_threshold}%",
                "validation_rate": rate,
                "timestamp": datetime.utcnow().isoformat()
            }
            logger.warning(alert["alert_message"], extra=alert)
            return alert
        
        if metrics.duplicate_records > self.duplicate_threshold:
            alert = {
                "severity": "WARNING",
                "batch_id": metrics.batch_id,
                "alert_message": f"Found {metrics.duplicate_records} duplicates (threshold: {self.duplicate_threshold})",
                "duplicate_count": metrics.duplicate_records,
                "timestamp": datetime.utcnow().isoformat()
            }
            logger.warning(alert["alert_message"], extra=alert)
            return alert
        
        return None
