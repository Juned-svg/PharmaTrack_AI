import sys
import json
import logging
from pathlib import Path
from src.parser import LogParser
from src.validator import LogValidator
from src.anomaly_detector import AnomalyDetector

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
    logger = logging.getLogger("PharmaTrackPipeline")
    
    input_file = Path("data/raw/instrument_logs.txt")
    val_dir = Path("data/validated")
    quar_dir = Path("data/quarantine_logs")
    
    if not input_file.exists():
        logger.error("Input logs missing. Please run generate_mock_data.py first.")
        sys.exit(1)
        
    logger.info("Starting Stage 1: Parsing Data Logs...")
    parser = LogParser()
    parsed_entries = parser.parse_file_to_list(input_file)
    
    logger.info("Starting Stage 2: Structural Verification & Constraints Enforcement...")
    validator = LogValidator(quarantine_dir=quar_dir)
    parsed_dicts = [parser.to_dict(e) for e in parsed_entries]
    validated_records = validator.validate_batch(parsed_dicts)
    
    if not validated_records:
        logger.error("Zero records passed schema bounds. Terminating flow.")
        sys.exit(1)
        
    logger.info("Starting Stage 3: Outlier Machine Learning Detection...")
    detector = AnomalyDetector(contamination=0.05)
    clean_dicts = [r.to_dict() for r in validated_records]
    detector.fit(clean_dicts)
    results = detector.detect_anomalies()
    
    out_df = detector.add_predictions_to_dataframe(results)
    out_df.to_csv(val_dir / "anomaly_results.csv", index=False)
    
    report = detector.generate_report(results)
    print("\n" + "="*40 + "\n" + report + "\n" + "="*40)
    
if __name__ == "__main__":
    main()