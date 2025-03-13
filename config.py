"""
Configuration module for loading and managing environment variables.
"""
import os
from typing import Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class to manage environment variables."""
    
    def __init__(self):
        # Game timing settings
        self.MAX_QUEUE_TIME: int = int(os.getenv('MAX_QUEUE_TIME', '30'))
        self.MAX_WAIT_TIME: int = int(os.getenv('MAX_WAIT_TIME', '15'))
        
        # Account settings
        self.ACCOUNT: str = os.getenv('MAJSOUL_ACCOUNT', '')
        if not self.ACCOUNT:
            raise ValueError('MAJSOUL_ACCOUNT must be set in environment variables')
            
        self.PASSWORD: str = os.getenv('MAJSOUL_PASSWORD', '')
        if not self.PASSWORD:
            raise ValueError('MAJSOUL_PASSWORD must be set in environment variables')
        
        # Game settings
        self.MATCH_RANK: str = os.getenv('MATCH_RANK', 'bronze').lower()
        self.AUTO_CONTINUE: bool = os.getenv('AUTO_CONTINUE', 'true').lower() == 'true'
        
        # Validate match rank
        valid_ranks = ['bronze', 'silver', 'gold']
        if self.MATCH_RANK not in valid_ranks:
            raise ValueError(f'MATCH_RANK must be one of: {", ".join(valid_ranks)}')

# Create a global config instance
config = Config()
