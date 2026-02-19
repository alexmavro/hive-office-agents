"""Hive audit layer — structured JSONL system-event logging.

See hive/audit/logger.py for the full AuditLogger API.
See hive/audit/retention.py for log rotation and size checking.
See hive/audit/reporter.py for daily MD report generation (SA.3).

IMPORTANT: This module logs system events only — not personal data.
Future reworks required before any public deployment are documented in STATUS.md.
"""

from hive.audit.logger import AuditLogger

__all__ = ["AuditLogger"]
