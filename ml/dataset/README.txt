SUGAR PLANT PREDICTIVE MAINTENANCE — REAL DATASET UPLOAD FOLDER
================================================================

Place your real equipment sensor CSV file in this folder before training.

REQUIRED CSV COLUMNS (exact column names):
-------------------------------------------
temperature         - Equipment temperature reading (°C)
temp_trend          - Change in temperature vs previous reading (+/- °C)
vibration           - Vibration level (mm/s)
vibration_trend     - Change in vibration vs previous reading (+/- mm/s)
pressure            - Steam or system pressure (bar)
pressure_trend      - Change in pressure vs previous reading (+/- bar)
motor_current       - Motor current draw (Amperes)
motor_speed         - Motor shaft speed (RPM)
conveyor_speed      - Conveyor belt speed (m/s) — use 0 if not applicable
operating_hours     - Cumulative equipment operating hours since last service
recent_alert_count  - Number of fault alerts in the past 7 days for this equipment
risk_label          - REQUIRED LABEL: must be 0 (Low), 1 (Medium), or 2 (High)

LABELLING GUIDE:
----------------
0 = Low Risk    — Equipment operating normally, all readings within normal range
1 = Medium Risk — Some readings trending abnormally, increased alert frequency
2 = High Risk   — Multiple readings out of range, imminent failure indicators

EXAMPLE ROW:
temperature,temp_trend,vibration,vibration_trend,pressure,pressure_trend,motor_current,motor_speed,conveyor_speed,operating_hours,recent_alert_count,risk_label
62.3,0.5,2.8,0.1,37.2,0.2,88.0,1478,1.8,1200,0,0

WHERE TO FIND REAL DATASETS:
------------------------------
1. UCI ML Repository — predictive maintenance datasets:
   https://archive.ics.uci.edu/ml/datasets.php?task=cla&area=&type=ts

2. Kaggle — search "predictive maintenance":
   https://www.kaggle.com/datasets?search=predictive+maintenance

3. Microsoft AI4I 2020 Predictive Maintenance Dataset (popular benchmark):
   https://archive.ics.uci.edu/ml/datasets/AI4I+2020+Predictive+Maintenance+Dataset

4. PRONOSTIA/FEMTO Bearing Dataset:
   https://www.femto-st.fr/en/Research-departments/AS2M/Research-groups/PHM/IEEE-PHM-2012-Data-challenge

NOTE: Real-world datasets will need column renaming to match the required names above.
Use the column_mapping feature in train_from_csv.py to map your column names.

