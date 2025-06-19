"""
Student management module for Qube Monitor application.
Handles student data, status tracking, and validation.
"""

import time
from typing import Dict, Set, Optional, List, Tuple
from support.config import *


class StudentManager:
    """Manages student data and status tracking."""
    
    def __init__(self):
        """Initialize StudentManager."""
        self.allowed_students: Set[int] = set()
        self.student_names: Dict[int, str] = {}
        self.student_statuses: Dict[int, Dict] = {}
        
    def update_allowed_students(self, student_text: str) -> None:
        """
        Update the list of allowed students from input text.
        
        Args:
            student_text: Text containing student numbers and names
                         Format: "123456:Student Name" or just "123456"
        """
        try:
            if not student_text.strip():
                self.allowed_students = set()
                self.student_names = {}
                return
            
            new_students = set()
            new_names = {}
            
            for line in student_text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                if ':' in line:
                    # Format: 123456:Student Name
                    try:
                        num_str, name = line.split(':', 1)
                        num = int(num_str.strip())
                        name = name.strip()
                        
                        if MIN_STUDENT_NUMBER <= num <= MAX_STUDENT_NUMBER:
                            new_students.add(num)
                            new_names[num] = name
                        else:
                            print(f"Invalid student number (not 6 digits): {num}")
                    except ValueError:
                        print(f"Invalid student input format: {line}")
                else:
                    # Just a number without name
                    try:
                        num = int(line)
                        if MIN_STUDENT_NUMBER <= num <= MAX_STUDENT_NUMBER:
                            new_students.add(num)
                            new_names[num] = f"Student {num}"
                        else:
                            print(f"Invalid student number (not 6 digits): {num}")
                    except ValueError:
                        print(f"Invalid student number format: {line}")
            
            # Update allowed students and names
            self.allowed_students = new_students
            self.student_names = new_names
            
            # Remove statuses for students no longer in the list
            students_to_remove = [
                student_num for student_num in self.student_statuses 
                if student_num not in self.allowed_students
            ]
            
            for student_num in students_to_remove:
                del self.student_statuses[student_num]
            
            print(f"Updated allowed students: {sorted(self.allowed_students)}")
            print(f"Student names: {self.student_names}")
            
        except Exception as e:
            print(f"Error updating allowed students: {e}")
            raise
    
    def is_student_allowed(self, student_number: int) -> bool:
        """
        Check if a student number is in the allowed list.
        
        Args:
            student_number: Student number to check
            
        Returns:
            bool: True if student is allowed, False otherwise
        """
        return student_number in self.allowed_students
    
    def get_student_name(self, student_number: int) -> str:
        """
        Get the name of a student.
        
        Args:
            student_number: Student number
            
        Returns:
            str: Student name or default format
        """
        return self.student_names.get(student_number, f"Student {student_number}")
    
    def update_student_status(self, student_number: int, status_code: str) -> Optional[Dict]:
        """
        Update the status of a student.
        
        Args:
            student_number: Student number
            status_code: Status code ('G', 'V', 'R')
            
        Returns:
            Dict or None: Updated status info or None if update was ignored
        """
        try:
            # Check if student is allowed
            if not self.is_student_allowed(student_number):
                print(f"Student {student_number} not in allowed list, ignored")
                return None
            
            # Validate status code
            if status_code not in STATUS_MAP:
                print(f"Unknown status code: {status_code}")
                return None
            
            current_time = time.time()
            current_time_str = time.strftime("%H:%M:%S")
            
            # Check if status has actually changed
            status_changed = True
            status_start_time = current_time
            
            if student_number in self.student_statuses:
                prev_status = self.student_statuses[student_number]
                if prev_status.get('code') == status_code:
                    # Status is the same
                    status_changed = False
                    status_start_time = prev_status.get('status_start_time', current_time)
                    
                    # Check for duplicate messages within threshold
                    if current_time - prev_status.get('last_update', 0) < DUPLICATE_MESSAGE_THRESHOLD:
                        print(f"Duplicate message for student {student_number}, ignored")
                        return None
                    
                    # Status is the same but outside threshold - update timestamp but don't log as change
                    print(f"Status repeat for student {student_number}, updating timestamp only")
            
            # If status hasn't changed, return special indicator
            if not status_changed:
                # Update timestamp but return None to indicate no real change
                self.student_statuses[student_number]['last_update'] = current_time
                return None
            
            # Get status display info
            status_text, color = STATUS_MAP[status_code]
            
            # Update student status
            status_info = {
                'status': status_text,
                'color': color,
                'time': current_time_str,
                'code': status_code,
                'last_update': current_time,
                'status_start_time': status_start_time
            }
            
            self.student_statuses[student_number] = status_info
            
            print(f"Updated status for {student_number}: {status_text}")
            return status_info
            
        except Exception as e:
            print(f"Error updating student status: {e}")
            return None
    
    def resolve_student_issue(self, student_number: int) -> bool:
        """
        Mark a student's issue as resolved.
        
        Args:
            student_number: Student number
            
        Returns:
            bool: True if resolved successfully, False otherwise
        """
        try:
            if student_number in self.student_statuses:
                self.student_statuses[student_number].update({
                    'status': 'Opgelost',
                    'color': 'blue',
                    'code': 'G',
                    'last_update': time.time()
                })
                print(f"Resolved issue for student {student_number}")
                return True
            return False
        except Exception as e:
            print(f"Error resolving student issue: {e}")
            return False
    
    def get_all_statuses(self) -> Dict[int, Dict]:
        """
        Get all current student statuses.
        
        Returns:
            Dict: All student statuses
        """
        return self.student_statuses.copy()
    
    def get_sorted_students(self) -> List[Tuple[int, Dict]]:
        """
        Get students sorted by priority (help needed first, then questions, then others).
        
        Returns:
            List of (student_number, status_info) tuples sorted by priority
        """
        def sort_priority(item):
            student_number, info = item
            status_code = info.get('code', 'G')
            status_start_time = info.get('status_start_time', time.time())
            
            if status_code == 'R':  # Help needed - highest priority
                return (0, -status_start_time)  # Negative for longest time first
            elif status_code == 'V':  # Question - second priority
                return (1, -status_start_time)  # Negative for longest time first
            else:  # Other statuses - lowest priority
                return (2, student_number)  # Sort by student number
        
        return sorted(self.student_statuses.items(), key=sort_priority)
    
    def get_students_with_active_status(self) -> List[int]:
        """
        Get list of students with active status (V or R).
        
        Returns:
            List of student numbers with active status
        """
        return [
            student_num for student_num, info in self.student_statuses.items()
            if info.get('code') in ['V', 'R']
        ]
    
    def calculate_status_duration(self, student_number: int) -> Optional[Tuple[str, str]]:
        """
        Calculate how long a student has been in their current status.
        
        Args:
            student_number: Student number
            
        Returns:
            Tuple of (duration_text, color) or None if not applicable
        """
        if student_number not in self.student_statuses:
            return None
            
        info = self.student_statuses[student_number]
        status_code = info.get('code')
        
        # Only calculate duration for V and R statuses
        if status_code not in ['V', 'R']:
            return None
        
        current_time = time.time()
        status_start_time = info.get('status_start_time', current_time)
        duration_seconds = int(current_time - status_start_time)
        
        # Format duration text
        if duration_seconds < 60:
            duration_text = f"{duration_seconds}s"
        elif duration_seconds < 3600:
            minutes = duration_seconds // 60
            seconds = duration_seconds % 60
            duration_text = f"{minutes}m {seconds}s"
        else:
            hours = duration_seconds // 3600
            minutes = (duration_seconds % 3600) // 60
            duration_text = f"{hours}h {minutes}m"
        
        # Determine color based on duration
        if duration_seconds > DURATION_CRITICAL_THRESHOLD:
            color = "red"
        elif duration_seconds > DURATION_WARNING_THRESHOLD:
            color = "orange"
        else:
            color = "black"
        
        return duration_text, color
    
    def clear_all_statuses(self) -> None:
        """Clear all student statuses."""
        self.student_statuses.clear()
        print("Cleared all student statuses")
    
    def get_student_count(self) -> Tuple[int, int]:
        """
        Get count of allowed students and students with current status.
        
        Returns:
            Tuple of (allowed_count, active_count)
        """
        return len(self.allowed_students), len(self.student_statuses)
