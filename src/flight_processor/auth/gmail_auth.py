"""Gmail API authentication"""
import os
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


class GmailAuthenticator:
    """Handles Gmail API authentication"""
    
    def __init__(self, scopes, credentials_file, token_file):
        """
        Initialize authenticator
        
        Args:
            scopes: List of OAuth2 scopes
            credentials_file: Path to credentials.json
            token_file: Path to token.json
        """
        self.scopes = scopes
        self.credentials_file = str(credentials_file)
        self.token_file = str(token_file)
        self.creds = None
        self.service = None
    
    def authenticate(self):
        """
        Authenticate with Gmail API
        
        Returns:
            Gmail API service object
        """
        # Check if token.json exists
        if os.path.exists(self.token_file):
            logger.info(f"Loading credentials from {self.token_file}")
            self.creds = Credentials.from_authorized_user_file(self.token_file, self.scopes)
        
        # Refresh or create new credentials if needed
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                logger.info("Refreshing expired credentials")
                self.creds.refresh(Request())
            else:
                logger.info("Starting OAuth2 flow for new credentials")
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_file}\n"
                        "Please download credentials.json from Google Cloud Console"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.scopes
                )
                self.creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            logger.info(f"Saving credentials to {self.token_file}")
            with open(self.token_file, 'w') as token:
                token.write(self.creds.to_json())
        
        # Build Gmail service
        logger.info("Building Gmail API service")
        self.service = build('gmail', 'v1', credentials=self.creds)
        return self.service
    
    def get_service(self):
        """
        Get authenticated Gmail service
        
        Returns:
            Gmail API service object or None if not authenticated
        """
        return self.service
