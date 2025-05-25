# domain/value_objects/tests/test_employee_availability.py
import unittest
from datetime import date
from domain.value_objects.employee_availability import EmployeeAvailability, AvailabilityStatus


class TestEmployeeAvailability(unittest.TestCase):
    def test_create_employee_availability(self):
        """Test creating an EmployeeAvailability value object."""
        today = date.today()
        availability = EmployeeAvailability(
            employee_id=1,
            date=today,
            period=2,
            status=AvailabilityStatus.AVAILABLE
        )
        
        self.assertEqual(availability.employee_id, 1)
        self.assertEqual(availability.date, today)
        self.assertEqual(availability.period, 2)
        self.assertEqual(availability.status, AvailabilityStatus.AVAILABLE)
    
    def test_create_employee_availability_with_defaults(self):
        """Test creating an EmployeeAvailability with default values."""
        today = date.today()
        availability = EmployeeAvailability(
            employee_id=1,
            date=today
        )
        
        self.assertEqual(availability.employee_id, 1)
        self.assertEqual(availability.date, today)
        self.assertIsNone(availability.period)
        self.assertEqual(availability.status, AvailabilityStatus.AVAILABLE)
    
    def test_create_employee_availability_with_full_day_status(self):
        """Test creating an EmployeeAvailability with a full-day status."""
        today = date.today()
        availability = EmployeeAvailability(
            employee_id=1,
            date=today,
            status=AvailabilityStatus.CALL_IN
        )
        
        self.assertEqual(availability.employee_id, 1)
        self.assertEqual(availability.date, today)
        self.assertIsNone(availability.period)
        self.assertEqual(availability.status, AvailabilityStatus.CALL_IN)
    
    def test_employee_availability_immutability(self):
        """Test that EmployeeAvailability is immutable."""
        today = date.today()
        availability = EmployeeAvailability(
            employee_id=1,
            date=today,
            period=2,
            status=AvailabilityStatus.AVAILABLE
        )
        
        with self.assertRaises(Exception):
            availability.employee_id = 2
        
        with self.assertRaises(Exception):
            availability.date = date(2023, 1, 1)
        
        with self.assertRaises(Exception):
            availability.period = 3
        
        with self.assertRaises(Exception):
            availability.status = AvailabilityStatus.CALL_IN
    
    def test_employee_availability_equality(self):
        """Test that EmployeeAvailability objects are equal if their attributes are equal."""
        today = date.today()
        availability1 = EmployeeAvailability(
            employee_id=1,
            date=today,
            period=2,
            status=AvailabilityStatus.AVAILABLE
        )
        
        availability2 = EmployeeAvailability(
            employee_id=1,
            date=today,
            period=2,
            status=AvailabilityStatus.AVAILABLE
        )
        
        availability3 = EmployeeAvailability(
            employee_id=2,
            date=today,
            period=2,
            status=AvailabilityStatus.AVAILABLE
        )
        
        self.assertEqual(availability1, availability2)
        self.assertNotEqual(availability1, availability3)
    
    def test_employee_availability_validation(self):
        """Test that EmployeeAvailability validates its attributes."""
        today = date.today()
        
        # Test invalid employee_id
        with self.assertRaises(ValueError):
            EmployeeAvailability(
                employee_id=-1,
                date=today
            )
        
        # Test invalid date
        with self.assertRaises(ValueError):
            EmployeeAvailability(
                employee_id=1,
                date="today"
            )
        
        # Test invalid period
        with self.assertRaises(ValueError):
            EmployeeAvailability(
                employee_id=1,
                date=today,
                period=0
            )
        
        with self.assertRaises(ValueError):
            EmployeeAvailability(
                employee_id=1,
                date=today,
                period=6
            )
        
        # Test invalid status
        with self.assertRaises(ValueError):
            EmployeeAvailability(
                employee_id=1,
                date=today,
                status="available"
            )


if __name__ == "__main__":
    unittest.main()