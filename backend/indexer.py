"""
File Indexer - Scans directories and builds document index
"""

from pathlib import Path
from typing import Dict, List
import json
import hashlib
from datetime import datetime
import logging

from document_parser import DocumentParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FileIndexer:
    """Indexes files and extracts their content"""

    def __init__(self, index_file: str = "file_index.json"):
        # Use user's AppData directory for writable storage
        import os
        if not os.path.isabs(index_file):
            app_data = os.path.expanduser("~/.foundit")
            os.makedirs(app_data, exist_ok=True)
            index_file = os.path.join(app_data, index_file)

        self.index_file = Path(index_file)
        self.parser = DocumentParser()
        self.documents = []
        self.file_hashes = {}  # Track file modifications

        # Load existing index if available
        self._load_index()

    def _load_index(self):
        """Load existing index from disk"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.documents = data.get('documents', [])
                    self.file_hashes = data.get('file_hashes', {})
                logger.info(f"Loaded {len(self.documents)} documents from index")
            except Exception as e:
                logger.error(f"Error loading index: {e}")
                self.documents = []
                self.file_hashes = {}

    def _save_index(self):
        """Save index to disk"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'documents': self.documents,
                    'file_hashes': self.file_hashes,
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
            logger.info(f"Saved {len(self.documents)} documents to index")
        except Exception as e:
            logger.error(f"Error saving index: {e}")

    def _get_file_hash(self, file_path: Path) -> str:
        """Get hash of file for change detection"""
        stat = file_path.stat()
        # Use modification time and size as a quick hash
        return hashlib.md5(
            f"{stat.st_mtime}_{stat.st_size}".encode()
        ).hexdigest()

    def _should_reindex(self, file_path: Path) -> bool:
        """Check if file needs to be reindexed"""
        file_str = str(file_path)
        current_hash = self._get_file_hash(file_path)

        if file_str not in self.file_hashes:
            return True

        return self.file_hashes[file_str] != current_hash

    def index_directory(
        self,
        directory: str,
        force_reindex: bool = False,
        progress_callback=None
    ) -> Dict:
        """
        Index all supported files in a directory
        Returns statistics about the indexing process

        progress_callback: Optional function(current, total, percentage) to report progress
        """
        dir_path = Path(directory)
        stats = {
            'files_indexed': 0,
            'total_files': 0,
            'skipped': 0,
            'errors': 0
        }

        logger.info(f"Indexing directory: {dir_path}")

        # Clear existing documents if force reindex
        if force_reindex:
            self.documents = []
            self.file_hashes = {}

        try:
            # First pass: count all files
            all_files = [f for f in dir_path.rglob('*') if f.is_file()]
            total_files = len(all_files)

            if progress_callback:
                progress_callback(0, total_files, 0)

            processed = 0

            # Second pass: process files
            for file_path in all_files:
                stats['total_files'] += 1
                processed += 1

                # Skip if file hasn't changed and not forcing reindex
                if not force_reindex and not self._should_reindex(file_path):
                    stats['skipped'] += 1
                    # Update progress even for skipped files
                    if progress_callback:
                        percentage = int((processed / total_files) * 100)
                        progress_callback(processed, total_files, percentage)
                    continue

                # Check if we can parse this file type
                if not self.parser.can_parse(file_path):
                    # Update progress for unsupported files
                    if progress_callback:
                        percentage = int((processed / total_files) * 100)
                        progress_callback(processed, total_files, percentage)
                    continue

                try:
                    # Extract content
                    content = self.parser.parse(file_path)

                    if content and content.strip():
                        # Remove old entry for this file if exists
                        self.documents = [
                            d for d in self.documents
                            if d['file_path'] != str(file_path)
                        ]

                        # Add new document
                        doc = {
                            'file_path': str(file_path),
                            'file_name': file_path.name,
                            'file_type': file_path.suffix.lower(),
                            'content': content,
                            'preview': self.parser.get_preview(content),
                            'indexed_at': datetime.now().isoformat()
                        }

                        self.documents.append(doc)
                        self.file_hashes[str(file_path)] = self._get_file_hash(file_path)
                        stats['files_indexed'] += 1

                        if stats['files_indexed'] % 10 == 0:
                            logger.info(f"Indexed {stats['files_indexed']} files...")

                        # Log PDF files specifically for debugging
                        if file_path.suffix.lower() == '.pdf':
                            logger.info(f"✓ Indexed PDF: {file_path.name} ({len(content)} chars)")
                    else:
                        # Log why file was skipped
                        if file_path.suffix.lower() == '.pdf':
                            logger.warning(f"✗ PDF has no extractable text (scanned image?): {file_path.name}")

                except Exception as e:
                    logger.error(f"Error indexing {file_path}: {e}")
                    if file_path.suffix.lower() == '.pdf':
                        logger.error(f"PDF parsing failed for: {file_path.name}")
                    stats['errors'] += 1

                # Update progress
                if progress_callback:
                    percentage = int((processed / total_files) * 100)
                    progress_callback(processed, total_files, percentage)

        except Exception as e:
            logger.error(f"Error scanning directory: {e}")

        # Save index to disk
        self._save_index()

        logger.info(f"Indexing complete: {stats}")
        return stats

    def get_documents(self) -> List[Dict]:
        """Get all indexed documents"""
        return self.documents

    def get_document_count(self) -> int:
        """Get number of indexed documents"""
        return len(self.documents)

    def clear(self):
        """Clear all indexed documents"""
        self.documents = []
        self.file_hashes = {}
        self._save_index()
        logger.info("Index cleared")
