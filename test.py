import datetime
import pytz

# Define IST timezone
ist = pytz.timezone('Asia/Kolkata')

# Get current UTC time and convert to IST
created_at = datetime.datetime.now(datetime.timezone.utc).astimezone(ist)

# Format to 12-hour clock with AM/PM
formatted_time = created_at.strftime("%I:%M %p %d-%m-%Y")

print(formatted_time)
