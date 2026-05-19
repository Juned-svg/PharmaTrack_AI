import logging
from typing import Optional, Any
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

@dataclass
class AnomalyDetectionResult:
    predictions: np.ndarray
    anomaly_scores: np.ndarray
    anomaly_indices: np.ndarray
    normal_indices: np.ndarray
    anomaly_count: int
    normal_count: int
    anomaly_ratio: float
    feature_statistics: dict[str, dict[str, float]] = field(default_factory=dict)

class AnomalyDetector:
    def __init__(self, contamination: float = 0.05, n_estimators: int = 100, random_state: int = 42) -> None:
        self._contamination = contamination
        self._n_estimators = n_estimators
        self._scaler = StandardScaler()
        self._model = IsolationForest(contamination=contamination, n_estimators=n_estimators, random_state=random_state, n_jobs=-1)
        self._dataframe = None
        self._is_fitted = False

    def load_records(self, records: list[dict[str, Any]]) -> pd.DataFrame:
        self._dataframe = pd.DataFrame(records)
        return self._dataframe

    def fit(self, records: Optional[list[dict[str, Any]]] = None) -> "AnomalyDetector":
        if records is not None: self.load_records(records)
        param_encoding = {"TEMP": 0, "PRESS": 1, "FLOW": 2}
        status_encoding = {"OK": 0, "WARN": 1, "CRITICAL": 2}
        
        df = self._dataframe.copy()
        df["param_encoded"] = df["parameter_type"].map(param_encoding)
        df["status_encoded"] = df["status_code"].map(status_encoding)
        
        features = df[["value", "param_encoded", "status_encoded"]].values
        scaled_features = self._scaler.fit_transform(features)
        self._model.fit(scaled_features)
        self._is_fitted = True
        return self

    def detect_anomalies(self) -> AnomalyDetectionResult:
        param_encoding = {"TEMP": 0, "PRESS": 1, "FLOW": 2}
        status_encoding = {"OK": 0, "WARN": 1, "CRITICAL": 2}
        df = self._dataframe.copy()
        df["param_encoded"] = df["parameter_type"].map(param_encoding)
        df["status_encoded"] = df["status_code"].map(status_encoding)
        
        features = df[["value", "param_encoded", "status_encoded"]].values
        scaled_features = self._scaler.transform(features)
        preds = self._model.predict(scaled_features)
        scores = self._model.decision_function(scaled_features)
        
        ano_idx = np.where(preds == -1)[0]
        norm_idx = np.where(preds == 1)[0]
        
        return AnomalyDetectionResult(
            predictions=preds, anomaly_scores=scores, anomaly_indices=ano_idx, normal_indices=norm_idx,
            anomaly_count=len(ano_idx), normal_count=len(norm_idx), anomaly_ratio=len(ano_idx)/len(preds)
        )

    def add_predictions_to_dataframe(self, result: AnomalyDetectionResult) -> pd.DataFrame:
        out = self._dataframe.copy()
        out["anomaly_flag"] = result.predictions
        out["anomaly_score"] = result.anomaly_scores
        out["is_anomaly"] = result.predictions == -1
        return out

    def generate_report(self, result: AnomalyDetectionResult) -> str:
        return f"Total Records Processed: {result.anomaly_count + result.normal_count}\nAnomalies Detected: {result.anomaly_count}\nAnomaly Ratio: {result.anomaly_ratio:.2%}"