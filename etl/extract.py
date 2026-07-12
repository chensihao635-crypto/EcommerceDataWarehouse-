# ============================================================
# Data Extraction Module
# ============================================================

import os
import pandas as pd
from datetime import datetime
from pathlib import Path
from loguru import logger
import yaml


class DataExtractor:
    """Data extraction class - responsible for reading raw data from source files"""
    
    def __init__(self, config_path=None):
        """
        Initialize data extractor
        
        Args:
            config_path: Path to config file, defaults to config/config.yaml
        """
        # Get project root directory
        self.project_root = Path(__file__).parent.parent
        
        # Load config
        if config_path is None:
            config_path = self.project_root / "config" / "config.yaml"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # Setup logging
        log_file = self.project_root / self.config['etl']['log_file']
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.add(str(log_file), rotation="10 MB", level=self.config['etl']['log_level'])
        
        logger.info("Data extractor initialized")
    
    def _resolve_source_path(self):
        """Resolve the source data file path"""
        source_file = self.config['data']['source_file']
        # Try relative to project root first
        data_file = (self.project_root / source_file).resolve()
        if data_file.exists():
            return data_file
        # Try relative to parent of project root (for ../data paths)
        data_file = (self.project_root.parent / Path(source_file).name).resolve()
        if data_file.exists():
            return data_file
        # Try with just the filename in common locations
        for parent in [self.project_root.parent, Path(r'd:\Desktop\program\data\online+retail')]:
            candidate = parent / Path(source_file).name
            if candidate.exists():
                return candidate.resolve()
        return (self.project_root / source_file).resolve()
    
    def extract(self):
        """
        Extract data from Excel file
        
        Returns:
            pandas.DataFrame: Raw data
        """
        logger.info("=" * 60)
        logger.info("Starting data extraction task")
        logger.info("=" * 60)
        
        # Get data file path
        data_file = self._resolve_source_path()
        sheet_name = self.config['data']['sheet_name']
        
        # Check if file exists
        if not data_file.exists():
            logger.error(f"Data file not found: {data_file}")
            raise FileNotFoundError(f"Data file not found: {data_file}")
        
        logger.info(f"Data file path: {data_file}")
        logger.info(f"File size: {data_file.stat().st_size / 1024 / 1024:.2f} MB")
        
        # Read Excel file
        try:
            logger.info(f"Reading data file (Sheet: {sheet_name})...")
            start_time = datetime.now()
            
            df = pd.read_excel(
                data_file,
                sheet_name=sheet_name,
                engine='openpyxl'
            )
            
            elapsed_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Data read complete, elapsed: {elapsed_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to read data file: {e}")
            raise
        
        # Print dataset info
        self._print_dataset_info(df)
        
        return df
    
    def _print_dataset_info(self, df):
        """
        Print basic dataset information
        
        Args:
            df: DataFrame
        """
        logger.info("-" * 60)
        logger.info("Dataset basic info:")
        logger.info(f"Row count: {len(df):,}")
        logger.info(f"Column count: {len(df.columns)}")
        
        logger.info("Field list:")
        for i, col in enumerate(df.columns, 1):
            dtype = df[col].dtype
            non_null = df[col].notna().sum()
            null_count = df[col].isna().sum()
            null_pct = null_count / len(df) * 100
            logger.info(f"  {i}. {col}: {dtype} (non-null: {non_null:,}, null: {null_count:,}, null%: {null_pct:.2f}%)")
        
        logger.info("Data preview (first 5 rows):")
        logger.info(f"\n{df.head().to_string()}")
        
        logger.info("Data statistics:")
        logger.info(f"\n{df.describe().to_string()}")
        logger.info("-" * 60)
    
    def extract_ods(self):
        """
        Extract data and save to ODS layer (raw data layer)
        
        Returns:
            pandas.DataFrame: Raw data
        """
        logger.info("Executing ODS layer data extraction...")
        
        # Extract raw data
        df = self.extract()
        
        # Add extraction timestamp
        df['etl_timestamp'] = datetime.now()
        
        # Save to temporary CSV (for subsequent Load)
        output_dir = self.project_root / "data" / "ods"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / "ods_retail_raw.csv"
        df.to_csv(output_file, index=False, encoding='utf-8')
        logger.info(f"ODS layer raw data saved: {output_file}")
        logger.info(f"ODS layer row count: {len(df):,}")
        
        return df


if __name__ == "__main__":
    # Test data extraction
    extractor = DataExtractor()
    df = extractor.extract_ods()
    print(f"\nExtraction complete! Data shape: {df.shape}")