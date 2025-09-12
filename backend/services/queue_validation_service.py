
from enum import Enum
from typing import Dict, List, Optional, Tuple
from utils.schemas import QueueType
import logging

logger = logging.getLogger(__name__)

class ValidationResult:
    def __init__(self, allowed: bool, reason: str = "", requires_confirmation: bool = False, 
                 confirmation_message: str = "", is_redundant: bool = False):
        self.allowed = allowed
        self.reason = reason
        self.requires_confirmation = requires_confirmation
        self.confirmation_message = confirmation_message
        self.is_redundant = is_redundant

class QueueValidationService:
    """Context-aware queue movement validation - replaces broken dedup logic"""
    
    def __init__(self):
        # Define the 64 transition rules from our proposal
        self._always_allow = {
            # FROM REVIEW
            (QueueType.REVIEW, QueueType.ACTIVE),
            (QueueType.REVIEW, QueueType.REJECTED),
            (QueueType.REVIEW, QueueType.ON_HOLD),
            
            # FROM ACTIVE  
            (QueueType.ACTIVE, QueueType.PROCESSING),  # System only
            (QueueType.ACTIVE, QueueType.ON_HOLD),
            (QueueType.ACTIVE, QueueType.REJECTED),
            (QueueType.ACTIVE, QueueType.REVIEW),
            
            # FROM PROCESSING
            (QueueType.PROCESSING, QueueType.COMPLETED),  # System only
            (QueueType.PROCESSING, QueueType.FAILED),     # System only
            
            # FROM FAILED
            (QueueType.FAILED, QueueType.ACTIVE),
            (QueueType.FAILED, QueueType.REVIEW),
            (QueueType.FAILED, QueueType.REJECTED),
            (QueueType.FAILED, QueueType.ON_HOLD),
            
            # FROM REJECTED
            (QueueType.REJECTED, QueueType.REVIEW),
            (QueueType.REJECTED, QueueType.ON_HOLD),
            
            # FROM ON_HOLD
            (QueueType.ON_HOLD, QueueType.ACTIVE),
            (QueueType.ON_HOLD, QueueType.REVIEW),
            (QueueType.ON_HOLD, QueueType.REJECTED),
            
            # FROM COMPLETED
            (QueueType.COMPLETED, QueueType.REJECTED),
        }
        
        self._require_confirmation = {
            # Potentially risky moves
            (QueueType.ACTIVE, QueueType.COMPLETED): "Mark as completed without extraction?",
            (QueueType.PROCESSING, QueueType.ACTIVE): "Cancel active extraction?",
            (QueueType.COMPLETED, QueueType.ACTIVE): "Already completed. Re-extract?",
            (QueueType.COMPLETED, QueueType.ON_HOLD): "Move completed entity to hold?",
            (QueueType.COMPLETED, QueueType.REVIEW): "Review already completed entity?",
            (QueueType.REJECTED, QueueType.ACTIVE): "Previously rejected. Process anyway?",
            (QueueType.FAILED, QueueType.COMPLETED): "Extraction failed. Mark complete anyway?",
            (QueueType.ON_HOLD, QueueType.COMPLETED): "Mark as completed without processing?",
        }
        
        self._always_block = {
            # Impossible/illogical moves
            (QueueType.ACTIVE, QueueType.FAILED),
            (QueueType.ACTIVE, QueueType.PROCESSING),      # System managed only
            (QueueType.PROCESSING, QueueType.ON_HOLD),
            (QueueType.PROCESSING, QueueType.REJECTED),
            (QueueType.PROCESSING, QueueType.REVIEW),
            (QueueType.COMPLETED, QueueType.FAILED),
            (QueueType.COMPLETED, QueueType.PROCESSING),   # System managed only
            (QueueType.FAILED, QueueType.PROCESSING),      # System managed only
            (QueueType.REJECTED, QueueType.FAILED),
            (QueueType.REJECTED, QueueType.PROCESSING),    # System managed only
            (QueueType.ON_HOLD, QueueType.FAILED),
            (QueueType.ON_HOLD, QueueType.PROCESSING),     # System managed only
        }
    
    def validate_movement(self, from_queue: QueueType, to_queue: QueueType, 
                         context: str = "manual") -> ValidationResult:
        """
        Validate if a queue movement is allowed
        
        Args:
            from_queue: Source queue
            to_queue: Target queue  
            context: Operation context ("manual", "system", "approval", "discovery")
        """
        transition = (from_queue, to_queue)
        
        # Check for redundant move (same queue)
        if from_queue == to_queue:
            return ValidationResult(
                allowed=True,
                reason="Redundant move - already in target queue",
                is_redundant=True
            )
        
        # Check if always blocked
        if transition in self._always_block:
            return ValidationResult(
                allowed=False,
                reason=f"Invalid transition: {from_queue.value} → {to_queue.value}"
            )
        
        # Check if always allowed
        if transition in self._always_allow:
            return ValidationResult(
                allowed=True,
                reason=f"Valid transition: {from_queue.value} → {to_queue.value}"
            )
        
        # Check if requires confirmation
        if transition in self._require_confirmation:
            return ValidationResult(
                allowed=True,
                reason=f"Conditional transition: {from_queue.value} → {to_queue.value}",
                requires_confirmation=True,
                confirmation_message=self._require_confirmation[transition]
            )
        
        # Default block for undefined transitions
        return ValidationResult(
            allowed=False,
            reason=f"Undefined transition: {from_queue.value} → {to_queue.value}"
        )
    
    def is_system_only_transition(self, from_queue: QueueType, to_queue: QueueType) -> bool:
        """Check if transition should only be performed by system"""
        system_only = {
            (QueueType.ACTIVE, QueueType.PROCESSING),
            (QueueType.PROCESSING, QueueType.COMPLETED),
            (QueueType.PROCESSING, QueueType.FAILED),
        }
        return (from_queue, to_queue) in system_only