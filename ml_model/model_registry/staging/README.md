# Model Registry

Model weight files are not committed to this repository due to file size.

## Setup

1. Download `distilbert_v3_model.zip` from the team shared drive:
   **[PASTE YOUR SHARED DRIVE LINK HERE]**

2. Extract it into this directory (`ml_model/model_registry/staging/`)

3. Confirm this path exists after extraction:
   `ml_model/model_registry/staging/distilbert_v3_907k_cleaned_20260312_133755/`

## Running without the model

The backend will start in mock mode automatically if model files are missing.
All API endpoints will respond — predictions will be simulated.
You will see this line in the backend terminal:
`WARNING  Model load failed — ... Starting in mock mode.`
