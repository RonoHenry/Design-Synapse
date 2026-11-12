import re

# Read the file
with open(
    r"d:\Projects\DesignSynapse\apps\labor-service\src\services\booking_service.py",
    "r",
    encoding="utf-8",
) as f:
    content = f.read()

# Fix reschedule_booking
content = re.sub(
    r'        if "scheduled_start" in new_schedule:\s+booking\.scheduled_start = new_schedule\["scheduled_start"\]\s+if "scheduled_completion_date" in new_schedule:\s+booking\.scheduled_completion_date = new_schedule\[\s+"scheduled_completion_date"\s+\]\s+if "reason" in new_schedule:\s+booking\.notes = \(\s+f"\{booking\.notes or \'\'\}\\\\nRescheduled: \{new_schedule\[\'reason\'\]\}"\s+\)\s+updated_booking = await self\.booking_repository\.update\(booking\)',
    """        # Build update data dict
        update_data = {}
        if "scheduled_start" in new_schedule:
            update_data["scheduled_start_date"] = new_schedule["scheduled_start"]
        if "scheduled_completion_date" in new_schedule:
            update_data["scheduled_completion_date"] = new_schedule["scheduled_completion_date"]
        if "reason" in new_schedule:
            update_data["notes"] = f"{booking.notes or ''}\\nRescheduled: {new_schedule['reason']}"

        updated_booking = await self.booking_repository.update(booking_id, update_data)""",
    content,
    flags=re.DOTALL,
)

# Fix cancel_booking
content = re.sub(
    r"        # Calculate cancellation penalty if applicable\s+penalty = self\._calculate_cancellation_penalty\(booking\)\s+booking\.status = BookingStatus\.CANCELLED\s+booking\.cancellation_reason = reason\s+booking\.cancellation_penalty = penalty\s+updated_booking = await self\.booking_repository\.update\(booking\)",
    """        # Calculate cancellation penalty if applicable
        penalty = self._calculate_cancellation_penalty(booking)

        # Use update_booking_status for status change
        updated_booking = await self.booking_repository.update_booking_status(
            booking_id, BookingStatus.CANCELLED
        )

        # Update cancellation-specific fields
        await self.booking_repository.update(booking_id, {
            "cancellation_reason": reason,
            "cancellation_penalty": penalty
        })

        # Refresh to get updated booking
        updated_booking = await self.booking_repository.get_by_id(booking_id)""",
    content,
    flags=re.DOTALL,
)

# Write back
with open(
    r"d:\Projects\DesignSynapse\apps\labor-service\src\services\booking_service.py",
    "w",
    encoding="utf-8",
) as f:
    f.write(content)

print("Fixed reschedule and cancel methods")
