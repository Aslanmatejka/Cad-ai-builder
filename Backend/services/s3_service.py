"""
Phase 4: AWS S3 Integration for Model Caching and Sharing
Stores generated CAD models in S3 with shareable URLs
"""

import boto3
from botocore.exceptions import ClientError
from typing import Dict, Optional
import os
from pathlib import Path
import uuid
from datetime import datetime, timedelta

class S3Service:
    """
    Manages CAD model uploads to S3 for caching and sharing
    """
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self.bucket_name = os.getenv('S3_BUCKET_NAME', 'cad-models-cache')
        self.cloudfront_domain = os.getenv('CLOUDFRONT_DOMAIN')  # Optional CDN
    
    async def upload_build(
        self,
        build_id: str,
        cad_dir: Path
    ) -> Dict[str, str]:
        """
        Upload STEP, STL, and parametric script to S3
        
        Args:
            build_id: Build identifier
            cad_dir: Directory containing exported files
            
        Returns:
            {
                "shareUrl": str,  # Public shareable link
                "s3Key": str,     # S3 object key prefix
                "expiresAt": str  # ISO timestamp
            }
        """
        
        s3_key_prefix = f"builds/{build_id}"
        files_to_upload = [
            (cad_dir / f"{build_id}.step", "step", "application/octet-stream"),
            (cad_dir / f"{build_id}.stl", "stl", "model/stl"),
            (cad_dir / f"{build_id}_parametric.py", "script", "text/x-python")
        ]
        
        uploaded_files = []
        
        for file_path, file_type, content_type in files_to_upload:
            if not file_path.exists():
                continue
                
            s3_key = f"{s3_key_prefix}/{file_type}/{file_path.name}"
            
            try:
                # Upload to S3 with metadata
                self.s3_client.upload_file(
                    str(file_path),
                    self.bucket_name,
                    s3_key,
                    ExtraArgs={
                        'ContentType': content_type,
                        'Metadata': {
                            'buildId': build_id,
                            'uploadDate': datetime.utcnow().isoformat()
                        }
                    }
                )
                
                uploaded_files.append({
                    "type": file_type,
                    "s3Key": s3_key,
                    "size": file_path.stat().st_size
                })
                
            except ClientError as e:
                raise RuntimeError(f"S3 upload failed for {file_type}: {str(e)}")
        
        # Generate presigned URL for sharing (7 days expiration)
        expires_in = 7 * 24 * 60 * 60  # 7 days in seconds
        
        # Use STL file for share URL (most common use case)
        stl_s3_key = f"{s3_key_prefix}/stl/{build_id}.stl"
        
        if self.cloudfront_domain:
            # Use CloudFront if configured
            share_url = f"https://{self.cloudfront_domain}/{stl_s3_key}"
        else:
            # Generate presigned URL
            share_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': stl_s3_key
                },
                ExpiresIn=expires_in
            )
        
        expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
        
        return {
            "shareUrl": share_url,
            "s3Key": s3_key_prefix,
            "uploadedFiles": uploaded_files,
            "expiresAt": expires_at
        }
    
    async def download_build(
        self,
        s3_key_prefix: str,
        download_dir: Path
    ) -> Dict[str, str]:
        """
        Download build files from S3
        
        Args:
            s3_key_prefix: S3 key prefix (e.g., "builds/{buildId}")
            download_dir: Local directory to save files
            
        Returns:
            {
                "buildId": str,
                "stepFile": str,
                "stlFile": str,
                "scriptFile": str
            }
        """
        
        # Extract build_id from prefix
        build_id = s3_key_prefix.split('/')[-1]
        
        files_to_download = [
            (f"{s3_key_prefix}/step/{build_id}.step", "step"),
            (f"{s3_key_prefix}/stl/{build_id}.stl", "stl"),
            (f"{s3_key_prefix}/script/{build_id}_parametric.py", "script")
        ]
        
        downloaded_files = {}
        
        for s3_key, file_type in files_to_download:
            local_path = download_dir / Path(s3_key).name
            
            try:
                self.s3_client.download_file(
                    self.bucket_name,
                    s3_key,
                    str(local_path)
                )
                downloaded_files[f"{file_type}File"] = f"/exports/cad/{local_path.name}"
                
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    # File not found - skip
                    continue
                raise RuntimeError(f"S3 download failed for {file_type}: {str(e)}")
        
        downloaded_files["buildId"] = build_id
        return downloaded_files
    
    async def check_build_exists(self, build_id: str) -> bool:
        """
        Check if build exists in S3 cache
        
        Args:
            build_id: Build identifier
            
        Returns:
            True if build exists in S3
        """
        s3_key = f"builds/{build_id}/stl/{build_id}.stl"
        
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        except ClientError:
            return False
    
    async def get_build_metadata(self, build_id: str) -> Optional[Dict]:
        """
        Get metadata for a cached build
        
        Args:
            build_id: Build identifier
            
        Returns:
            Metadata dict or None if not found
        """
        s3_key = f"builds/{build_id}/stl/{build_id}.stl"
        
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            return {
                "buildId": build_id,
                "size": response['ContentLength'],
                "lastModified": response['LastModified'].isoformat(),
                "metadata": response.get('Metadata', {})
            }
        except ClientError:
            return None

# Singleton instance
s3_service = S3Service()
