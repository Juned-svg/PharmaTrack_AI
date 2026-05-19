import random
import logging
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")

INSTRUMENTS = ["INST-A01", "INST-B02", "INST-C03", "INST-D04"]
BOUNDS = {"TEMP": (15.0, 85.0), "PRESS": (0.5, 5.0), "FLOW": (0.1, 2.5)}

def generate_logs(output_path: Path, lines: int = 2000):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base_time = datetime.now()
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# PharmaTrack AI - Test Logs\n")
        for i in range(1, lines + 1):
            ts = (base_time + timedelta(seconds=i*30)).strftime("%Y-%m-%d %H:%M:%S")
            inst = random.choice(INSTRUMENTS)
            param = random.choice(list(BOUNDS.keys()))
            prob = random.random()
            
            if prob < 0.75: # Nominal
                val = round(random.uniform(BOUNDS[param][0], BOUNDS[param][1]), 2)
                line = f"{ts} | {inst} | {param} | {val} | OK\n"
            elif prob < 0.85: # Malformed Parse Failures
                line = f"{ts} Critical Failure on {inst} without pipe splitting\n"
            elif prob < 0.95: # Validation Bounds Breach
                val = round(BOUNDS[param][1] + random.uniform(10, 100), 2)
                line = f"{ts} | {inst} | {param} | {val} | CRITICAL\n"
            else: # Structural Outliers
                val = round(BOUNDS[param][0] + 0.1, 2)
                line = f"{ts} | {inst} | {param} | {val} | CRITICAL\n"
            f.write(line)
            
if __name__ == "__main__":
    generate_logs(Path("data/raw/instrument_logs.txt"))