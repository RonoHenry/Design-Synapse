# Read the file
with open(
    r"d:\Projects\DesignSynapse\apps\labor-service\src\services\booking_service.py",
    "r",
    encoding="utf-8",
) as f:
    lines = f.readlines()

# Fix reschedule_booking (lines 312-323)
new_reschedule = """        # Build update data dict
        update_data = {}
        if "scheduled_start" in new_schedule:
            update_data["scheduled_start_date"] = new_schedule["scheduled_start"]
        if "scheduled_completion_date" in new_schedule:
            update_data["scheduled_completion_date"] = new_schedule["scheduled_completion_date"]
        if "reason" in new_schedule:
            update_data["notes"] = f"{booking.notes or ''}\\nRescheduled: {new_schedule['reason']}"

        updated_booking = await self.booking_repository.update(booking_id, update_data)
"""

lines[311:323] = [new_reschedule + "\n"]

# Write back
with open(
    r"d:\Projects\DesignSynapse\apps\labor-service\src\services\booking_service.py",
    "w",
    encoding="utf-8",
) as f:
    f.writelines(lines)

print("Fixed reschedule_booking method")
