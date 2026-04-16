#!/usr/bin/env python3
"""Phase 4: Review Workflow Management - API Handlers for Manual Review Process"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class ReviewDecision:
    """Represents a reviewer's decision on a normalized entry."""
    entry_id: str
    reviewer_name: str
    timestamp: str
    decision: str  # 'approved', 'rejected', 'modified'
    modified_payload: Optional[Dict] = None
    notes: str = ''
    confidence_override: Optional[float] = None


class ReviewWorkflow:
    """Manages the reviewer workflow for healthcare EMR entries."""
    
    def __init__(self, store_path: str = './review_store'):
        self.store_path = store_path
        os.makedirs(store_path, exist_ok=True)
        self.decisions_file = os.path.join(store_path, 'review_decisions.json')
        self.decisions = self._load_decisions()
    
    def _load_decisions(self) -> Dict:
        """Load existing review decisions from file."""
        if os.path.exists(self.decisions_file):
            try:
                with open(self.decisions_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading review decisions: {e}")
                return {}
        return {}
    
    def _save_decisions(self):
        """Persist review decisions to file."""
        try:
            with open(self.decisions_file, 'w') as f:
                json.dump(self.decisions, f, indent=2)
        except Exception as e:
            print(f"Error saving review decisions: {e}")
    
    def list_flagged_entries(self, entries: List[Dict], review_threshold: int = 70) -> List[Dict]:
        """
        Return entries that need review (confidence < threshold or no normalization).
        
        Args:
            entries: List of parsed log entries
            review_threshold: Confidence threshold below which entries are flagged (0-100)
        
        Returns:
            List of entries needing review with enriched context
        """
        flagged = []
        for entry in entries:
            confidence = entry.get('normalization_confidence', 0)
            review_needed = entry.get('review_needed', False)
            
            # Flag if: confidence low, no normalization, or explicitly marked
            if confidence < review_threshold or review_needed or not entry.get('normalized_payload'):
                # Add context for reviewer
                entry_copy = entry.copy()
                entry_copy['review_context'] = {
                    'raw_message': entry.get('message', ''),
                    'parsed_fields': entry.get('fields', {}),
                    'extracted_payload': entry.get('normalized_payload', {}),
                    'confidence_breakdown': entry.get('confidence_components', {}),
                    'previous_decisions': self.decisions.get(entry.get('entry_id'), []),
                }
                flagged.append(entry_copy)
        
        return flagged
    
    def record_decision(self, entry_id: str, reviewer_name: str, decision: str,
                       modified_payload: Optional[Dict] = None, notes: str = '') -> ReviewDecision:
        """
        Record a reviewer's decision on an entry.
        
        Args:
            entry_id: Unique identifier for the entry
            reviewer_name: Name of the reviewer
            decision: 'approved', 'rejected', or 'modified'
            modified_payload: If decision == 'modified', the new normalized payload
            notes: Optional notes from reviewer
        
        Returns:
            ReviewDecision object
        """
        rev_decision = ReviewDecision(
            entry_id=entry_id,
            reviewer_name=reviewer_name,
            timestamp=datetime.now().isoformat(),
            decision=decision,
            modified_payload=modified_payload,
            notes=notes,
        )
        
        if entry_id not in self.decisions:
            self.decisions[entry_id] = []
        
        self.decisions[entry_id].append(asdict(rev_decision))
        self._save_decisions()
        
        return rev_decision
    
    def get_entry_decision_history(self, entry_id: str) -> List[Dict]:
        """Get all review decisions for an entry."""
        return self.decisions.get(entry_id, [])
    
    def get_final_payload(self, entry: Dict) -> Dict:
        """
        Get the final normalized payload for an entry,
        considering reviewer modifications if approved.
        
        Args:
            entry: The log entry
        
        Returns:
            The approved/modified normalized payload
        """
        entry_id = entry.get('entry_id')
        decisions = self.decisions.get(entry_id, [])
        
        if decisions:
            # Get most recent decision
            latest = decisions[-1]
            if latest['decision'] == 'modified' and latest.get('modified_payload'):
                return latest['modified_payload']  # Modified decisions include approval
            elif latest['decision'] == 'approved':
                if latest.get('modified_payload'):
                    return latest['modified_payload']
                else:
                    return entry.get('normalized_payload', {})
            elif latest['decision'] == 'rejected':
                return {}  # No approved payload
        
        return entry.get('normalized_payload', {})
    
    def get_review_statistics(self, entries: List[Dict]) -> Dict:
        """
        Get statistics on review status and completeness.
        
        Returns:
            Dict with counts and percentages
        """
        total = len(entries)
        reviewed = len([e for e in entries if self.get_entry_decision_history(e.get('entry_id'))])
        approved = len([
            e for e in entries
            if self.get_entry_decision_history(e.get('entry_id')) and
               self.get_entry_decision_history(e.get('entry_id'))[-1]['decision'] == 'approved'
        ])
        
        return {
            'total_entries': total,
            'reviewed': reviewed,
            'pending_review': total - reviewed,
            'approved': approved,
            'rejection_rate': (1 - (approved / reviewed)) * 100 if reviewed > 0 else 0,
            'completion_rate': (reviewed / total) * 100,
        }


# REST API Helper Functions (for Flask integration)
def export_reviewed_entries(entries: List[Dict], review_workflow: ReviewWorkflow) -> Dict:
    """
    Export entries with final payloads after review process.
    Includes audit trail for compliance.
    """
    exported = []
    for entry in entries:
        final_entry = entry.copy()
        final_entry['normalized_payload'] = review_workflow.get_final_payload(entry)
        final_entry['review_history'] = review_workflow.get_entry_decision_history(entry.get('entry_id'))
        exported.append(final_entry)
    
    return {
        'status': 'success',
        'entries': exported,
        'statistics': review_workflow.get_review_statistics(entries),
        'export_timestamp': datetime.now().isoformat(),
    }


def get_review_summary(entries: List[Dict], review_workflow: ReviewWorkflow) -> Dict:
    """
    Get a summary of entries pending review and their confidence scores.
    """
    flagged = review_workflow.list_flagged_entries(entries)
    
    summary = {
        'total_entries': len(entries),
        'flagged_for_review': len(flagged),
        'by_confidence_range': {
            'critical_0-50': len([e for e in entries if e.get('normalization_confidence', 0) < 50]),
            'low_50-70': len([e for e in entries if 50 <= e.get('normalization_confidence', 0) < 70]),
            'medium_70-85': len([e for e in entries if 70 <= e.get('normalization_confidence', 0) < 85]),
            'high_85-100': len([e for e in entries if e.get('normalization_confidence', 0) >= 85]),
        },
        'by_event_type': {},
    }
    
    # Group by event type
    for entry in entries:
        event_type = entry.get('event_type', 'unknown')
        if event_type not in summary['by_event_type']:
            summary['by_event_type'][event_type] = {
                'total': 0,
                'flagged': 0,
                'avg_confidence': 0,
            }
        
        summary['by_event_type'][event_type]['total'] += 1
        if entry in flagged:
            summary['by_event_type'][event_type]['flagged'] += 1
    
    return summary
