from celery import Celery
import pandas as pd
import json
import os
from datetime import datetime

# Initialize Celery
celery_app = Celery(__name__)
celery_app.conf.broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
celery_app.conf.result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

@celery_app.task(bind=True)
def process_csv_etl(self, filepath, job_id):
    """
    ETL Pipeline:
    1. Extract: Read CSV file
    2. Transform: Clean and process data
    3. Load: Save results
    """
    try:
        # EXTRACT
        print(f"[{job_id}] Extracting data from {filepath}")
        df = pd.read_csv(filepath)
        original_rows = len(df)

        # TRANSFORM
        print(f"[{job_id}] Starting transformations")

        # Clean: Remove duplicates
        df = df.drop_duplicates()
        deduplicated_rows = len(df)

        # Clean: Remove rows with all NaN values
        df = df.dropna(how='all')

        # Handle missing values - fill with mean for numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        for col in numeric_cols:
            if df[col].isnull().sum() > 0:
                df[col].fillna(df[col].mean(), inplace=True)

        # Fill categorical NaNs with 'Unknown'
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            df[col].fillna('Unknown', inplace=True)

        # Calculate statistics for numeric columns
        statistics = {}
        for col in numeric_cols:
            statistics[col] = {
                'mean': float(df[col].mean()),
                'median': float(df[col].median()),
                'std': float(df[col].std()),
                'min': float(df[col].min()),
                'max': float(df[col].max()),
            }

        # Add a processed flag column (example transformation)
        df['processed_at'] = datetime.now().isoformat()

        # Normalize numeric columns (scale to 0-1)
        for col in numeric_cols:
            min_val = df[col].min()
            max_val = df[col].max()
            if max_val > min_val:
                df[f'{col}_normalized'] = (df[col] - min_val) / (max_val - min_val)

        # LOAD
        print(f"[{job_id}] Loading results")
        output_csv = os.path.join('results', f"{job_id}_output.csv")
        df.to_csv(output_csv, index=False)

        # Save metadata
        result_metadata = {
            'job_id': job_id,
            'original_rows': original_rows,
            'processed_rows': len(df),
            'duplicate_rows_removed': original_rows - deduplicated_rows,
            'columns': df.columns.tolist(),
            'statistics': statistics,
            'output_file': output_csv,
            'processed_at': datetime.now().isoformat(),
        }

        result_file = os.path.join('results', f"{job_id}_result.json")
        with open(result_file, 'w') as f:
            json.dump(result_metadata, f, indent=2)

        # Clean up uploaded file
        if os.path.exists(filepath):
            os.remove(filepath)

        print(f"[{job_id}] ETL pipeline completed successfully")
        return result_metadata

    except Exception as e:
        print(f"[{job_id}] Error in ETL pipeline: {str(e)}")
        error_data = {
            'job_id': job_id,
            'error': str(e),
            'error_type': type(e).__name__,
            'timestamp': datetime.now().isoformat(),
        }

        error_file = os.path.join('results', f"{job_id}_error.json")
        with open(error_file, 'w') as f:
            json.dump(error_data, f, indent=2)

        # Clean up uploaded file
        if os.path.exists(filepath):
            os.remove(filepath)

        raise
